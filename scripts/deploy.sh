#!/usr/bin/env bash
# scripts/deploy.sh — push current branch and run the remote deploy.
# Quick local wrapper around `bilouro-deploy` on the Lightsail VM.

set -euo pipefail

cd "$(dirname "$0")/.."

VM_HOST="${VM_HOST:-3.251.103.83}"
VM_USER="${VM_USER:-ubuntu}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/lightsail-bilouro.pem}"

echo "==> git push"
git push origin "$(git branch --show-current)"

echo "==> remote deploy on $VM_HOST"
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=accept-new "$VM_USER@$VM_HOST" 'sudo bilouro-deploy'
