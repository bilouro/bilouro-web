#!/usr/bin/env bash
# scripts/cloud_build.sh — builds the Docker image via AWS CodeBuild
# (zero dependency on local Docker Desktop).
#
# Steps:
#   1. Zip the repo (excluding .git, .venv, infra/terraform state)
#   2. Upload to S3 source bucket
#   3. Trigger CodeBuild
#   4. Stream logs until done
#   5. Image lands in ECR

set -euo pipefail

cd "$(dirname "$0")/.."

PROFILE="${AWS_PROFILE_OVERRIDE:-bilouro}"
REGION="$(aws configure get region --profile "$PROFILE")"

cd infra/terraform
PROJECT=$(terraform output -raw codebuild_project_name 2>/dev/null)
BUCKET=$(terraform output -raw build_source_bucket 2>/dev/null)
cd ../..

[ -z "$PROJECT" ] && { echo "Error: CodeBuild project not found. Run terraform apply first."; exit 1; }

ZIP="/tmp/bilouro-source.zip"
echo "→ Zipping source (excluding .git, .venv, infra/terraform state)..."
rm -f "$ZIP"
zip -qr "$ZIP" . \
  -x ".git/*" \
  -x ".venv/*" \
  -x "*/__pycache__/*" \
  -x "infra/terraform/.terraform/*" \
  -x "infra/terraform/*.tfstate*" \
  -x ".idea/*" \
  -x ".DS_Store" \
  -x "media/*" \
  -x "staticfiles/*" \
  -x "*.pyc"

SIZE=$(du -h "$ZIP" | cut -f1)
echo "→ Source zip: $ZIP ($SIZE)"

echo "→ Uploading to s3://${BUCKET}/source.zip..."
aws s3 cp "$ZIP" "s3://${BUCKET}/source.zip" --profile "$PROFILE" --region "$REGION" --quiet

echo "→ Starting CodeBuild project: $PROJECT"
BUILD_ID=$(aws codebuild start-build \
  --project-name "$PROJECT" \
  --profile "$PROFILE" --region "$REGION" \
  --query 'build.id' --output text)
echo "→ Build started: $BUILD_ID"
echo "→ Streaming logs (Ctrl-C to detach; build continues in cloud)..."

LOG_GROUP="/aws/codebuild/${PROJECT}"
sleep 10  # give CodeBuild time to create the log stream
LOG_STREAM=$(aws logs describe-log-streams \
  --log-group-name "$LOG_GROUP" \
  --profile "$PROFILE" --region "$REGION" \
  --order-by LastEventTime --descending \
  --max-items 1 --query 'logStreams[0].logStreamName' --output text)

aws logs tail "$LOG_GROUP" --log-stream-names "$LOG_STREAM" \
  --follow --profile "$PROFILE" --region "$REGION" || true

# Wait for completion
echo ""
echo "→ Waiting for build to finish..."
while true; do
  STATUS=$(aws codebuild batch-get-builds --ids "$BUILD_ID" \
    --profile "$PROFILE" --region "$REGION" \
    --query 'builds[0].buildStatus' --output text)
  if [ "$STATUS" != "IN_PROGRESS" ]; then
    echo "→ Build status: $STATUS"
    break
  fi
  sleep 10
done

if [ "$STATUS" = "SUCCEEDED" ]; then
  echo "✓ Image pushed to ECR. Now: terraform apply -var enable_apprunner=true"
else
  echo "✗ Build did not succeed. Check CloudWatch logs."
  exit 1
fi
