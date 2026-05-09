#!/usr/bin/env bash
# server_deploy.sh — runs ON THE LIGHTSAIL VM. Pulls, installs, migrates,
# bootstraps, restarts, health-checks, rolls back on failure.
#
# Install once at /usr/local/bin/bilouro-deploy (see lightsail_app_setup.sh).
#
# Usage on VM:  sudo bilouro-deploy
# Usage from laptop: see scripts/deploy.sh wrapper.

set -euo pipefail

APP_DIR=/opt/bilouro/web
APP_USER=bilouro
SERVICE=bilouro-web
HEALTH_URL="http://127.0.0.1:8000/healthz/"

START_SHA=$(sudo -u "$APP_USER" git -C "$APP_DIR" rev-parse HEAD)
echo "==> deploy starting from $START_SHA"

cleanup_rollback() {
  echo "❌ deploy failed — rolling back to $START_SHA"
  sudo -u "$APP_USER" git -C "$APP_DIR" reset --hard "$START_SHA"
  sudo -u "$APP_USER" bash -lc "cd $APP_DIR && uv sync --no-dev" || true
  sudo systemctl restart "$SERVICE"
  exit 1
}

trap cleanup_rollback ERR

echo "==> git pull"
sudo -u "$APP_USER" git -C "$APP_DIR" pull --ff-only

NEW_SHA=$(sudo -u "$APP_USER" git -C "$APP_DIR" rev-parse HEAD)
if [ "$START_SHA" = "$NEW_SHA" ]; then
  echo "==> no new commits; skipping rebuild"
  trap - ERR
  exit 0
fi
echo "==> updating to $NEW_SHA"

echo "==> uv sync"
sudo -u "$APP_USER" bash -lc "cd $APP_DIR && uv sync --no-dev"

echo "==> migrate + collectstatic + compilemessages"
sudo -u "$APP_USER" bash -lc "cd $APP_DIR && set -a && . /etc/bilouro.env && set +a && \
  uv run python manage.py migrate --noinput && \
  uv run python manage.py collectstatic --noinput && \
  uv run python manage.py compilemessages --ignore=.venv"

echo "==> bootstrap_sites (idempotent)"
sudo -u "$APP_USER" bash -lc "cd $APP_DIR && set -a && . /etc/bilouro.env && set +a && \
  uv run python manage.py bootstrap_sites --prod" || echo "(bootstrap had warnings)"

echo "==> systemd timer for publish_scheduled_pages (idempotent)"
sudo tee /etc/systemd/system/bilouro-publish-scheduled.service >/dev/null <<UNIT
[Unit]
Description=Wagtail — publish scheduled pages
After=network.target postgresql.service

[Service]
Type=oneshot
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
EnvironmentFile=/etc/bilouro.env
ExecStart=/home/$APP_USER/.local/bin/uv run python manage.py publish_scheduled_pages
UNIT

sudo tee /etc/systemd/system/bilouro-publish-scheduled.timer >/dev/null <<'UNIT'
[Unit]
Description=Run Wagtail publish_scheduled_pages hourly

[Timer]
OnCalendar=hourly
Persistent=true
Unit=bilouro-publish-scheduled.service

[Install]
WantedBy=timers.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable --now bilouro-publish-scheduled.timer >/dev/null

echo "==> restart $SERVICE"
sudo systemctl restart "$SERVICE"

echo "==> health check"
sleep 4
for i in 1 2 3 4 5 6 7 8 9 10; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL" --max-time 5 || echo "000")
  if [ "$code" = "200" ]; then
    echo "✓ health OK (try $i)"
    trap - ERR
    echo ""
    echo "🎉 deploy complete  $START_SHA → $NEW_SHA"
    exit 0
  fi
  echo "  health try $i = $code, waiting 3s..."
  sleep 3
done

echo "❌ health check failed after 10 tries"
false  # triggers ERR trap → rollback
