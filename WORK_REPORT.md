# Relatório de migração + iteração — bilouro.com

**Última actualização:** 2026-05-09

---

## TL;DR

✅ **Site totalmente live em HTTPS** com 3 subdomínios + apex redirect.
✅ **Migração completa** App Runner → Lightsail.
✅ **Content em produção:** 4 tech posts, 12 projects, 2 books com posts pré-lançamento.
✅ **Deploy 1-comando**: `./scripts/deploy.sh` ou `git push` (com GH Actions activado).
✅ **SEO ready**: robots.txt, sitemap.xml, OG cards, JSON-LD Person, canonical URLs.

Endpoints:
- https://www.bilouro.com/  (home + about/CV)
- https://tech.bilouro.com/  (4 posts) + /projects/ (12 projects)
- https://books.bilouro.com/  (catálogo + 2 posts pré-lançamento agregados)
- https://bilouro.com/  → 301 → www
- https://www.bilouro.com/admin/  (admin Wagtail)

---

## Infra atual

### Lightsail (production)
- **Instance**: `bilouro-prod` em eu-west-1a, Ubuntu 24.04, micro_3_0 (1GB RAM, 2 vCPU, 40GB SSD)
- **IP estático**: `3.251.103.83`
- **Stack**: Postgres 16 + Python 3.13 (uv) + gunicorn (systemd) + nginx + Certbot
- **HTTPS**: Let's Encrypt, 4 certs (`www`, `tech`, `books`, `bilouro.com`)
- **Apex redirect**: nginx 301 `bilouro.com` → `www.bilouro.com`
- **Backup**: cron domingo 02:00 UTC, pg_dump → S3 (12-week retention)
- **Alarmes**: 3 (CPU, status check, burst capacity) → email `bilouro@bilouro.com` (precisa confirmar subscrição)

### Recursos AWS partilhados
- **S3 media** `bilouro-prod-media-eu-west-1` (Wagtail media files + backups SQL)
- **AWS Budgets** $20/$50 → alertas mensais
- **IAM user** `bilouro-cli-admin`

---

## O que está no site

### `www.bilouro.com` (autoral)
- HomePage com hero (kicker + h1 + CTAs + 3-card grid)
- AboutPage com bio + stack/skills + experience + contacts (curado, sem PII)

### `tech.bilouro.com` (developer blog)
- 4 posts publicados (still-coding + voice-agent series)
- ProjectIndexPage `/projects/` com 12 cards
- 4 posts em DRAFT (teasers + strangler-pattern) — manuais para publicar quando estiveres pronto
- RSS feed em `/feed/`

### `books.bilouro.com` (catálogo + blog pré-lançamento)
- BookCatalogPage com 2 livros (`Jesus, o Líder` PT + `Jesus, the Leader` EN)
- Agregação de posts pré-lançamento na homepage
- Cada `/books/<livro>/` mostra os posts daquele livro
- Cadência LinkedIn → blog: a cada post LinkedIn, importas via `manage.py import_posts`
- 4 posts em DRAFT prontos (Mateus 4 + Lucas 6 PT+EN) para publicação semanal

---

## Deploy process

### Atual (depois de instalado)

**1-comando local:**
```bash
./scripts/deploy.sh
```

Faz: `git push` → SSH para Lightsail → `sudo bilouro-deploy` → pull/sync/migrate/collectstatic/bootstrap/restart/health-check (com rollback automático se falha).

**GitHub Actions (auto-deploy on push):**
Workflow definido em `.github/workflows/deploy.yml` (gitignored localmente — PAT precisa de scope `workflow`).

Para activar:
```bash
gh auth refresh -s workflow
git rm --cached .github/workflows/  # remove from gitignore
# edit .gitignore to remove .github/workflows/ line
git add .github/workflows/deploy.yml .gitignore
git commit -m "ci: enable auto-deploy on push to main"
git push
```

E adicionar **2 secrets** no repo (Settings → Secrets → Actions):
- `LIGHTSAIL_SSH_KEY` = conteúdo de `~/.ssh/lightsail-bilouro.pem`
- `LIGHTSAIL_HOST` = `3.251.103.83`

Depois disso, qualquer `git push origin main` faz deploy automático com smoke test.

### Hotfix manual via SSH

Se precisares de mexer directamente:
```bash
ssh -i ~/.ssh/lightsail-bilouro.pem ubuntu@3.251.103.83
sudo bilouro-deploy           # ou commands manuais
```

---

## Comandos úteis para conteúdo

### Importar posts (LinkedIn-style ou frontmatter-style)
```bash
# Tech blog
ssh -i ~/.ssh/lightsail-bilouro.pem ubuntu@3.251.103.83 \
  "scp ... /tmp/import-posts/ && sudo -u bilouro bash -lc 'cd /opt/bilouro/web && set -a && . /etc/bilouro.env && set +a && uv run python manage.py import_posts /tmp/import-posts --parent-slug tech'"

# Books (pt/en)
... --parent-slug jesus-o-lider     # PT
... --parent-slug jesus-the-leader  # EN
```

### Publicar/despublicar posts em produção
Login no admin: https://www.bilouro.com/admin/ → Pages → encontrar post → "Publish" / "Unpublish"

### Adicionar projetos novos
Admin → Pages → tech → Projects → Add child → ProjectPage

---

## TODOs que ficam contigo

### Imediato
- [ ] **Confirmar email Lightsail** (verifica spam, "AWS Notification - Subscription Confirmation")
- [ ] **Activar snapshots automáticos** (1 clique em https://lightsail.aws.amazon.com/ls/webapp/eu-west-1/instances/bilouro-prod, Snapshots tab)
- [ ] **Login admin** e **mudar password** de `Bilouro!2026Admin` para algo robusto
- [ ] **Submeter sitemap ao Google Search Console** (passos em `SUGGESTIONS.md` §4.1)

### Esta semana
- [ ] **Activar GitHub Actions deploy** (passos acima)
- [ ] **Comprimir imagens dos posts** (PNG ~1MB → WebP <200KB) — vê `SUGGESTIONS.md` §5
- [ ] **Adicionar JSON-LD BlogPosting/Book** nos templates (eu posso fazer; ~30 min)

### Próximo mês
- [ ] Publicar 4-6 posts a partir do `linkedin/knowledge_gap/*` (ver `SUGGESTIONS.md` §2)
- [ ] Adicionar `/cv/` page com link para PDF
- [ ] Definir plano newsletter (Buttondown / Resend)

---

## Custos mensais

```
Lightsail micro_3_0:        $7.00
Lightsail snapshots auto:   $0.50  (após activares)
S3 media + backups SQL:     <$0.50
AWS Budgets/alarms:         $0
─────────────────────────────────
TOTAL:                      ~$8/mês
```

vs. App Runner stack ~$22-25/mês. **Poupança de ~60%.**

---

## Documentos relacionados

- [README.md](README.md) — desenvolvimento local
- [DNS_LOCAWEB.md](DNS_LOCAWEB.md) — instruções DNS Locaweb (referência)
- [SUGGESTIONS.md](SUGGESTIONS.md) — sugestões de conteúdo, SEO, novas secções
- [scripts/](scripts/) — provisioning, deploy, backup, certbot
- [infra/terraform/](infra/terraform/) — apenas S3 media + Budgets (App Runner stack destroyed)
