# DNS — Configuração na Locaweb

Instruções para apontar **bilouro.com** ao site App Runner sem partir o Google Workspace.

---

## 🎯 Objetivo

Adicionar **9 registos CNAME** no painel DNS da Locaweb para que:
- `www.bilouro.com` → site (vertente autoral + CV)
- `tech.bilouro.com` → blog tech
- `books.bilouro.com` → catálogo de livros
- HTTPS funcione automaticamente (cert AWS ACM)

E **NÃO mexer** em nada do Google Workspace (email continua a funcionar).

---

## ⚠️ O que NUNCA tocar

Estes registos pertencem ao **Google Workspace** — se removeres, o email pára:

- `MX` records (`aspmx.l.google.com`, `alt1.aspmx…`, etc.)
- `TXT` com `v=spf1 include:_spf.google.com`
- `CNAME` que começam com `google._domainkey…` ou `default._domainkey…` (DKIM do Google)
- `TXT` com nome `_dmarc.bilouro.com`

> **Regra de ouro:** só vais **adicionar** registos novos. Nunca editar nem apagar os existentes.

---

## 1️⃣ Registos de ROUTING (3 CNAMEs)

Estes mandam tráfego dos visitantes para o App Runner.

| Tipo | Nome | Valor | TTL |
|---|---|---|---|
| CNAME | `www` | `5isq839us4.eu-west-1.awsapprunner.com` | 300 |
| CNAME | `tech` | `5isq839us4.eu-west-1.awsapprunner.com` | 300 |
| CNAME | `books` | `5isq839us4.eu-west-1.awsapprunner.com` | 300 |

> Conforme o painel da Locaweb, em "Nome" pode pedir só `www` ou o domínio completo `www.bilouro.com`. As duas formas equivalem ao mesmo. Usa o que pede.

---

## 2️⃣ Registos de VALIDAÇÃO SSL (6 CNAMEs)

Sem isto, o cert HTTPS não é emitido pela AWS e os 3 subdomínios mostrarão erro de certificado.

São strings esquisitas (com `_<hash>` no início). Copia **exactamente** como abaixo, atenção a maiúsculas/minúsculas e pontos.

### www.bilouro.com (2 registos)

| Tipo | Nome | Valor |
|---|---|---|
| CNAME | `_7f4c62ea8e794fc66336a43962c578c2.www` | `_42c1bdd73b3b6ac86267e4e3852d47a9.jkddzztszm.acm-validations.aws` |
| CNAME | `_d4706e20c5e5901a76a74d42ea2cd26b.t0hm6ijkwws122arvaerpez6tn11kwu.www` | `_9988b2c1f72e95116f8a8c795343e3ca.jkddzztszm.acm-validations.aws` |

### tech.bilouro.com (2 registos)

| Tipo | Nome | Valor |
|---|---|---|
| CNAME | `_7091d8667060c89a9be00f1e73adac04.tech` | `_bc20ae49564c6c2a343a4087d6db00ab.jkddzztszm.acm-validations.aws` |
| CNAME | `_7adbeafa2bcd586ca0dc999941097484.1h661xmj5py1fyz9pjrpb7pdt3d98wc.tech` | `_1b81f6ae87f37a296eaa0b41c734347f.jkddzztszm.acm-validations.aws` |

### books.bilouro.com (2 registos)

| Tipo | Nome | Valor |
|---|---|---|
| CNAME | `_62e8a4b3c125e7e3b53b14a4a8e1ebf1.9iam05c5ut3dyhpz3ykorpfdtc987eq.books` | `_d1c9f12f500583bd1e6a673b603753fc.jkddzztszm.acm-validations.aws` |
| CNAME | `_d871a27d2940bc6c675b8229057dfba3.books` | `_18ee596c92afea8b1baf43f103820d3a.jkddzztszm.acm-validations.aws` |

> Se o painel Locaweb não aceitar `_underscore` no início, contacta o suporte. Os modernos aceitam normalmente.
> Se o painel exigir o **nome completo**, junta `.bilouro.com` no fim de cada "Nome" (ex.: `_7f4c62ea8e794fc66336a43962c578c2.www.bilouro.com`).

---

## 3️⃣ Apex `bilouro.com` (sem `www`) — opcional

Locaweb e a maioria dos DNS **não permitem CNAME no apex** (limitação RFC 1034). Solução recomendada:

### Opção A — URL Forwarding (mais simples)
No painel Locaweb procura **"Redirecionamento de URL"** ou **"URL Forwarding"** e configura:

```
De:   bilouro.com
Para: https://www.bilouro.com
Tipo: 301 (Permanent)
```

### Opção B — Não fazer nada
Aceitar que `bilouro.com` (sem `www`) não funciona. Visitantes que escrevam só "bilouro.com" não chegam ao site.

---

## ✅ Como verificar que está tudo certo

### 1. Após adicionar os 9 registos, espera 5-30 minutos para propagação.

### 2. Testa a propagação:
```bash
# Roteamento
dig www.bilouro.com CNAME +short
dig tech.bilouro.com CNAME +short
dig books.bilouro.com CNAME +short
# Devem responder: 5isq839us4.eu-west-1.awsapprunner.com.

# Validação ACM
dig _7f4c62ea8e794fc66336a43962c578c2.www.bilouro.com CNAME +short
# Deve responder: _42c1bdd73b3b6ac86267e4e3852d47a9.jkddzztszm.acm-validations.aws.
```

### 3. Confirma estado dos certs no AWS (de 5 em 5 min):
```bash
SVC_ARN="arn:aws:apprunner:eu-west-1:950701332313:service/bilouro-prod-web/cf1441b15acf4933ab2a472a71df146c"
aws apprunner describe-custom-domains \
  --service-arn "$SVC_ARN" \
  --profile bilouro --region eu-west-1 \
  --query 'CustomDomains[].[DomainName,Status]' --output table
```

Procuras `active` em todos. Estados intermédios:
- `pending_certificate_dns_validation` → ainda à espera dos teus DNS
- `binding_certificate` → cert emitido, a ligar ao serviço (~5 min)
- `active` → ✅ pronto

### 4. Smoke test final:
```bash
curl -I https://www.bilouro.com/
curl -I https://tech.bilouro.com/
curl -I https://books.bilouro.com/
# Todos devem responder HTTP 200
```

---

## 🟢 Quando estiver tudo `active`

Os 3 sites passam a funcionar via:
- https://www.bilouro.com/
- https://tech.bilouro.com/
- https://books.bilouro.com/

A URL provisória `https://5isq839us4.eu-west-1.awsapprunner.com/` continua a funcionar mas perde-se o sentido — usa os domínios reais.

---

## 🆘 Troubleshooting

**"Certificado inválido" no browser:**
- Faltam registos de validação ou foram colados errado. Re-confirma cada `_<hash>` no painel.

**"DNS_PROBE_FINISHED_NXDOMAIN":**
- Propagação ainda não chegou. Espera mais 5-30 min.
- Verifica que o registo está realmente no painel da Locaweb.

**"Site can't be reached" (mas DNS resolve):**
- O CNAME de routing está mal configurado. Confirma o valor `5isq839us4.eu-west-1.awsapprunner.com`.

**"Bad Request" / "Server Error" no site (DNS+HTTPS funcionam):**
- O Wagtail Site não tem este hostname configurado. O `bootstrap_sites --prod` deveria ter feito mas pode ter ficado para trás. Login no admin → Settings → Sites → confirma que existem 3 sites com hostnames `www.bilouro.com`, `tech.bilouro.com`, `books.bilouro.com`.

**Quero apagar tudo e recomeçar:**
```bash
cd /Users/victor/Documents/GitHub/bilouro-web/infra/terraform
terraform destroy
```

---

## 📞 Suporte Locaweb

Se o painel der problemas com os registos `_underscore` (raro):
- Telefone: 0800 014 1234 (BR) / +351 21 942 6500 (PT)
- Chat: dentro do painel, ícone de chat

Diz-lhes: "Quero adicionar registos `CNAME` para validação ACM da AWS, com nomes que começam por underscore (`_`)."
