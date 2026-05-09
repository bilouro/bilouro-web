# Relatório de migração — App Runner → Lightsail

**Data:** 2026-05-09
**Sessão:** Autónoma

---

## TL;DR

Site **bilouro.com** migrado de AWS App Runner (~$22/mês) para **AWS Lightsail VM** (~$8/mês).
DNS já apontado para o Lightsail. Apenas falta:
1. Aguardar propagação DNS final (em curso) → Certbot emite certs HTTPS
2. Validares HTTPS nos 3 subdomínios + apex
3. Desligar App Runner com 1 comando Terraform

Conteúdo expandido: 2 livros (PT+EN) "Jesus, o Líder" / "Jesus, the Leader" + 6 posts pré-lançamento (3 PT + 3 EN). 8 posts no tech blog (com imagens onde existem).

---

## Infra ATUAL

### Lightsail (novo, ATIVO)
- **Instance**: `bilouro-prod` em eu-west-1a
- **Plan**: `micro_3_0` (1GB RAM, 2 vCPU, 40GB SSD) → **$7/mês**
- **OS**: Ubuntu 24.04 LTS
- **IP estático**: `3.251.103.83`
- **Stack**: Postgres 16 + Python 3.13 (uv) + gunicorn (systemd) + nginx + Certbot
- **Apex redirect**: `bilouro.com` → `https://www.bilouro.com` (301 via nginx)
- **Backup**: cron domingo 02:00 UTC, `pg_dump` → `s3://bilouro-prod-media-eu-west-1/backups/postgres/`, retém 12 semanas
- **Alarmes Lightsail**: CPU>80%, StatusCheckFailed, BurstCapacity<20% → email `bilouro@bilouro.com`
- **Contact email**: `PendingVerification` ⚠️ — **precisas confirmar** subscription via email enviado pela AWS

### App Runner (antigo, AINDA ATIVO até validação)
- Service `bilouro-prod-web` em eu-west-1
- Custom domains www/tech/books — agora sem tráfego (DNS já aponta para Lightsail)
- Custo: ~$5-10/mês enquanto não desligares

### Recursos AWS partilhados (ficam)
- **S3 bucket** `bilouro-prod-media-eu-west-1` — media files do Wagtail (continua a funcionar do Lightsail)
- **RDS Postgres** `bilouro-prod-pg` — não usado pelo Lightsail (Postgres está local na VM); **podes destruir** depois de validares migração
- **ECR** `bilouro-prod-web` — não usado pelo Lightsail; **podes destruir** depois
- **Secrets Manager** entries — não usados pelo Lightsail; **podes destruir** depois
- **CloudWatch alarms** (4) — só relevantes para App Runner; **podes apagar** depois
- **AWS Budget** $20/$50 — manter sempre

---

## Conteúdo do site

### `www.bilouro.com` (autoral)
- HomePage com headline + bio
- AboutPage com CV curado (sem PII): bio, stack, experience, contact links

### `tech.bilouro.com` (developer blog)
- 8 posts importados de `linkedin/knowledge-base/posts/` (com imagens onde os PNGs existem):
  - `01-still-coding-after-15-years` (post01.png)
  - `02-voice-agent-overview` (post-2.png)
  - `02b-voice-agent-smb-teaser`
  - `03-voice-agent-architecture` (post-03.png)
  - `03b-voice-agent-model-decisions-teaser`
  - `04-voice-agent-build-vs-buy` (post04.png)
  - `04b-voice-agent-build-vs-buy-teaser`
  - `05-strangler-pattern` (sem PNG associado)

### `books.bilouro.com` (catálogo + blog pré-lançamento)
- **2 livros**, ambos `coming_soon=True`:
  - **"Jesus, o Líder"** (PT) com 3 posts importados de `book_jesus_lider/posts/pt/`
  - **"Jesus, the Leader"** (EN) com 3 posts importados de `book_jesus_leader/posts/en/`
- Cada post tem imagem (PNG do mesmo dia da publicação LinkedIn)

### Workflow definido
A cada post LinkedIn publicado, fazes:
```bash
ssh -i ~/.ssh/lightsail-bilouro.pem ubuntu@3.251.103.83 \
  'sudo -u bilouro bash -lc "cd /opt/bilouro/web && set -a && . /etc/bilouro.env && set +a && \
  uv run python manage.py import_posts /path/to/new/post --parent-slug jesus-o-lider"'
```
(idealmente automatiza via GitHub Actions ou outro processo).

---

## O que tu fazes para finalizar

### 1️⃣ Confirmar email Lightsail (agora)
Vai ao inbox `bilouro@bilouro.com` e clica em "Confirm subscription" no email "AWS Notification - Subscription Confirmation" (vai para 2 emails: 1 do CloudWatch SNS + 1 do Lightsail).

### 2️⃣ Activar snapshots automáticos (1 clique)
🔗 https://lightsail.aws.amazon.com/ls/webapp/eu-west-1/instances/bilouro-prod
- Tab **Snapshots** → "Enable automatic snapshots"
- Mantém o default (00:00 UTC, 7 dias retenção)
- Custo: ~$0.50/mês

### 3️⃣ Esperar propagação DNS + Certbot (em curso)
A propagação DNS final está em curso no momento da escrita deste relatório. O retry loop do Certbot está activo e vai emitir os certs assim que o Let's Encrypt resolver chegar a `3.251.103.83` em todos os 3 subdomínios.

Quando vires o site responder em `https://www.bilouro.com/` no browser, está pronto.

### 4️⃣ Validar HTTPS
```bash
curl -I https://www.bilouro.com/
curl -I https://tech.bilouro.com/
curl -I https://books.bilouro.com/
curl -I http://bilouro.com/        # 301 → https://www.bilouro.com/
```
Todos devem responder `HTTP/2 200` (ou 301 para o apex).

### 5️⃣ Desligar App Runner (depois de validares)
```bash
cd /Users/victor/Documents/GitHub/bilouro-web/infra/terraform
terraform apply -auto-approve -var enable_apprunner=false
```
Isto remove App Runner Service + Custom Domain Associations + VPC Connector.

### 6️⃣ (Opcional) Destruir recursos AWS não-usados
Depois de uns dias a confirmar que tudo funciona:
```bash
# Destrói RDS, ECR, Secrets — perde-os
terraform destroy -target aws_db_instance.main \
                  -target aws_ecr_repository.web \
                  -target aws_secretsmanager_secret.db_url \
                  -target aws_secretsmanager_secret.django_secret_key
```
Ou destruir tudo:
```bash
terraform destroy
```

### 7️⃣ Login admin e MUDAR PASSWORD
```
URL:      https://www.bilouro.com/admin/
Username: admin
Password: Bilouro!2026Admin
```
Vai a Settings → Users → admin → Change password. **Faz isto já**.

---

## Arquivos importantes do repo

| Path | Para quê |
|---|---|
| `DNS_LOCAWEB.md` | Instruções DNS detalhadas (passo a passo) |
| `WORK_REPORT.md` | Este ficheiro — visão geral |
| `scripts/lightsail_provision.sh` | Bootstrap inicial Ubuntu |
| `scripts/lightsail_app_setup.sh` | Clone + venv + systemd + nginx |
| `scripts/lightsail_run_certbot.sh` | Emitir certs Let's Encrypt + swap nginx para HTTPS |
| `scripts/lightsail_backup.sh` | Cron `pg_dump` → S3 (instalado em `/usr/local/bin/bilouro-backup`) |
| `scripts/cloud_build.sh` | Para App Runner (legacy) — descontinuar quando shutdown |
| `apps/core/management/commands/import_posts.py` | Importar posts LinkedIn-style ou frontmatter-style com imagens |
| `apps/core/management/commands/bootstrap_sites.py` | Idempotente — cria 3 sites + 2 livros + AboutPage |
| `infra/terraform/` | Toda a infra App Runner — vai-se descontinuar gradualmente |

---

## Custos estimados (pós-migração)

### Imediato (App Runner ainda a correr)
- App Runner: ~$5-10/mês
- Lightsail: $7/mês
- Outros: ~$1/mês
- **Total**: ~$13-18/mês — temporário durante validação

### Após desligar App Runner
- Lightsail: $7/mês
- Snapshots: $0.50/mês
- Backup S3: <$0.10/mês
- S3 (media): <$1/mês
- Domain registration (Locaweb): ~$1/mês equivalente
- **Total**: ~$9/mês

### Após `terraform destroy` (cleanup completo)
- Lightsail + S3 media + Snapshots: ~$8/mês
- Domain registration: ~$1/mês
- **Total**: ~$9/mês

Poupança vs. App Runner stack: ~$10-15/mês (~30%).

---

## Decisões / Trade-offs assumidos

1. **Lightsail VM em vez de Container Service**: 4× mais barato, sem auto-scaling. Aceitável para tráfego baixo/médio.
2. **Postgres local, não managed**: $13/mês de poupança vs RDS. Backup semanal mitiga risco.
3. **Sem CloudFront**: latência directa para a VM em Irlanda (ok para PT/EU). Adicionar CloudFront depois se necessário.
4. **HTTPS via Let's Encrypt + Certbot**, não AWS ACM: gratuito, auto-renew via cron Certbot.
5. **Apex redirect via nginx 301**, não DNS-level: rápido, sem dependência de outro provedor.
6. **Backup via cron na VM**, não Lambda: Postgres está local na VM, Lambda exigiria expor a porta — cron mais simples.

---

## Limitações que o utilizador deve saber

- **Sem auto-scaling**: se viralizar, sobe traffic à mão (resize bundle no Lightsail). Hint: $10/mês plan é 2GB RAM + same vCPUs.
- **Single point of failure**: se a VM cair, site cai. Snapshots permitem recovery.
- **Postgres self-managed**: tu (ou cron + alarmes) responsabilizas por upgrades major.
- **Apex** `bilouro.com` mantém um cert separado (Let's Encrypt). Renovação automática via Certbot.

---

## TODOs futuros (não bloqueantes)

- [ ] Adicionar GitHub Actions para auto-deploy on push (substituir cloud_build.sh + manual SSH)
- [ ] Sentry ou similar para tracking de erros
- [ ] Plausible Analytics ($9/mês ou self-host)
- [ ] Newsletter (Buttondown / Resend) — fase 5 do plano original
- [ ] Loja real (Gumroad/Lemon Squeezy) quando o livro lançar
- [ ] i18n PT/EN com `wagtail-localize` — está instalado, ainda não configurado nos modelos
- [ ] CloudFront na frente do Lightsail (se quiseres CDN global)
- [ ] Migrar DNS para Route 53 ou Cloudflare se decidires deixar Locaweb
