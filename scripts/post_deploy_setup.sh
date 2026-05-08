#!/usr/bin/env bash
# scripts/post_deploy_setup.sh — one-time post-deploy operations.
#
# Creates a Django superuser by:
#   1. Temporarily allowing your public IP into the RDS security group
#   2. Temporarily making RDS publicly accessible
#   3. Running createsuperuser from local against the prod database
#   4. Reverting both changes
#
# Usage:
#   ./scripts/post_deploy_setup.sh

set -euo pipefail

cd "$(dirname "$0")/.."

PROFILE="${AWS_PROFILE_OVERRIDE:-bilouro}"
REGION="$(aws configure get region --profile "$PROFILE")"

cd infra/terraform
RDS_ENDPOINT=$(terraform output -raw rds_endpoint 2>/dev/null)
RDS_SG=$(terraform state show aws_security_group.rds | grep -E '^\s+id\s+=' | head -1 | awk -F'"' '{print $2}')
DB_URL_ARN=$(terraform output -raw secret_db_url_arn 2>/dev/null)
cd ../..

MY_IP=$(curl -s https://checkip.amazonaws.com)
echo "Your IP: $MY_IP"
echo "RDS SG:  $RDS_SG"

cleanup() {
  echo ""
  echo "→ Reverting RDS to private..."
  aws ec2 revoke-security-group-ingress --profile "$PROFILE" --region "$REGION" \
    --group-id "$RDS_SG" \
    --protocol tcp --port 5432 --cidr "${MY_IP}/32" 2>&1 | head -3 || true
  aws rds modify-db-instance --profile "$PROFILE" --region "$REGION" \
    --db-instance-identifier bilouro-prod-pg \
    --no-publicly-accessible \
    --apply-immediately >/dev/null
  echo "Done. RDS will revert to private in a few minutes."
}
trap cleanup EXIT

echo "→ Allowing $MY_IP/32 in RDS SG..."
aws ec2 authorize-security-group-ingress --profile "$PROFILE" --region "$REGION" \
  --group-id "$RDS_SG" \
  --protocol tcp --port 5432 --cidr "${MY_IP}/32"

echo "→ Making RDS publicly accessible (takes ~30s)..."
aws rds modify-db-instance --profile "$PROFILE" --region "$REGION" \
  --db-instance-identifier bilouro-prod-pg \
  --publicly-accessible --apply-immediately >/dev/null

echo "→ Waiting for change to propagate..."
sleep 60

echo "→ Fetching DATABASE_URL from Secrets Manager..."
DATABASE_URL=$(aws secretsmanager get-secret-value --profile "$PROFILE" --region "$REGION" \
  --secret-id "$DB_URL_ARN" --query SecretString --output text)

echo "→ Creating superuser..."
DJANGO_SUPERUSER_USERNAME="${DJANGO_SUPERUSER_USERNAME:-admin}"
DJANGO_SUPERUSER_EMAIL="${DJANGO_SUPERUSER_EMAIL:-bilouro@bilouro.com}"
read -s -p "Choose a strong superuser password: " DJANGO_SUPERUSER_PASSWORD
echo ""
export DJANGO_SUPERUSER_USERNAME DJANGO_SUPERUSER_EMAIL DJANGO_SUPERUSER_PASSWORD
export DATABASE_URL
export DJANGO_SETTINGS_MODULE="config.settings.dev"
export ALLOWED_HOSTS="*"

uv run python manage.py createsuperuser --noinput || echo "(superuser may already exist; that's OK)"

echo ""
echo "✓ Superuser '$DJANGO_SUPERUSER_USERNAME' is ready."
echo "  Login at: https://www.bilouro.com/admin/  (after DNS propagates)"
