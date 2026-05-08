# Relatório do autonomous run — bilouro-web

**Sessão:** ~2h trabalhadas em modo autónomo
**Data:** 2026-05-08

---

## ✅ O que está pronto

### Local
- Projecto Wagtail completo em `/Users/victor/Documents/GitHub/bilouro-web/`
- 5 apps Django (`core`, `autoral`, `tech`, `shop`, `newsletter`) com Custom User
- 6 page models: HomePage, AboutPage, BlogIndexPage, BlogPostPage, BookCatalogPage, BookPage
- 3 temas CSS distintos (autoral / tech / shop)
- Comandos `manage.py`:
  - `bootstrap_sites` (idempotente, cria 3 Wagtail Sites + AboutPage rica + BookPage placeholder)
  - `import_markdown` (LinkedIn-style + plain markdown)
- 8 posts tech importados de `linkedin/knowledge-base/posts/` (curados)
- AboutPage com headline/bio/skills/experience/contact (sem PII — sem telefone/morada/CEP/email pessoal)
- BookPage placeholder "Jesus, o Líder"
- Postgres 16 local via docker-compose
- Dev server: http://localhost:8001 — verificado HTTP 200 nos 3 sites + admin
- Superuser local: **`admin` / `admin`**

### Git/GitHub
- Repo privado: https://github.com/bilouro/bilouro-web
- 2 commits pushados

### AWS infra (Terraform aplicado)
| Recurso | ID/Nome |
|---|---|
| Account | `950701332313` |
| Region | `eu-west-1` (Irlanda) |
| Profile | `bilouro` |
| ECR repo | `bilouro-prod-web` |
| RDS Postgres | `bilouro-prod-pg` (db.t4g.micro, 16.13, **privado**) |
| S3 media | `bilouro-prod-media-eu-west-1` |
| Secrets Manager | `bilouro-prod/db-url`, `bilouro-prod/django-secret-key` |
| IAM roles | `bilouro-prod-apprunner-{ecr-access,instance}` |
| Security groups | RDS + App Runner VPC connector |
| Budget alerts | $20 (50/80/100% ACTUAL + 100% FORECAST) e $50 (100% ACTUAL) — emails para `bilouro@bilouro.com` |

### App Runner
- Configuração Terraform escrita (`apprunner.tf`)
- **Pendente** habilitar via `terraform apply -var enable_apprunner=true` após push da imagem ECR
- Domínios configurados via `aws_apprunner_custom_domain_association` (3: www / tech / books)

---

## 🟡 A finalizar (em progresso ou bloqueado em ti)

### 1. Build/push da imagem Docker para ECR (em curso)
A correr em background — emulação amd64 num Mac arm64 é lenta (~10-15 min). Output em `/tmp/bilouro-build.log`.

### 2. `terraform apply -var enable_apprunner=true`
Será corrido automaticamente após o push terminar.

### 3. DNS na Locaweb (TU TENS DE FAZER)

Quando o terraform apply do App Runner terminar, vou imprimir os registos. Depois disso, no painel DNS da Locaweb:

#### Registos a adicionar — 6 ao todo (3 subdomínios × 2 cada)

Para cada subdomínio (`www`, `tech`, `books`):

**(a) Registo de validação SSL** — só ativa o cert HTTPS. Vai parecer estranho (longa string `_xxxxx`). Adicionar exactamente como impresso pelo terraform.
```
Tipo: CNAME
Nome: _<hash>.www.bilouro.com
Valor: _<hash>.acm-validations.aws.
TTL:  300
```

**(b) Registo de routing** — manda o tráfego para o App Runner.
```
Tipo: CNAME
Nome: www.bilouro.com
Valor: <hash>.<region>.awsapprunner.com
TTL:  300
```

#### Apex `bilouro.com` (sem `www`)

Locaweb tipicamente **não suporta CNAME no apex** (limitação do RFC). Opções:
1. **Recomendado**: usar a função "Redirecionamento de URL" da Locaweb para `bilouro.com → https://www.bilouro.com` (301 permanent).
2. Alternativa: deixar `bilouro.com` apontando para uma página estática "redirect" da Locaweb.

#### O que NÃO tocar (Google Workspace)

❌ **Nunca remover ou modificar:**
- Registo `MX` (aspmx.l.google.com etc.)
- Registo `TXT` com `v=spf1 include:_spf.google.com`
- Registos `CNAME` que começam com `google._domainkey` ou `default._domainkey` (DKIM do Google)
- Registo `TXT` com `_dmarc`

Vais adicionar APENAS CNAMEs novos para `_<hash>.www`, `_<hash>.tech`, `_<hash>.books`, `www`, `tech`, `books`. Tudo o que já está fica.

### 4. Criar superuser de produção (TU TENS DE FAZER, ou eu faço-o se preferires)

Após primeiro deploy:
```bash
cd /Users/victor/Documents/GitHub/bilouro-web
./scripts/post_deploy_setup.sh
```
O script:
1. Adiciona o teu IP público à RDS security group temporariamente
2. Torna o RDS publicamente acessível (~30s)
3. Pede password e cria o superuser
4. Reverte tudo automaticamente

### 5. SES (transactional email)
**Não configurado** porque não há newsletter no MVP. Fica para fase 5 quando ligar a newsletter.

### 6. GitHub Actions deploy workflow
Ficheiro pronto em `/Users/victor/Documents/GitHub/bilouro-web/.github/workflows/deploy.yml` (não foi pushado — o teu PAT não tem o scope `workflow`). Para ativar:
```bash
gh auth refresh -s workflow
git add .github/workflows/deploy.yml && git commit -m "ci: GH Actions auto-deploy" && git push
```
E adicionar secrets `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` ao repo.

---

## 💰 Custos estimados

### Imediato (a partir de hoje)
- RDS db.t4g.micro: **~$0.43/dia = ~$13/mês** (free tier nos primeiros 12 meses se elegível)
- Secrets Manager: $0.40/segredo × 2 = **$0.80/mês**
- S3 + ECR: <$1/mês
- App Runner (após apply -var enable_apprunner=true): **$5-10/mês** sem tráfego (provisioned compute paused), $10-25/mês com tráfego baixo
- Custom Domains App Runner: $0

**Total realista**: $7-15/mês durante free tier; $25-40/mês depois.

### Budgets configurados
- Alert a 50%/80%/100% de **$20/mês**
- Alert extra a 100% de **$50/mês**

### Como pausar custos rapidamente
```bash
cd infra/terraform
terraform apply -var enable_apprunner=false   # para App Runner ($5-25/mês economizados)
# RDS continua a correr; para parar:
terraform destroy -target aws_db_instance.main   # destrói RDS
```

---

## 📋 Sequência de comandos para finalizar

1. **Esperar build ECR terminar** (em curso)
2. **Apply App Runner**: `cd infra/terraform && terraform apply -auto-approve -var enable_apprunner=true`
3. **Copiar registos DNS** de `terraform output dns_records_for_locaweb`
4. **Adicionar registos na Locaweb** (UI da Locaweb)
5. **Esperar propagação DNS + validação ACM** (~10-30 min)
6. **Criar superuser**: `./scripts/post_deploy_setup.sh`
7. **Smoke test**:
   ```bash
   curl -I https://www.bilouro.com/
   curl -I https://tech.bilouro.com/
   curl -I https://books.bilouro.com/
   ```
8. **Login admin**: `https://www.bilouro.com/admin/`

---

## 🔧 Problemas conhecidos / TODOs

- `bilouro.com` apex precisa de redirect manual na Locaweb (CNAME-no-apex)
- Newsletter não implementada (Fase 5)
- Pagamentos: `BookPage.buy_url` está vazio (Fase 6)
- GH Actions workflow precisa de `workflow` scope no PAT para auto-deploy
- Tema "tech" — body é renderizado como `linebreaks` simples, não com markdown rendering avançado nem syntax highlighting (basta para já)
- `wagtail-localize` instalado mas i18n PT/EN não configurado nas páginas ainda (placeholder estrutura)

---

## 📁 Estrutura final

```
bilouro-web/
├── apps/
│   ├── core/         Custom User + bootstrap_sites command
│   ├── autoral/      HomePage, AboutPage
│   ├── tech/         BlogIndexPage, BlogPostPage + import_markdown command
│   ├── shop/         BookCatalogPage, BookPage
│   └── newsletter/   placeholder
├── config/
│   ├── settings/{base,dev,prod}.py
│   └── urls.py · wsgi.py · asgi.py
├── templates/
│   ├── _base.html
│   ├── autoral/{base,home_page,about_page}.html
│   ├── tech/{base,blog_index_page,blog_post_page}.html
│   └── shop/{base,book_catalog_page,book_page}.html
├── static/css/{_base,autoral,tech,shop}.css
├── infra/terraform/
│   ├── versions.tf · variables.tf · main.tf
│   ├── budget.tf · ecr.tf · rds.tf · s3.tf
│   ├── secrets.tf · iam.tf
│   ├── apprunner.tf · domains.tf
│   ├── outputs.tf
│   └── README.md
├── scripts/
│   ├── deploy.sh             build + push + apply
│   └── post_deploy_setup.sh  one-time superuser via temporary RDS access
├── Dockerfile                multi-stage (uv + gunicorn)
├── docker-compose.yml        local Postgres + optional web
├── pyproject.toml            uv + ruff + djlint
├── README.md
└── DEPLOY_REPORT.md          (este ficheiro)
```
