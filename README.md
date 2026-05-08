# bilouro-web

Wagtail multi-site for **bilouro.com**, with three subdomains:

| Subdomain | App | Purpose |
|---|---|---|
| `www.bilouro.com` | `apps.autoral` | Landing + About / CV |
| `tech.bilouro.com` | `apps.tech` | Developer blog (markdown posts) |
| `books.bilouro.com` | `apps.shop` | Book catalogue + product pages |

## Stack

- Python 3.13 · Django 5.2 · Wagtail 7
- Postgres 16 · Gunicorn · WhiteNoise
- Dependency manager: **uv**
- Lint/format: **ruff** (replaces black) · **djlint** for templates
- Container: multi-stage Dockerfile
- Hosting (planned): AWS App Runner + RDS + S3 + CloudFront + SES

## Setup (local)

```bash
# 1. Install uv (one-time)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Install dependencies (creates .venv automatically)
uv sync

# 3. Start Postgres
docker compose up -d db

# 4. Copy env defaults
cp .env.example .env

# 5. Migrate + create superuser
uv run python manage.py migrate
uv run python manage.py createsuperuser

# 6. Run dev server
uv run python manage.py runserver
```

Open http://localhost:8000/admin/ to manage content.

## Multi-site setup (one-time, in admin)

After first migration, create three Wagtail Sites in `/admin/sites/`:

| Hostname (local) | Hostname (prod) | Root page |
|---|---|---|
| `www.localhost` | `www.bilouro.com` | `HomePage` |
| `tech.localhost` | `tech.bilouro.com` | `BlogIndexPage` |
| `books.localhost` | `books.bilouro.com` | `BookCatalogPage` |

Add to `/etc/hosts` for local subdomain testing:

```
127.0.0.1 www.localhost tech.localhost books.localhost
```

## Importing content from `linkedin/knowledge-base/posts/`

```bash
uv run python manage.py import_markdown \
    /Users/victor/Documents/GitHub/linkedin/knowledge-base/posts \
    --parent-slug tech-blog
```

## Running with Docker (mirrors production)

```bash
docker compose --profile full up --build
```

## Project layout

```
bilouro/
├── apps/
│   ├── core/        Custom User, helpers
│   ├── autoral/     HomePage, AboutPage  (www)
│   ├── tech/        BlogIndexPage, BlogPostPage  (tech)
│   ├── shop/        BookCatalogPage, BookPage  (books)
│   └── newsletter/  placeholder for Phase 5
├── config/
│   ├── settings/    base / dev / prod
│   ├── urls.py
│   └── wsgi.py · asgi.py
├── templates/       _base.html + per-vertical bases
├── static/css/      autoral.css · tech.css · shop.css
├── infra/terraform/ AWS infrastructure as code
├── Dockerfile       multi-stage (uv, gunicorn)
├── docker-compose.yml  local Postgres + optional web
└── pyproject.toml   uv + ruff + djlint config
```

## Deployment (planned)

See `infra/terraform/README.md` for AWS infrastructure.
