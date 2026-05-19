#!/usr/bin/env bash
# scripts/lightsail_goaccess.sh — install GoAccess + private dashboard at /admin/stats/.
#
# What it does:
#   1. Install goaccess + apache2-utils (for htpasswd).
#   2. Persist analyzed data across log rotations with --keep-db-files.
#   3. Hourly cron regenerates /var/www/stats/index.html from /var/log/nginx/access.log*.
#   4. Logrotate config bumped to 60 days for nginx access logs.
#   5. nginx /admin/stats/ location with HTTP Basic Auth (htpasswd).
#
# Required env vars before running:
#   STATS_USER       — basic-auth username
#   STATS_PASSWORD   — basic-auth password (plain; will be bcrypted by htpasswd)
#
# Run remotely:
#   STATS_USER=admin STATS_PASSWORD='...' \
#     ssh -i ~/.ssh/<key>.pem ubuntu@<vm-ip> 'sudo -E bash -s' < scripts/lightsail_goaccess.sh
#
# Idempotent. Safe to re-run.

set -euo pipefail

: "${STATS_USER:?Set STATS_USER}"
: "${STATS_PASSWORD:?Set STATS_PASSWORD}"

STATS_DIR=/var/www/stats
DB_DIR=/var/lib/goaccess
HTPASSWD=/etc/nginx/.htpasswd-stats
CRON_FILE=/etc/cron.d/goaccess

echo "==> install packages"
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y goaccess apache2-utils >/dev/null

echo "==> create dirs"
mkdir -p "$STATS_DIR" "$DB_DIR"
chown www-data:www-data "$STATS_DIR"

echo "==> basic-auth credentials"
htpasswd -bcB "$HTPASSWD" "$STATS_USER" "$STATS_PASSWORD"
chmod 640 "$HTPASSWD"
chown root:www-data "$HTPASSWD"

echo "==> logrotate: keep 60 days of nginx logs"
sed -i 's/^\(\s*rotate\s*\)[0-9]\+/\160/' /etc/logrotate.d/nginx || true
grep -q "rotate 60" /etc/logrotate.d/nginx || echo "  ! warning: rotate setting not bumped — inspect /etc/logrotate.d/nginx manually"

echo "==> initial GoAccess report"
# COMBINED log format = standard nginx. --keep-db-files lets us accumulate beyond
# rotated logs by re-running goaccess incrementally.
# Use a wrapper to absorb -.gz logs into a single stream sorted by time.
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

echo "==> nginx /admin/stats/ location"
# Append a snippet to the existing shared bilouro-app.conf so all three vhosts
# expose the dashboard. Idempotent.
SNIPPET=/etc/nginx/snippets/bilouro-stats.conf
cat > "$SNIPPET" <<'CONF'
# Private analytics dashboard.
location /admin/stats/ {
    alias /var/www/stats/;
    index index.html;
    auth_basic "bilouro stats";
    auth_basic_user_file /etc/nginx/.htpasswd-stats;
    try_files $uri $uri/ =404;
}
CONF

# Include the snippet inside bilouro-app.conf (only once).
MAIN_SNIPPET=/etc/nginx/snippets/bilouro-app.conf
if ! grep -q "bilouro-stats.conf" "$MAIN_SNIPPET"; then
  # Insert before the catch-all "location /" block.
  awk '
    /^location \/ \{/ && !inserted { print "include /etc/nginx/snippets/bilouro-stats.conf;"; print ""; inserted=1 }
    { print }
  ' "$MAIN_SNIPPET" > "$MAIN_SNIPPET.tmp" && mv "$MAIN_SNIPPET.tmp" "$MAIN_SNIPPET"
fi

nginx -t
systemctl reload nginx

echo
echo "==> done. dashboard available at:"
echo "    https://www.bilouro.com/admin/stats/"
echo "    (also tech.* and books.*)"
echo "    user: $STATS_USER"
echo "    password: <as supplied>"
echo
echo "Manual rebuild any time: sudo /usr/local/bin/goaccess-rebuild"
echo "Cron rebuilds hourly at minute 17 (see $CRON_FILE)."
