#!/usr/bin/env bash
# scripts/lightsail_fail2ban.sh — install + configure fail2ban on the Lightsail VM.
#
# Two jails:
#   - sshd: bans SSH brute-forcers (4 failures in 10 min → 1h ban).
#   - nginx-scanners: bans IPs that trigger many 4xx (404/444/400/403) in a short
#     window — catches secret-probe bots that target /.env, /.git/, etc.
#
# Idempotent. Run via SSH to the VM:
#     ssh -i <path-to-key> ubuntu@<your-vm-ip> 'sudo bash -s' < scripts/lightsail_fail2ban.sh
# or scp + sudo bash.

set -euo pipefail

apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y fail2ban >/dev/null

tee /etc/fail2ban/filter.d/nginx-scanners.conf >/dev/null <<'EOF'
# Match probes blocked by our 444 rules + generic 4xx flood from scanners.
[Definition]
failregex = ^<HOST> .* "(GET|POST|HEAD) [^"]+" (444|400|403|404) .*$
ignoreregex =
datepattern = %%d/%%b/%%Y:%%H:%%M:%%S %%z
EOF

tee /etc/fail2ban/jail.d/bilouro.local >/dev/null <<'EOF'
[DEFAULT]
bantime  = 1h
findtime = 2m
maxretry = 10
backend  = auto
ignoreip = 127.0.0.1/8 ::1

[sshd]
enabled  = true
port     = ssh
logpath  = %(sshd_log)s
backend  = %(sshd_backend)s
maxretry = 4
findtime = 10m
bantime  = 1h

[nginx-scanners]
enabled  = true
port     = http,https
filter   = nginx-scanners
logpath  = /var/log/nginx/access.log
maxretry = 15
findtime = 2m
bantime  = 6h
EOF

systemctl enable --now fail2ban
fail2ban-client reload >/dev/null
sleep 1
fail2ban-client status

echo "==> done. To inspect a jail:"
echo "    sudo fail2ban-client status nginx-scanners"
echo "    sudo fail2ban-client unban <IP>"
