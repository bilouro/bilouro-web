# bilouro-web

[Wagtail](https://wagtail.org/) multi-site behind **bilouro.com**, deployed on AWS Lightsail.

Three subdomains served by a single Wagtail project (multi-site by hostname):

| Subdomain | Django app | Purpose |
|---|---|---|
| `www.bilouro.com` | `apps.autoral` | Landing + About / CV |
| `tech.bilouro.com` | `apps.tech` | Tech blog + Projects (12+) |
| `books.bilouro.com` | `apps.shop` | Book catalogue + pre-launch posts |

Apex `bilouro.com` 301-redirects to `www.bilouro.com`.

## Stack

- Python 3.13 · Django 5.2 · Wagtail 7
- PostgreSQL 16 · Gunicorn · WhiteNoise
- nginx + Certbot (Let's Encrypt) on Lightsail
- Dependency manager: [uv](https://docs.astral.sh/uv/)
- Lint/format: [ruff](https://docs.astral.sh/ruff/) (replaces black) · [djlint](https://www.djlint.com/) for templates
- Media: AWS S3 (`django-storages`)
- RSS / Atom feeds, sitemap.xml, robots.txt out of the box

## Local development

```bash
# 1. Install uv (one-time)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Install dependencies (creates .venv automatically)
uv sync

# 3. Start Postgres
docker compose up -d db

# 4. Copy env defaults
cp .env.example .env

# 5. Migrate + bootstrap (idempotent)
uv run python manage.py migrate
uv run python manage.py bootstrap_sites          # 3 sites + 2 books + 12 projects + about
uv run python manage.py createsuperuser

# 6. Run dev server
uv run python manage.py runserver
```

For local subdomain testing, add to `/etc/hosts`:

```
127.0.0.1 www.localhost tech.localhost books.localhost
```

Then open http://www.localhost:8000/, http://tech.localhost:8000/projects/, etc.

## Importing posts from external sources

The `import_posts` command handles both LinkedIn-style and frontmatter-style markdown:

```bash
uv run python manage.py import_posts /path/to/markdown/dir --parent-slug tech
uv run python manage.py import_posts /path/to/markdown/dir --parent-slug jesus-o-lider
```

Auto-detects format. Auto-finds image by basename (`file.md` → `file.png`) or by pattern fallback for numbered LinkedIn posts (`post-NN.png`).

## Production deployment (Lightsail)

Single-command deploy:

```bash
./scripts/deploy.sh   # git push + ssh && sudo bilouro-deploy
```

The remote `bilouro-deploy` script (installed at `/usr/local/bin/`) does:
pull → uv sync → migrate → collectstatic → bootstrap → restart → health check → rollback if it fails.

See `scripts/lightsail_*` for one-off provisioning, Certbot, and weekly Postgres backup to S3.

## Project layout

```
bilouro-web/
├── apps/
│   ├── core/         Custom User + bootstrap_sites + import_posts + RSS feeds
│   ├── autoral/      HomePage, AboutPage  (www)
│   ├── tech/         BlogIndexPage, BlogPostPage, ProjectIndexPage, ProjectPage  (tech)
│   ├── shop/         BookCatalogPage, BookPage, BookPostPage  (books)
│   └── newsletter/   placeholder
├── config/
│   ├── settings/     base.py · dev.py · prod.py
│   └── urls.py · wsgi.py · asgi.py
├── templates/        _base.html + per-vertical bases + page templates
├── static/css/       _base.css · autoral.css · tech.css · shop.css
├── infra/terraform/  S3 media bucket + AWS Budgets (Lightsail itself is managed via aws-cli)
├── scripts/
│   ├── deploy.sh                  laptop wrapper
│   ├── server_deploy.sh           runs on the VM (installed as bilouro-deploy)
│   ├── lightsail_provision.sh     first-time Ubuntu bootstrap
│   ├── lightsail_app_setup.sh     clone + venv + systemd + nginx
│   ├── lightsail_run_certbot.sh   issue Let's Encrypt certs
│   ├── lightsail_nginx_https.sh   swap nginx to HTTPS-aware config
│   └── lightsail_backup.sh        weekly pg_dump → S3
├── docker-compose.yml             local Postgres only
├── pyproject.toml                 uv + ruff + djlint
└── README.md
```

## License

This is a personal project. Source is available for reference; please don't redeploy verbatim under your own domain.
