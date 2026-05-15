#!/usr/bin/env bash
# scripts/lightsail_run_certbot.sh — issue Let's Encrypt certs and switch nginx to HTTPS.
# Run AFTER you've migrated DNS to Lightsail's static IP and the records have propagated.
#
# Run on the VM as ubuntu:
#   /tmp/lightsail_run_certbot.sh

set -euo pipefail

ALERT_EMAIL="${ALERT_EMAIL:?Set ALERT_EMAIL=<email for Let's Encrypt notifications>}"

echo "==> Certbot — issue certs (subdomains + apex)"
sudo mkdir -p /var/www/html

sudo certbot certonly --webroot -w /var/www/html \
  --non-interactive --agree-tos --email "$ALERT_EMAIL" \
  -d www.bilouro.com -d tech.bilouro.com -d books.bilouro.com \
  --cert-name www.bilouro.com

sudo certbot certonly --webroot -w /var/www/html \
  --non-interactive --agree-tos --email "$ALERT_EMAIL" \
  -d bilouro.com \
  --cert-name bilouro.com

echo "==> swap nginx to HTTPS-aware config"
sudo tee /etc/nginx/sites-available/bilouro >/dev/null <<'NGINX'
# Apex bilouro.com → 301 to www
server {
    listen 80;
    listen [::]:80;
    server_name bilouro.com;
    location /.well-known/acme-challenge/ { root /var/www/html; }
    return 301 https://www.bilouro.com$request_uri;
}

server {
    listen 443 ssl;
    listen [::]:443 ssl;
    http2 on;
    server_name bilouro.com;
    ssl_certificate     /etc/letsencrypt/live/bilouro.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/bilouro.com/privkey.pem;
    return 301 https://www.bilouro.com$request_uri;
}

# Subdomains: HTTP → 301 to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name www.bilouro.com tech.bilouro.com books.bilouro.com;
    location /.well-known/acme-challenge/ { root /var/www/html; }
    location / { return 301 https://$host$request_uri; }
}

# Subdomains over HTTPS
server {
    listen 443 ssl;
    listen [::]:443 ssl;
    http2 on;
    server_name www.bilouro.com tech.bilouro.com books.bilouro.com;

    ssl_certificate     /etc/letsencrypt/live/www.bilouro.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/www.bilouro.com/privkey.pem;

    client_max_body_size 25m;

    location /static/ {
        alias /opt/bilouro/web/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /healthz {
        proxy_pass http://127.0.0.1:8000/healthz;
        access_log off;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_redirect off;
        proxy_read_timeout 60s;
    }
}
NGINX

sudo nginx -t
sudo systemctl reload nginx

echo "==> enable SECURE_SSL_REDIRECT in app env"
sudo sed -i 's/^SECURE_SSL_REDIRECT=.*/SECURE_SSL_REDIRECT=True/' /etc/bilouro.env
sudo systemctl restart bilouro-web

echo "==> done. Test:"
echo "  curl -I https://www.bilouro.com/"
echo "  curl -I https://tech.bilouro.com/"
echo "  curl -I https://books.bilouro.com/"
echo "  curl -I http://bilouro.com/   # should 301 to https://www.bilouro.com/"
