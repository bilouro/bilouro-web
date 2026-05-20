# bilouro-web

A production-ready [Wagtail](https://wagtail.org/) multi-site running three independent subdomains from a single project, deployed on a $8/month AWS Lightsail VM. Built as a real personal site at [bilouro.com](https://www.bilouro.com/) — and shared as a reference implementation you can fork.

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/)
[![Django 5.2](https://img.shields.io/badge/django-5.2-092e20.svg)](https://www.djangoproject.com/)
[![Wagtail 7](https://img.shields.io/badge/wagtail-7-43b1b0.svg)](https://wagtail.org/)
[![License: BSD-3-Clause](https://img.shields.io/badge/license-BSD--3--Clause-yellow.svg)](LICENSE)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](#contributing)

## Live

| Subdomain | App | Purpose |
|---|---|---|
| [www.bilouro.com](https://www.bilouro.com/) | `apps.autoral` | Landing + About / CV |
| [tech.bilouro.com](https://tech.bilouro.com/) | `apps.tech` | Engineering blog + projects |
| [books.bilouro.com](https://books.bilouro.com/) | `apps.shop` | Book catalogue + pre-launch posts |

Apex `bilouro.com` 301-redirects to `www`.

## Why this exists

If you are about to build a personal site (or three) and find yourself reaching for Next.js + Vercel + Sanity / Contentful / Strapi for a project that gets a few thousand views a month, this repo is the boring alternative:

- **One Postgres, one admin, one VM, three sites.** Multi-site routing by hostname is built into Wagtail; the trade-off is "you write Python templates" instead of "you write React components".
- **$8 / month all-in** (Lightsail nano + S3 media + Let's Encrypt). No vendor lock-in.
- **i18n done two ways**, on purpose:
  - UI strings via `gettext` + django-rosetta.
  - Per-field translations (`field` + `field_pt`) chosen by a tiny template tag and a language cookie — no `wagtail-localize` page tree duplication.
- **Search without Elasticsearch** — Wagtail's `SearchField` + Postgres backend, host-scoped at `/search/?q=...`.
- **Atom/RSS feeds** and **multi-site sitemaps** out of the box.
- **Deploy is one command** from the laptop: `git push` + `ssh && sudo bilouro-deploy` → pull, migrate, collectstatic, restart, health-check, auto-rollback on non-200.

If you want the full story, the [`tech.bilouro.com`](https://tech.bilouro.com/) blog has a post called *Three Sites One Admin One Postgres* that walks through it.

## Stack

| Layer | Choice |
|---|---|
| Language | Python 3.13 |
| Framework | Django 5.2 · Wagtail 7 |
| Database | PostgreSQL 16 |
| App server | Gunicorn (3 workers) + WhiteNoise |
| Reverse proxy | nginx + Let's Encrypt (Certbot) |
| Media | AWS S3 + signed URLs (`django-storages`) |
| Dependency manager | [uv](https://docs.astral.sh/uv/) |
| Lint / format | [ruff](https://docs.astral.sh/ruff/) + [djlint](https://www.djlint.com/) |
| Host | AWS Lightsail (Ubuntu, $8 / month nano) |

## Quick start

```bash
# 1. Install uv (one-time)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Clone & install
git clone https://github.com/bilouro/bilouro-web.git
cd bilouro-web
uv sync

# 3. Local Postgres
docker compose up -d db

# 4. Env defaults
cp .env.example .env

# 5. Migrate + idempotent bootstrap (3 sites, demo content)
uv run python manage.py migrate
uv run python manage.py bootstrap_sites
uv run python manage.py createsuperuser

# 6. Run
uv run python manage.py runserver
```

For local subdomain testing, add to `/etc/hosts`:

```
127.0.0.1 www.localhost tech.localhost books.localhost
```

Then open <http://www.localhost:8000/>, <http://tech.localhost:8000/projects/>, etc.

## Forking this for your own site

This repo is a working sample, not a generator. To make it yours:

1. **Rename the package.** `bilouro` appears in `pyproject.toml`, `config/settings/*`, deploy scripts, and the `bilouro:bilouro` system user on the VM. A grep + replace gets most of it.
2. **Rewrite `bootstrap_sites`.** [`apps/core/management/commands/bootstrap_sites.py`](apps/core/management/commands/bootstrap_sites.py) is idempotent: it creates / updates the Wagtail Sites, root pages, and demo content. Change the hostnames, page titles, and seed projects there.
3. **Replace `apps/autoral`, `apps/tech`, `apps/shop`** with the verticals you actually want. The conventions (template per app, per-field PT, `{% tr %}` tag) work for any number of subdomains.
4. **Rewrite or remove the book pipeline.** [`apps/shop`](apps/shop/) is a niche use case (book reflections in two languages). If you don't need it, delete the app and prune its references from `INSTALLED_APPS`, URLs, and `bootstrap_sites`.
5. **Point `scripts/deploy.sh`** at your VM (env vars `VM_HOST`, `VM_USER`, `SSH_KEY`). The remote `server_deploy.sh` installs as `bilouro-deploy`; rename to taste.

The license (BSD-3-Clause) lets you do this commercially. The only requirement is to keep the copyright notice in source-distributed copies — see `LICENSE`.

## Importing posts from external markdown

```bash
uv run python manage.py import_posts /path/to/dir --parent-slug tech
uv run python manage.py import_posts /path/to/dir --parent-slug jesus-o-lider
```

Auto-detects two markdown formats (LinkedIn-style with `## Texto (copy-paste)` block, or YAML-frontmatter). Auto-finds the cover image by basename or by the `image:` frontmatter field.

## Production deployment

```bash
./scripts/deploy.sh   # git push + ssh && sudo bilouro-deploy
```

The remote `bilouro-deploy` script (installed at `/usr/local/bin/`) does:

> pull → `uv sync` → migrate → collectstatic → compilemessages → bootstrap → restart → HTTP health-check → auto-rollback to previous SHA if non-200.

See `scripts/lightsail_*` for one-off provisioning (Ubuntu bootstrap, Certbot, S3 backup).

### Hardening

The Lightsail nano is small (911 MB RAM, no swap by default). The prod box runs three cheap safeguards, all applied via the `scripts/lightsail_*` snippets so they survive a redeploy:

1. **2 GB swap file** (`/swapfile`, `vm.swappiness=10`). Absorbs RAM spikes from bulk page imports and Wagtail image rendition generation.
2. **nginx `444` for secret-probe paths** — `location ~* …` blocks at the top of [`bilouro-app.conf`](scripts/lightsail_nginx_https.sh) close the connection instantly for `/.env*`, `/.git/`, `/.aws/`, `/serviceAccountKey.json`, `/settings.py`, `/phpinfo.php`, `*.bak`, `*.sql`, etc. ~500–1000 hits/day stop here, never reach Django.
3. **fail2ban** — two jails: `sshd` (4 failed logins in 10 min → 1 h ban) and `nginx-scanners` (15 × 4xx in 2 min → 6 h ban). Installer: [`scripts/lightsail_fail2ban.sh`](scripts/lightsail_fail2ban.sh).

4. **HTTPS catch-all** — `listen 443 ssl http2 default_server` block returns `444` for any SNI/Host that doesn't match a known vhost. Closes a leak where unknown hosts (e.g. `random.example.com → 3.251.103.83`) used to fall through to the first matching server block (typically `bilouro.com` apex 301) and surface bilouro content under arbitrary names. Templated in [`scripts/lightsail_nginx_https.sh`](scripts/lightsail_nginx_https.sh).

### Analytics (server-side, log-based)

No JS tracking, no third-party SaaS. [GoAccess](https://goaccess.io/) parses the existing nginx `access.log` and renders static HTML dashboards **gated by the Wagtail admin login**. Three reports are generated, each linked in the Wagtail admin sidebar:

- `https://<your-site>/admin/stats/` — all hosts combined
- `https://<your-site>/admin/stats/bilouro/` — `*.bilouro.com` only
- `https://<your-site>/admin/stats/hashtag-jesus/` — `*.hashtag-jesus.com` only

This requires nginx to log the `$host` (custom `vhost_combined` log format). The wrapper at `/usr/local/bin/goaccess-rebuild` greps the shared access log by host prefix before running goaccess for each report.

How it works: a Django view (`apps.core.views.stats_dashboard`, decorated with `@require_admin_access`) authorizes the request, then issues `X-Accel-Redirect` so nginx serves the static HTML at native speed from an `internal` location. No double-password, no extra middleware cost.

```bash
ssh -i <key> ubuntu@<vm> 'sudo bash -s' < scripts/lightsail_goaccess.sh
```

The installer ([`scripts/lightsail_goaccess.sh`](scripts/lightsail_goaccess.sh)):

- Installs GoAccess.
- Hourly cron regenerates `/var/www/stats/index.html` (uses `--persist --restore` so data accumulates across log rotations).
- Bumps `logrotate` retention for nginx access logs from 14 to 60 days.
- Wires nginx `location /_internal/stats/` with the `internal;` directive — only the Django view can dispatch it.

Wagtail-side wiring lives in [`apps/core/views.py`](apps/core/views.py) (the view) and [`apps/core/wagtail_hooks.py`](apps/core/wagtail_hooks.py) (admin URL + sidebar menu item).

Manual rebuild any time: `sudo /usr/local/bin/goaccess-rebuild`.

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
├── infra/terraform/  S3 media bucket + AWS Budgets
├── scripts/
│   ├── deploy.sh                  laptop wrapper
│   ├── server_deploy.sh           runs on the VM (installed as bilouro-deploy)
│   ├── lightsail_provision.sh     first-time Ubuntu bootstrap
│   ├── lightsail_app_setup.sh     clone + venv + systemd + nginx
│   ├── lightsail_run_certbot.sh   issue Let's Encrypt certs
│   ├── lightsail_nginx_https.sh   HTTPS-aware nginx (+ 444 probe drops)
│   ├── lightsail_fail2ban.sh      install fail2ban (sshd + nginx-scanners)
│   ├── lightsail_goaccess.sh      install GoAccess dashboard (/admin/stats/)
│   └── lightsail_backup.sh        weekly pg_dump → S3
├── docker-compose.yml             local Postgres only
├── pyproject.toml                 uv + ruff + djlint
├── LICENSE                        BSD-3-Clause
└── README.md
```

## Contributing

Contributions are welcome. Some areas that can use love:

- More multi-site examples (e.g. a fourth vertical).
- A `cookiecutter`-style fork that asks for subdomain names and generates the bootstrap.
- Replacing the hand-rolled `field` + `field_pt` pattern with a documented integration with `wagtail-localize` for users who prefer page-tree duplication.
- Better tests (current coverage is honestly thin).
- Documentation translations.

How to contribute:

1. [Open an issue](https://github.com/bilouro/bilouro-web/issues/new) first for anything non-trivial — keeps us aligned before code is written.
2. Fork the repo and create a feature branch (`git checkout -b feat/short-name`).
3. Run `uv run ruff format . && uv run ruff check . && uv run djlint templates/` before committing.
4. Open a PR with a short description and link to the issue.

By contributing you agree your changes are licensed under BSD-3-Clause (same as the repo).

For larger discussions, security issues, or just to say hi: `hello@bilouro.com`.

## Acknowledgments

Stand on the shoulders of:

- [Wagtail](https://wagtail.org/) — multi-site by hostname is the killer feature this whole repo is built on.
- [Django](https://www.djangoproject.com/) — five years of stability.
- [uv](https://docs.astral.sh/uv/) — replaced pip, virtualenv, and pip-tools in 10 minutes.
- [ruff](https://docs.astral.sh/ruff/) — replaced black + isort + flake8.
- [Let's Encrypt](https://letsencrypt.org/) and [Certbot](https://certbot.eff.org/) — the entire HTTPS layer.
- AWS Lightsail — the most boring, cheapest way to run a real VM in 2026.

## License

[BSD-3-Clause](LICENSE). You are free to fork, redeploy under your own domain, and use this commercially. The only requirement is to keep the copyright notice in source-distributed copies.

© 2026 Victor H. Bilouro · `hello@bilouro.com`
