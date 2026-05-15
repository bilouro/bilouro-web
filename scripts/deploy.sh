#!/usr/bin/env bash
# scripts/deploy.sh — push current branch and run the remote deploy.
# Quick local wrapper around the remote deploy script on your VM.
#
# Required env vars (export them once in your shell or a .envrc):
#   VM_HOST   — the VM's public IP or hostname
#   SSH_KEY   — path to the SSH private key for VM_USER
# Optional:
#   VM_USER   — defaults to "ubuntu"

set -euo pipefail

cd "$(dirname "$0")/.."

: "${VM_HOST:?Set VM_HOST=<your VM IP or hostname>}"
: "${SSH_KEY:?Set SSH_KEY=<path to your ssh private key>}"
VM_USER="${VM_USER:-ubuntu}"

echo "==> git push"
git push origin "$(git branch --show-current)"

echo "==> remote deploy on $VM_HOST"
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=accept-new "$VM_USER@$VM_HOST" 'sudo bilouro-deploy'
