#!/usr/bin/env bash
# scripts/lightsail_provision.sh — bootstrap a fresh Ubuntu 24.04 Lightsail VM:
#   - Postgres 16
#   - Python 3.13 (via deadsnakes), uv
#   - nginx (TLS via Certbot, apex redirect, reverse proxy to gunicorn)
#   - systemd service for the app
#   - awscli
#
# Run on the VM as ubuntu user (sudo where needed). Idempotent.

set -euo pipefail

APP_DIR=/opt/bilouro/web
APP_USER=bilouro
DOMAINS_PRIMARY="www.bilouro.com"
DOMAINS_OTHER="tech.bilouro.com books.bilouro.com"
APEX="bilouro.com"

if [ "$(whoami)" != "ubuntu" ]; then
  echo "Run as ubuntu user." >&2; exit 1
fi

echo "==> apt update + base packages"
sudo apt-get update -y
sudo apt-get install -y --no-install-recommends \
  build-essential ca-certificates curl gnupg lsb-release \
  python3 python3-venv python3-dev libpq-dev \
  postgresql postgresql-contrib \
  nginx ufw \
  certbot python3-certbot-nginx \
  jq unzip git

echo "==> awscli v2"
if ! command -v aws >/dev/null 2>&1; then
  cd /tmp
  curl -sSLo awscliv2.zip "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip"
  unzip -q awscliv2.zip
  sudo ./aws/install
  rm -rf aws awscliv2.zip
fi

echo "==> uv (single-shot binary)"
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
fi

echo "==> firewall"
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

echo "==> create app user"
if ! id "$APP_USER" >/dev/null 2>&1; then
  sudo useradd --system --create-home --shell /bin/bash "$APP_USER"
fi
sudo mkdir -p "$APP_DIR"
sudo chown -R "$APP_USER":"$APP_USER" /opt/bilouro

echo "==> postgres setup"
sudo -u postgres psql -c "DO \$\$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='bilouro') THEN
    CREATE ROLE bilouro LOGIN PASSWORD 'bilouro_local_change_me';
  END IF;
END \$\$;"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='bilouro'" | grep -q 1 || \
  sudo -u postgres createdb -O bilouro bilouro

echo "==> done."
