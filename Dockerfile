# ─── builder ────────────────────────────────────────────────────────
FROM python:3.13-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never

# uv is the package manager
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /uvx /usr/local/bin/

WORKDIR /app

# Install deps first (cached layer)
COPY pyproject.toml uv.lock* ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev || \
    uv sync --no-install-project --no-dev

# Copy source and install project
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev

# ─── runtime ────────────────────────────────────────────────────────
FROM python:3.13-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=config.settings.prod \
    PATH="/app/.venv/bin:$PATH" \
    PORT=8000

WORKDIR /app

# Copy venv + source from builder
COPY --from=builder /app /app

# Non-root user
RUN useradd --system --uid 1000 --create-home app \
    && chown -R app:app /app

USER app

EXPOSE 8000

# Healthcheck (App Runner expects /healthz/)
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/healthz/').read()" || exit 1

# Migrate + collectstatic + bootstrap (all idempotent), then gunicorn
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py collectstatic --noinput && python manage.py bootstrap_sites --prod && gunicorn config.wsgi:application --bind 0.0.0.0:${PORT} --workers 3 --access-logfile - --error-logfile -"]
