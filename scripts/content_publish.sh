#!/usr/bin/env bash
# scripts/content_publish.sh — push one content folder from drafts/ to the VM and
# run its importer there (studio.bilouro.com). Content lives in drafts/ (gitignored).
#
#   ./scripts/content_publish.sh solution <slug> [import_solution_copy args...]
#   ./scripts/content_publish.sh article  <slug> [import_article args...]
#
# Examples:
#   ./scripts/content_publish.sh solution studio-app --dry-run
#   ./scripts/content_publish.sh solution software-box-crossfit --create
#   ./scripts/content_publish.sh article  marcacoes-whatsapp-estudio --publish
#   ./scripts/content_publish.sh article  lista-de-espera-aulas-de-grupo --go-live "2026-10-18 09:00"
#
# Env (same as deploy.sh): VM_HOST, SSH_KEY, optional VM_USER (default ubuntu).
set -euo pipefail
cd "$(dirname "$0")/.."

: "${VM_HOST:?Set VM_HOST}"; : "${SSH_KEY:?Set SSH_KEY}"
VM_USER="${VM_USER:-ubuntu}"
KIND="${1:?solution|article}"; SLUG="${2:?slug}"; shift 2
APP_DIR=/opt/bilouro/web

case "$KIND" in
  solution)
    SRC="drafts/$SLUG"; DEST="drafts/$SLUG"
    CMD="import_solution_copy --dir drafts/$SLUG --slug $SLUG"
    FILTER=(--include=copy.en.md --include=copy.pt.md --include=screens/ --include='screens/*.png' --include=screens/captions.md --exclude='*')
    ;;
  article)
    SRC="drafts/artigos/$SLUG"; DEST="drafts/artigos/$SLUG"
    CMD="import_article $SLUG"
    FILTER=(--include=article.en.md --include=article.pt.md --exclude='*')
    ;;
  *) echo "kind must be solution or article" >&2; exit 2 ;;
esac
[ -d "$SRC" ] || { echo "missing $SRC" >&2; exit 1; }

# Pages and articles may reference studio-app/screens — ship that folder too.
if grep -q 'studio-app/screens' "$SRC"/*.md 2>/dev/null; then
  EXTRA="studio-app"
fi

SSH=(ssh -i "$SSH_KEY" -o StrictHostKeyChecking=accept-new "$VM_USER@$VM_HOST")
echo "==> sync $SRC → VM"
"${SSH[@]}" "mkdir -p /tmp/content/$DEST"
rsync -az -e "ssh -i $SSH_KEY" "${FILTER[@]}" "$SRC/" "$VM_USER@$VM_HOST:/tmp/content/$DEST/"
if [ -n "${EXTRA:-}" ]; then
  "${SSH[@]}" "mkdir -p /tmp/content/drafts/$EXTRA/screens"
  rsync -az -e "ssh -i $SSH_KEY" --include='*.png' --include=captions.md --exclude='*' "drafts/$EXTRA/screens/" "$VM_USER@$VM_HOST:/tmp/content/drafts/$EXTRA/screens/"
fi

ARGS=""; for a in "$@"; do ARGS+=" $(printf '%q' "$a")"; done
echo "==> manage.py $CMD$ARGS (on VM)"
"${SSH[@]}" "sudo rsync -a /tmp/content/drafts/ $APP_DIR/drafts/ && sudo chown -R bilouro:bilouro $APP_DIR/drafts && \
  sudo -u bilouro bash -lc 'cd $APP_DIR && set -a && . /etc/bilouro.env && set +a && uv run python manage.py $CMD$ARGS'" \
  | grep -v '^Task id'
