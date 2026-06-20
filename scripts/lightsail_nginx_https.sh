#!/usr/bin/env bash
# scripts/lightsail_nginx_https.sh — switch nginx to HTTPS using per-domain certs.
# Run after all 5 certs (www/tech/books/studio/bilouro) exist in /etc/letsencrypt/live/.
#
# To add the studio cert (after the DNS A/CNAME for studio.bilouro.com resolves
# to this VM and the HTTP→301 block below is live so the ACME webroot is served):
#   sudo certbot certonly --webroot -w /var/www/html \
#     --non-interactive --agree-tos --email "$ALERT_EMAIL" \
#     -d studio.bilouro.com --cert-name studio.bilouro.com

set -euo pipefail

sudo tee /etc/nginx/sites-available/bilouro >/dev/null <<'NGINX'
# Apex bilouro.com → 301 to www
server {
    listen 80;
    listen [::]:80;
    server_name bilouro.com;
    location /.well-known/acme-challenge/ { root /var/www/html; }
    location / { return 301 https://www.bilouro.com$request_uri; }
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name bilouro.com;
    ssl_certificate     /etc/letsencrypt/live/bilouro.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/bilouro.com/privkey.pem;
    return 301 https://www.bilouro.com$request_uri;
}

# Subdomains: HTTP → 301 to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name www.bilouro.com tech.bilouro.com books.bilouro.com studio.bilouro.com;
    location /.well-known/acme-challenge/ { root /var/www/html; }
    location / { return 301 https://$host$request_uri; }
}

# www subdomain HTTPS
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name www.bilouro.com;
    ssl_certificate     /etc/letsencrypt/live/www.bilouro.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/www.bilouro.com/privkey.pem;
    include /etc/nginx/snippets/bilouro-app.conf;
}

# tech subdomain HTTPS
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name tech.bilouro.com;
    ssl_certificate     /etc/letsencrypt/live/tech.bilouro.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/tech.bilouro.com/privkey.pem;
    include /etc/nginx/snippets/bilouro-app.conf;
}

# books subdomain HTTPS
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name books.bilouro.com;
    ssl_certificate     /etc/letsencrypt/live/books.bilouro.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/books.bilouro.com/privkey.pem;
    include /etc/nginx/snippets/bilouro-app.conf;
}

# studio subdomain HTTPS
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name studio.bilouro.com;
    ssl_certificate     /etc/letsencrypt/live/studio.bilouro.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/studio.bilouro.com/privkey.pem;
    include /etc/nginx/snippets/bilouro-app.conf;
}

# Default catch-all HTTP (no cert needed) — drop unknown hosts before they reach Django
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    return 444;
}

# Default catch-all HTTPS — drop unknown SNI / Host so they don't fall through to
# the first matching vhost and accidentally serve content under wrong domains.
# Uses any valid cert (TLS will mismatch SNI for unknown hosts; HTTP response is 444).
server {
    listen 443 ssl http2 default_server;
    listen [::]:443 ssl http2 default_server;
    server_name _;
    ssl_certificate     /etc/letsencrypt/live/www.bilouro.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/www.bilouro.com/privkey.pem;
    return 444;
}
NGINX

sudo mkdir -p /etc/nginx/snippets
sudo tee /etc/nginx/snippets/bilouro-app.conf >/dev/null <<'SNIP'
client_max_body_size 25m;

# Drop secret-probe scans without hitting Django (added 2026-05-14 after OOM
# postmortem). 444 = nginx closes the connection without sending a response.
location ~* (?:^|/)\.env(?:$|/|\.[a-z]+$) { return 444; }
location ~* (?:^|/)\.(?:git|aws|boto|svn|hg)(?:/|$) { return 444; }
location ~* /(?:serviceAccountKey|service-account|google-service-account|firebase-service-account|aws-credentials|credentials|secrets|config)\.(?:json|js|ya?ml)$ { return 444; }
location ~* /(?:settings|local_settings|wp-config|configuration)\.(?:py|php|inc)$ { return 444; }
location ~* /(?:phpinfo|info|test|adminer|phpmyadmin)\.php$ { return 444; }
location ~* /(?:web\.config|\.htaccess|\.htpasswd|\.npmrc|\.pypirc|id_rsa|id_dsa)$ { return 444; }
location ~* \.(?:bak|backup|old|orig|swp|swo|tmp|sql)$ { return 444; }

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
SNIP

sudo nginx -t
sudo systemctl reload nginx

# Enable SSL redirect in Django
sudo sed -i 's/^SECURE_SSL_REDIRECT=.*/SECURE_SSL_REDIRECT=True/' /etc/bilouro.env
sudo systemctl restart bilouro-web

echo "==> nginx HTTPS active. Test:"
echo "  curl -I https://www.bilouro.com/"
echo "  curl -I https://tech.bilouro.com/"
echo "  curl -I https://books.bilouro.com/"
echo "  curl -I http://bilouro.com/"
