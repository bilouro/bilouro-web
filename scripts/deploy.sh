#!/usr/bin/env bash
# scripts/deploy.sh — build, push to ECR, trigger App Runner deploy.
#
# Usage:
#   ./scripts/deploy.sh                  # full pipeline
#   ./scripts/deploy.sh build            # only docker build
#   ./scripts/deploy.sh push             # only push (assumes built)

set -euo pipefail

cd "$(dirname "$0")/.."

PROFILE="${AWS_PROFILE_OVERRIDE:-bilouro}"
REGION="$(aws configure get region --profile "$PROFILE")"
ACCOUNT="$(aws sts get-caller-identity --profile "$PROFILE" --query Account --output text)"
REPO_NAME="bilouro-prod-web"
TAG="${IMAGE_TAG:-latest}"

ECR_URI="${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com/${REPO_NAME}"

cmd_build() {
  echo "→ docker build (linux/amd64)..."
  docker build --platform=linux/amd64 -t "${REPO_NAME}:${TAG}" .
}

cmd_login() {
  echo "→ ECR login..."
  aws ecr get-login-password --region "$REGION" --profile "$PROFILE" \
    | docker login --username AWS --password-stdin "${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com"
}

cmd_push() {
  cmd_login
  echo "→ tagging + pushing to ${ECR_URI}:${TAG}..."
  docker tag "${REPO_NAME}:${TAG}" "${ECR_URI}:${TAG}"
  docker push "${ECR_URI}:${TAG}"
}

cmd_apply_apprunner() {
  echo "→ terraform apply with App Runner enabled..."
  cd infra/terraform
  terraform apply -auto-approve -var enable_apprunner=true
  cd ../..
}

case "${1:-all}" in
  build) cmd_build ;;
  login) cmd_login ;;
  push)  cmd_push ;;
  apply) cmd_apply_apprunner ;;
  all)
    cmd_build
    cmd_push
    cmd_apply_apprunner
    echo "→ Deploy complete."
    cd infra/terraform
    URL=$(terraform output -raw apprunner_service_url 2>/dev/null || echo "")
    [ -n "$URL" ] && echo "App Runner URL: https://${URL}"
    ;;
  *) echo "Unknown command: $1"; exit 1 ;;
esac
