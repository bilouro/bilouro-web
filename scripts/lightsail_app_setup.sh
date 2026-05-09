#!/usr/bin/env bash
# scripts/lightsail_app_setup.sh — clone code + create venv + systemd + nginx + Certbot.
# Run as `ubuntu` on the VM, after lightsail_provision.sh has succeeded.
#
# Required env vars before running:
#   GITHUB_TOKEN  — fine-grained PAT with read access to bilouro/bilouro-web
#   AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY  — for S3 media + Secrets Manager
#   ALERT_EMAIL  — for Certbot notifications

set -euo pipefail

APP_DIR=/opt/bilouro/web
APP_USER=bilouro

: "${ALERT_EMAIL:=bilouro@bilouro.com}"
: "${DJANGO_SECRET_KEY:=$(openssl rand -hex 64)}"
: "${DB_PASSWORD:=$(openssl rand -hex 16)}"
: "${SUPERUSER_USERNAME:=admin}"
if [ -z "${SUPERUSER_PASSWORD:-}" ]; then
  SUPERUSER_PASSWORD=$(openssl rand -base64 24 | tr -d '/+=' | head -c 24)
  echo ">>> Generated random superuser password: $SUPERUSER_PASSWORD"
  echo ">>> Store this NOW or set SUPERUSER_PASSWORD env var before running."
fi
: "${SUPERUSER_EMAIL:=bilouro@bilouro.com}"

echo "==> set Postgres password"
sudo -u postgres psql -c "ALTER ROLE bilouro WITH PASSWORD '${DB_PASSWORD}';"

echo "==> clone repo (or update)"
if [ ! -d "$APP_DIR/.git" ]; then
  sudo -u "$APP_USER" git clone "git@github.com:bilouro/bilouro-web.git" "$APP_DIR"
else
  sudo -u "$APP_USER" git -C "$APP_DIR" pull --ff-only
fi

echo "==> uv sync as app user"
sudo -u "$APP_USER" bash -lc "cd $APP_DIR && \$HOME/.local/bin/uv sync --no-dev"

echo "==> /etc/bilouro.env"
sudo tee /etc/bilouro.env >/dev/null <<EOF
DJANGO_SETTINGS_MODULE=config.settings.prod
SECRET_KEY=${DJANGO_SECRET_KEY}
DEBUG=False
ALLOWED_HOSTS=www.bilouro.com,tech.bilouro.com,books.bilouro.com,bilouro.com,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://www.bilouro.com,https://tech.bilouro.com,https://books.bilouro.com
DATABASE_URL=postgres://bilouro:${DB_PASSWORD}@127.0.0.1:5432/bilouro
WAGTAILADMIN_BASE_URL=https://www.bilouro.com
DEFAULT_FROM_EMAIL=hello@bilouro.com
SECURE_SSL_REDIRECT=False
AWS_STORAGE_BUCKET_NAME=bilouro-prod-media-eu-west-1
AWS_S3_REGION_NAME=eu-west-1
AWS_SES_REGION_NAME=eu-west-1
AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID:-}
AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY:-}
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EOF
sudo chown "$APP_USER":"$APP_USER" /etc/bilouro.env
sudo chmod 600 /etc/bilouro.env

echo "==> Django migrate + collectstatic + bootstrap"
sudo -u "$APP_USER" bash -lc "cd $APP_DIR && set -a && . /etc/bilouro.env && set +a && \
  \$HOME/.local/bin/uv run python manage.py migrate --noinput && \
  \$HOME/.local/bin/uv run python manage.py collectstatic --noinput && \
  \$HOME/.local/bin/uv run python manage.py bootstrap_sites --prod"

echo "==> superuser (idempotent)"
sudo -u "$APP_USER" bash -lc "cd $APP_DIR && set -a && . /etc/bilouro.env && set +a && \
  DJANGO_SUPERUSER_USERNAME=$SUPERUSER_USERNAME \
  DJANGO_SUPERUSER_EMAIL=$SUPERUSER_EMAIL \
  DJANGO_SUPERUSER_PASSWORD=$SUPERUSER_PASSWORD \
  \$HOME/.local/bin/uv run python manage.py createsuperuser --noinput || echo 'superuser exists'"

echo "==> systemd unit /etc/systemd/system/bilouro-web.service"
sudo tee /etc/systemd/system/bilouro-web.service >/dev/null <<'UNIT'
[Unit]
Description=bilouro-web (Wagtail + Gunicorn)
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=notify
User=bilouro
Group=bilouro
WorkingDirectory=/opt/bilouro/web
EnvironmentFile=/etc/bilouro.env
ExecStart=/home/bilouro/.local/bin/uv run gunicorn config.wsgi:application \
  --bind 127.0.0.1:8000 \
  --workers 3 \
  --timeout 60 \
  --access-logfile - \
  --error-logfile -
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable bilouro-web
sudo systemctl restart bilouro-web

echo "==> nginx config"
sudo tee /etc/nginx/sites-available/bilouro >/dev/null <<'NGINX'
# Apex redirect: bilouro.com → www.bilouro.com
server {
    listen 80;
    listen [::]:80;
    server_name bilouro.com;
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

# Subdomains: reverse proxy to gunicorn
server {
    listen 80;
    listen [::]:80;
    server_name www.bilouro.com tech.bilouro.com books.bilouro.com;

    # Allow Certbot ACME challenges
    location /.well-known/acme-challenge/ { root /var/www/html; }

    location / { return 301 https://$host$request_uri; }
}

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

sudo ln -sf /etc/nginx/sites-available/bilouro /etc/nginx/sites-enabled/bilouro
sudo rm -f /etc/nginx/sites-enabled/default

echo "==> initial nginx config WITHOUT SSL (for Certbot bootstrap)"
sudo tee /etc/nginx/sites-available/bilouro-bootstrap >/dev/null <<'NGINXBOOT'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name www.bilouro.com tech.bilouro.com books.bilouro.com bilouro.com _;
    location /.well-known/acme-challenge/ { root /var/www/html; }
    location / { return 200 "ok\n"; add_header Content-Type text/plain; }
}
NGINXBOOT
sudo ln -sf /etc/nginx/sites-available/bilouro-bootstrap /etc/nginx/sites-enabled/bilouro
sudo rm -f /etc/nginx/sites-enabled/bilouro
sudo systemctl restart nginx

echo "==> Certbot — issue certs for www, tech, books, and apex"
sudo mkdir -p /var/www/html
sudo certbot certonly --webroot -w /var/www/html \
  --non-interactive --agree-tos --email "$ALERT_EMAIL" \
  -d www.bilouro.com -d tech.bilouro.com -d books.bilouro.com \
  --cert-name www.bilouro.com || echo "(certs may already exist)"

sudo certbot certonly --webroot -w /var/www/html \
  --non-interactive --agree-tos --email "$ALERT_EMAIL" \
  -d bilouro.com \
  --cert-name bilouro.com || echo "(apex cert may already exist)"

echo "==> swap to real nginx config + reload"
sudo ln -sf /etc/nginx/sites-available/bilouro /etc/nginx/sites-enabled/bilouro
sudo nginx -t
sudo systemctl reload nginx

echo "==> done. Test: curl -I https://www.bilouro.com/"
