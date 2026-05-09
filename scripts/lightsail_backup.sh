#!/usr/bin/env bash
# /usr/local/bin/bilouro-backup — weekly Postgres dump → S3.
# Cron: every Sunday 02:00 UTC.

set -euo pipefail

source /etc/bilouro.env

BUCKET="bilouro-prod-media-eu-west-1"
DATE=$(date -u +%Y-%m-%d)
DUMP_FILE="/tmp/bilouro-${DATE}.sql.gz"

PGPASSWORD=$(echo "$DATABASE_URL" | sed -E 's|^postgres://[^:]+:([^@]+)@.*|\1|')
export PGPASSWORD

pg_dump -h 127.0.0.1 -U bilouro -d bilouro --no-owner --no-acl | gzip > "$DUMP_FILE"

aws s3 cp "$DUMP_FILE" "s3://${BUCKET}/backups/postgres/bilouro-${DATE}.sql.gz" \
  --region eu-west-1 \
  --storage-class STANDARD_IA

# keep last 12 weeks (~3 months)
aws s3 ls "s3://${BUCKET}/backups/postgres/" --region eu-west-1 \
  | sort \
  | head -n -12 \
  | awk '{print $4}' \
  | while read -r key; do
      [ -n "$key" ] && aws s3 rm "s3://${BUCKET}/backups/postgres/${key}" --region eu-west-1
    done

rm -f "$DUMP_FILE"
echo "[$(date)] backup ok: bilouro-${DATE}.sql.gz"
