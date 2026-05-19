#!/usr/bin/env bash
# scripts/lightsail_goaccess.sh — install GoAccess + private dashboard at /admin/stats/.
#
# What it does:
#   1. Install goaccess.
#   2. Persist analyzed data across log rotations (goaccess --persist --restore).
#   3. Hourly cron regenerates /var/www/stats/index.html from /var/log/nginx/access.log*.
#   4. Logrotate config bumped to 60 days for nginx access logs.
#   5. nginx /_internal/stats/ location with the `internal` directive — only
#      Django/Wagtail can dispatch the file via X-Accel-Redirect, after
#      authorising the request with `@require_admin_access`. The public-facing
#      URL is /admin/stats/, served by the Wagtail admin (with a sidebar
#      menu item registered in apps/core/wagtail_hooks.py).
#
# Run remotely:
#   ssh -i ~/.ssh/<key>.pem ubuntu@<vm-ip> 'sudo bash -s' < scripts/lightsail_goaccess.sh
#
# Idempotent. Safe to re-run. Removes legacy htpasswd from prior version that
# used nginx basic-auth.

set -euo pipefail

STATS_DIR=/var/www/stats
DB_DIR=/var/lib/goaccess
CRON_FILE=/etc/cron.d/goaccess
LEGACY_HTPASSWD=/etc/nginx/.htpasswd-stats

echo "==> install packages"
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y goaccess >/dev/null

echo "==> create dirs"
mkdir -p "$STATS_DIR" "$DB_DIR"
chown www-data:www-data "$STATS_DIR"

if [ -f "$LEGACY_HTPASSWD" ]; then
  echo "==> remove legacy htpasswd (auth now via Wagtail admin)"
  rm -f "$LEGACY_HTPASSWD"
fi

echo "==> logrotate: keep 60 days of nginx logs"
sed -i 's/^\(\s*rotate\s*\)[0-9]\+/\160/' /etc/logrotate.d/nginx || true
grep -q "rotate 60" /etc/logrotate.d/nginx || echo "  ! warning: rotate setting not bumped — inspect /etc/logrotate.d/nginx manually"

echo "==> install goaccess-rebuild wrapper"
cat > /usr/local/bin/goaccess-rebuild <<'WRAPPER'
#!/usr/bin/env bash
set -euo pipefail
STATS_DIR=/var/www/stats
DB_DIR=/var/lib/goaccess
# Concatenate logs in chronological order (oldest first).
zcat -f /var/log/nginx/access.log.*.gz 2>/dev/null > /tmp/goaccess-input || true
for f in $(ls -tr /var/log/nginx/access.log.[0-9] 2>/dev/null); do cat "$f" >> /tmp/goaccess-input; done
cat /var/log/nginx/access.log >> /tmp/goaccess-input
goaccess /tmp/goaccess-input \
  --log-format=COMBINED \
  --db-path="$DB_DIR" \
  --persist --restore \
  -o "$STATS_DIR/index.html" \
  --html-report-title="bilouro.com stats" \
  --no-progress \
  --ignore-crawlers \
  --real-os \
  --html-prefs='{"theme":"darkPurple","perPage":12}'
rm -f /tmp/goaccess-input
WRAPPER
chmod +x /usr/local/bin/goaccess-rebuild

# Run the first build now (so the dashboard exists before we wire nginx).
/usr/local/bin/goaccess-rebuild

echo "==> cron: hourly rebuild"
cat > "$CRON_FILE" <<EOF
# Regenerate bilouro.com stats every hour.
17 * * * * root /usr/local/bin/goaccess-rebuild >> /var/log/goaccess-cron.log 2>&1
EOF
chmod 644 "$CRON_FILE"

echo "==> nginx /_internal/stats/ location (internal; reached only via X-Accel-Redirect)"
SNIPPET=/etc/nginx/snippets/bilouro-stats.conf
cat > "$SNIPPET" <<'CONF'
# Private analytics dashboard. The Django/Wagtail view at /admin/stats/ is
# `@require_admin_access`; on success it emits X-Accel-Redirect: /_internal/stats/
# and nginx serves the static HTML from this internal-only location.
location /_internal/stats/ {
    internal;
    alias /var/www/stats/;
    index index.html;
    try_files $uri $uri/index.html =404;
}
CONF

# Include the snippet inside bilouro-app.conf (only once).
MAIN_SNIPPET=/etc/nginx/snippets/bilouro-app.conf
if ! grep -q "bilouro-stats.conf" "$MAIN_SNIPPET"; then
  awk '
    /^location \/ \{/ && !inserted { print "include /etc/nginx/snippets/bilouro-stats.conf;"; print ""; inserted=1 }
    { print }
  ' "$MAIN_SNIPPET" > "$MAIN_SNIPPET.tmp" && mv "$MAIN_SNIPPET.tmp" "$MAIN_SNIPPET"
fi

nginx -t
systemctl reload nginx

echo
echo "==> done. Dashboard available at:"
echo "    https://www.bilouro.com/admin/stats/"
echo "    (or tech.* / books.*)"
echo "    Login: same as your Wagtail admin user."
echo
echo "Manual rebuild any time: sudo /usr/local/bin/goaccess-rebuild"
echo "Cron rebuilds hourly at minute 17 (see $CRON_FILE)."
