# Sugestões de conteúdo + indexação Google

Sessão de avaliação profunda dos repos GitHub + `linkedin/` + perfil profissional para definir o que pode ir para `tech.bilouro.com`.

---

## 1. O que já está no site (estado atual)

### tech.bilouro.com
- **4 posts** (de 8 importados; teasers + draft mantidos como unpublished):
  1. After 15 years leading teams, I still commit every week
  2. Voice agent on the phone for a Pilates studio
  3. Model choices that defined our voice agent
  4. Build vs buy your AI voice agent? Wrong question.
- **12 projects**: Kuehne+Nagel CMD modernization, Voice Agent SMB, Email Agent, Release Automation Stack, BookBuilder, bilouro-web, cookbook, querysetget, sgsb, SGUI, Arduino Coding Dojo, GSoC 2008.

### books.bilouro.com
- 2 livros (PT + EN, coming_soon)
- 2 posts pré-lançamento publicados (1 PT + 1 EN, kickoff João 13)
- 4 posts adicionais como **draft** (Mateus 4 + Lucas 6 PT/EN — para publicar nas próximas terças/quintas)

### www.bilouro.com
- Home com hero
- About com bio + skills + experience + contacts (curado, sem PII)

---

## 2. Conteúdo que recomendo adicionar ao tech (próximos meses)

### Posts (a partir do que já tens em `linkedin/knowledge-base/`)

| Prioridade | Tema | Source para usar | Tipo |
|---|---|---|---|
| **A** | "The Strangler That Saved Six Months of Downtime" | `posts/05-strangler-pattern.md` (já em draft) | Publicar no LinkedIn + tech blog |
| **A** | Workflow de Wagtail+gunicorn+nginx no Lightsail (este projecto) | DEPLOY_REPORT.md + WORK_REPORT.md | Tutorial técnico |
| **A** | "From App Runner to Lightsail: $22 → $8/mo migration" | Histórico desta sessão | Caso real |
| **B** | "Postgres 16 backup com cron, pg_dump e S3" | scripts/lightsail_backup.sh | Tutorial mini |
| **B** | "Rate-limiting Let's Encrypt: o que aprendi a esmurrar Certbot" | Logs desta sessão | War story |
| **C** | Conteúdo de `knowledge_gap/` — cada gap escrito como série de aprendizagem | knowledge_gap/*.md | Série "Learning in Public" |

### Knowledge gaps que dão posts excelentes
Da pasta `linkedin/knowledge_gap/`, cada um pode virar 1-2 posts:
- **Apache Airflow** → "Choosing between Airflow, Prefect and dbt for ETL"
- **Apache Spark** → "Spark on AWS EMR vs. Databricks: cost analysis"
- **Databricks** → "Databricks Lakehouse: when does it actually win?"
- **dbt** → "dbt + Postgres: when you don't need Snowflake"
- **GCP BigQuery** → "BigQuery vs Athena vs Redshift for SMB analytics"
- **MLOps** → "MLOps without Sagemaker: a stack from scratch"
- **LangChain** → "Why I built voice agents WITHOUT LangChain"
- **TensorFlow/PyTorch** → "TF vs PyTorch in 2026 (post-Transformers era)"
- **Industrial protocols / HMI** → série específica (nicho mas raro online)

### Histórias da carreira que valem post
Do `knowledge-base/02-experiencia-profissional.md`:
- Kuehne+Nagel monolith → microservices (já tens projeto + posts; podes expandir com 3-4 posts técnicos)
- Azul Seguros: Oracle PL/SQL migration
- Leroy Merlin (Ytech): order management + CI/CD
- Natixis: financial services automation

---

## 3. Secções novas que sugiro

### A. **Newsletter** (futuro)
Quando tiveres ~30+ posts e leitores. Buttondown ou Resend (free tier 3k subs). Já tens domínio email Workspace; SES configurar para sending.

### B. **Now page** (`/now/`)
Página estilo "What I'm doing now" — currently working on, learning, reading. Trends: nownownow.com tem listagem.

### C. **Talks / Speaking**
Se vais palestrar (ou já palestraste — `08-conquistas-palestras.md` tem refs), página dedicada com slides + vídeos.

### D. **Reading list** (`/reading/`)
Livros lidos com nota curta. Útil para SEO e personal branding.

### E. **`uses` page** (`/uses/`)
"My setup" — hardware + software. Trend gigante na comunidade dev. Ver uses.tech.

### F. **`/cv/` page com PDF**
Versão PDF do CV técnico (já existe em `linkedin/knowledge-base/cv-tech-v2.pdf`). Página HTML + link de download. Útil para recrutadores.

### G. **Blog comments** (futuro)
Disqus ou Giscus (GitHub Discussions). Adicionar quando audience justificar.

---

## 4. Indexação Google (passos que precisas fazer)

### Passos automatizados (✅ feito)
- [x] `robots.txt` em todas as 3 origens
- [x] `sitemap.xml` em todas as 3 origens (Wagtail Sitemap built-in)
- [x] Meta description, canonical, OG tags em todas as páginas
- [x] JSON-LD Person schema na home
- [x] HTTPS válido
- [x] Mobile-responsive (CSS responsive)
- [x] Cross-linking entre subdomínios via footer (`_cross_nav.html`)
- [x] Page titles únicos por página
- [x] Heading hierarchy (h1, h2, h3)

### Passos manuais que tu fazes

#### 1. Google Search Console (15 min)
1. Vai a https://search.google.com/search-console
2. Click "Add property"
3. Adiciona **3 properties separadas** (uma por subdomínio):
   - `https://www.bilouro.com`
   - `https://tech.bilouro.com`
   - `https://books.bilouro.com`
4. Verifica via DNS TXT record (mais fácil) — Google dá-te uma string `google-site-verification=...`
   - Adiciona no painel Locaweb como TXT record (não interfere com Google Workspace)
5. Em cada property, "Sitemaps" → submete `sitemap.xml`
6. "URL Inspection" → testa cada URL principal para forçar crawl

#### 2. Bing Webmaster Tools (10 min)
1. https://www.bing.com/webmasters
2. Verifica os 3 subdomínios
3. Submete sitemaps

#### 3. Estabelece sinais externos
- Adiciona links bilouro.com no teu **LinkedIn profile** (about + featured)
- Tweet 1× anunciando os subdomínios + reposts cada artigo
- Submete posts a aggregators relevantes (Hacker News, Lobsters, dev.to)

#### 4. Schema markup adicional (já preparado)
- **Person** schema na home ✅
- **BlogPosting** schema nos posts (TODO no template — fácil de adicionar)
- **Book** schema nas BookPages (TODO)
- **CollectionPage** no `/projects/` (TODO)

Posso adicionar os 3 acima se quiseres — ~30 min de template work.

---

## 5. Quick wins para SEO (próximas semanas)

| Acção | Esforço | Impacto |
|---|---|---|
| Submeter sitemaps ao Google Search Console | 15 min | Alto — começa indexação |
| Adicionar BlogPosting JSON-LD nos posts | 20 min | Médio — rich snippets |
| Comprimir imagens (atualmente PNGs ~1MB) | 30 min | Alto — Core Web Vitals |
| Adicionar lazy loading nas imagens (`loading="lazy"`) | 5 min | Médio — LCP |
| OG image dedicada (não a PNG do post) | 1h | Médio — share preview |
| Cabeçalho `Cache-Control` na nginx para CSS/imagens | 5 min | Médio — perf score |
| Pre-render homepage (Wagtail static export?) | 2h | Alto — TTFB |
| Adicionar Plausible Analytics | 30 min | Baixo (privacy-first) |

---

## 6. Conteúdo de PROJETOS — recomendações para enriquecer

Os 12 projects estão como cartões; podes:

- **Adicionar imagens hero** a cada (screenshots ou diagramas). Se tiveres screenshots dos sistemas, basta upload via admin → ProjectPage → Image.
- **Expandir descrição** dos projects "work" (CMD, Release Automation) com diagramas de arquitectura — sem expor info confidencial. Estilo "redacted case study".
- **Tags** (já existe campo `tech_stack`). Considerar adicionar filtros por tag na grid.
- **Métricas** quando relevante: linhas de código, no. de devs no time, runtime stats. Adiciona credibilidade.

---

## 7. Conteúdo a NÃO colocar (privado / estratégico)

Do `linkedin/`:
- ❌ `applies/*` — candidaturas a vagas (privado)
- ❌ `anti-targets.md` — conteúdo estratégico negativo
- ❌ Telefone, email pessoal, CEP, morada exacta — manter sempre PII fora
- ❌ Profile.pdf como está (tem PII; CV-tech-v2 está OK porque foi curado)
- ❌ Detalhes confidenciais de projetos work (Kuehne+Nagel, etc.) — expor lições, não detalhes

---

## 8. Priorização final (o que fazer na próxima semana)

```
Hoje (1h):       Google Search Console setup (verificar 3 subdomínios + submit sitemap)
Esta semana (4h): Comprimir imagens + JSON-LD posts + OG images + Plausible
Mês 1:            Publicar 4-6 posts dos knowledge_gap; expandir CMD case study
Mês 2:            Adicionar /cv/, /uses/, /now/
Mês 3:            Newsletter setup quando atingires 50+ subscribers no LinkedIn
```
