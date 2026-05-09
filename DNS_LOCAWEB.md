# DNS — Migração para Lightsail (substitui App Runner)

Este doc cobre **a migração** de DNS do App Runner para o Lightsail.
Estavas a apontar para `5isq839us4.eu-west-1.awsapprunner.com` (App Runner).
Vamos passar a apontar para o **IP estático Lightsail**: `3.251.103.83`.

---

## ✅ Estado actual da nova infra

| Item | Estado |
|---|---|
| Lightsail VM `bilouro-prod` | ✅ ligada (Ubuntu 24.04, micro_3_0, 1GB RAM, $7/mês) |
| IP estático | ✅ `3.251.103.83` (anexado, free enquanto attached) |
| Postgres 16 + Wagtail | ✅ a correr (gunicorn @ systemd) |
| nginx | ✅ HTTP only por agora (HTTPS depois do DNS) |
| 3 sites Wagtail | ✅ www / tech / books configurados com hostnames de prod |
| Apex redirect | ✅ `bilouro.com` → `www.bilouro.com` (301) |
| Backup semanal SQL → S3 | ✅ cron domingo 02:00 UTC, retém 12 semanas |
| Snapshots automáticos | ⚠️ é só configurar via console (1 clique — passos abaixo) |
| Lightsail alarmes | ✅ CPU>80%, StatusCheckFailed, BurstCapacity<20% — emails para `bilouro@bilouro.com` (precisa **confirmar** subscrição via email) |
| Superuser admin | ✅ `admin` / `<see your password store>` (muda já após login) |

> ⚠️ App Runner continua a correr e a ser servido via HTTPS válido. Custo continua. Só é desligado **depois** de validares que o Lightsail está a servir tudo bem.

---

## 🧪 Como testar o Lightsail antes do DNS migrar

A nova VM serve via Host header. Testa pelos comandos:

```bash
curl -I -H "Host: www.bilouro.com" http://3.251.103.83/
curl -I -H "Host: tech.bilouro.com" http://3.251.103.83/
curl -I -H "Host: books.bilouro.com" http://3.251.103.83/
curl -I -H "Host: bilouro.com" http://3.251.103.83/   # esperado 301 para www
```

Os 4 devem responder. Para testares no browser sem mexer no DNS, edita `/etc/hosts`:

```bash
sudo tee -a /etc/hosts >/dev/null <<EOF
3.251.103.83 www.bilouro.com tech.bilouro.com books.bilouro.com bilouro.com
EOF
```

(Lembra-te de remover esta linha do `/etc/hosts` antes de migrar DNS.)

---

## 🔵 Passo 1 — DNS na Locaweb (substitui os 9 registos App Runner)

### Registos a APAGAR (App Runner antigos)

Estes 9 registos estão actualmente no painel — todos com valor que aponta para `awsapprunner.com` ou `acm-validations.aws`:

```
www                           CNAME  5isq839us4.eu-west-1.awsapprunner.com
tech                          CNAME  5isq839us4.eu-west-1.awsapprunner.com
books                         CNAME  5isq839us4.eu-west-1.awsapprunner.com
_<hash>.www                   CNAME  _<hash>.acm-validations.aws         (×2)
_<hash>.tech                  CNAME  _<hash>.acm-validations.aws         (×2)
_<hash>.books                 CNAME  _<hash>.acm-validations.aws         (×2)
```

**Apaga os 9.** Os de validação ACM já não fazem sentido (Lightsail usa Let's Encrypt).

### Registos a CRIAR (Lightsail)

```
www      A      3.251.103.83
tech     A      3.251.103.83
books    A      3.251.103.83
@/.      A      3.251.103.83     ← apex bilouro.com (registo "raiz")
```

**TTL**: 300 ou 1h. **4 registos A** apenas. Sem CNAMEs novos. Sem `_underscore`.

> 🔑 No painel da Locaweb, "Nome" pode ser `www` ou `www.bilouro.com` conforme o painel. Para o apex, costuma ser `@`, `.` ou deixar em branco. Se ficar em dúvida, contacta o suporte ("preciso de adicionar um registo A no domínio raiz `bilouro.com` apontando para `3.251.103.83`").

### Registos a NÃO TOCAR

❌ MX (`aspmx.l.google.com` etc.)
❌ TXT `v=spf1 include:_spf.google.com`
❌ CNAMEs `google._domainkey…` ou `default._domainkey…`
❌ TXT `_dmarc`

---

## 🟡 Passo 2 — Esperar propagação (~5-30 min)

```bash
# Verifica que cada subdomínio resolve para 3.251.103.83
dig +short www.bilouro.com A @1.1.1.1
dig +short tech.bilouro.com A @1.1.1.1
dig +short books.bilouro.com A @1.1.1.1
dig +short bilouro.com A @1.1.1.1
# Todos devem responder: 3.251.103.83
```

Quando `dig` mostrar `3.251.103.83` em todos, podes prosseguir.

---

## 🟢 Passo 3 — Emitir certs HTTPS no Lightsail

SSH para a VM e corre o script de Certbot:

```bash
ssh -i ~/.ssh/lightsail-bilouro.pem ubuntu@3.251.103.83
./lightsail_run_certbot.sh
```

O script:
1. Pede certs Let's Encrypt para `www`, `tech`, `books` (uma SAN cert) e para `bilouro.com`
2. Substitui o config nginx para o HTTPS-completo
3. Reinicia o app com `SECURE_SSL_REDIRECT=True`
4. Reload nginx

Cron de auto-renovação (Certbot já configura via apt; corre 2x/dia, renova 30 dias antes de expirar).

### Verifica HTTPS

```bash
curl -I https://www.bilouro.com/
curl -I https://tech.bilouro.com/
curl -I https://books.bilouro.com/
curl -I http://bilouro.com/        # 301 → https://www.bilouro.com/
```

---

## 🔻 Passo 4 — Desligar App Runner (só DEPOIS de validares Passo 3)

Os 3 subdomínios devem responder em HTTPS via Lightsail. Login admin deve funcionar em `https://www.bilouro.com/admin/` com `admin` / `<see your password store>`.

Quando confirmares que está tudo a funcionar:

```bash
cd /Users/victor/Documents/GitHub/bilouro-web/infra/terraform
terraform apply -auto-approve -var enable_apprunner=false
```

Isto desliga App Runner + remove Custom Domain associations. **Mantém** RDS, S3, Secrets, ECR, CodeBuild, Budgets — em caso de querer voltar.

Para desligar tudo:
```bash
terraform destroy
```
(Antes vê `terraform plan -destroy` para perceberes o impacto.)

---

## 🔔 Snapshots automáticos (1 clique no console)

Vai a https://lightsail.aws.amazon.com/ls/webapp/eu-west-1/instances/bilouro-prod
- Tab **Snapshots**
- "Enable automatic snapshots"
- Hora preferida (UTC). Default 00:00 UTC.
- Custo: ~$0.05/GB/mês × 7 dias retenção (default) ≈ $0.50/mês

(Não consegui automatizar via CLI — Lightsail não expõe esse comando. Console-only.)

---

## 📂 Ficheiros úteis no repo

| Path | Para quê |
|---|---|
| `scripts/lightsail_provision.sh` | bootstrap inicial Ubuntu (apt, postgres, uv, etc.) |
| `scripts/lightsail_app_setup.sh` | clona repo, instala deps, systemd, nginx (run uma vez) |
| `scripts/lightsail_run_certbot.sh` | passo 3 acima — emite cert e activa HTTPS |
| `scripts/lightsail_backup.sh` | semanal pg_dump → S3 (instalado em `/usr/local/bin/bilouro-backup`) |

## 🔁 Redeploy futuro (depois de mudar código)

```bash
ssh -i ~/.ssh/lightsail-bilouro.pem ubuntu@3.251.103.83 '
sudo -u bilouro git -C /opt/bilouro/web pull --ff-only
sudo -u bilouro bash -lc "cd /opt/bilouro/web && uv sync --no-dev"
sudo -u bilouro bash -lc "cd /opt/bilouro/web && set -a && . /etc/bilouro.env && set +a && uv run python manage.py migrate --noinput && uv run python manage.py collectstatic --noinput"
sudo systemctl restart bilouro-web
'
```

(Idealmente isto vira um `scripts/lightsail_deploy.sh` ou um GitHub Actions later.)

---

## 💰 Custos comparados

| Item | App Runner (atual) | Lightsail (novo) |
|---|---|---|
| Compute | $5-10/mês | $7/mês fixo |
| RDS Postgres | $13/mês (ou free tier 12m) | $0 (na mesma VM) |
| Secrets Manager | $0.80/mês | $0 (env file) |
| S3 + ECR | <$1/mês | <$1/mês (S3 mantém-se) |
| Snapshots | — | ~$0.50/mês |
| Backups SQL → S3 | — | <$0.10/mês |
| **Total** | **$18-25/mês** | **~$8/mês** |

Poupança estimada: ~$10-15/mês (pós free tier).

---

## ⚠️ Limitações vs App Runner

- **Sem auto-scaling**: se viralizar, sobe traffic à mão (resize bundle no Lightsail).
- **Cold start ausente** (Lightsail nunca dorme).
- **Single point of failure**: se a VM cair, site cai. Snapshots + alarmes mitigam.
- **Postgres self-managed**: tu fazes backup (cron já configurado), recovery, upgrades major.

Para a tua escala atual (~10-100 visitas/dia), trade-off vale a pena.

---

## 🧯 Troubleshooting

**"Site can't be reached" após migração DNS**:
- DNS ainda a propagar. `dig +short www.bilouro.com` deve mostrar `3.251.103.83`.

**Certbot falha com "Failed authorization procedure"**:
- DNS não propagou completamente; espera mais 10-30 min.

**HTTP 502 no site**:
- gunicorn não está a correr. SSH e `sudo systemctl status bilouro-web` + `sudo journalctl -u bilouro-web -n 50`.

**HTTPS dá "Your connection is not private"**:
- Cert não foi emitido ainda. Corre `./lightsail_run_certbot.sh` no VM.

**Email Lightsail não chega**:
- Confirma a subscrição no email "AWS Lightsail Notifications - Subscription Confirmation" (verifica spam).
