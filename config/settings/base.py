"""Base settings shared by dev and prod."""
import os
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent
env = environ.Env()

# Read .env if present (no-op if missing)
env_file = BASE_DIR / ".env"
if env_file.exists():
    env.read_env(str(env_file))


# ─── Core ───────────────────────────────────────────────────────────
SECRET_KEY = env("SECRET_KEY", default="insecure-dev-only-change-in-prod")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ─── Apps ───────────────────────────────────────────────────────────
LOCAL_APPS = [
    "apps.core",
    "apps.autoral",
    "apps.tech",
    "apps.newsletter",
    "apps.shop",
]

WAGTAIL_APPS = [
    "wagtail.contrib.forms",
    "wagtail.contrib.redirects",
    "wagtail.embeds",
    "wagtail.sites",
    "wagtail.users",
    "wagtail.snippets",
    "wagtail.documents",
    "wagtail.images",
    "wagtail.search",
    "wagtail.admin",
    "wagtail",
    "wagtail_localize",
    "wagtail_localize.locales",
    "wagtailmetadata",
    "wagtailcache",
    "modelcluster",
    "taggit",
]

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
]

INSTALLED_APPS = LOCAL_APPS + WAGTAIL_APPS + DJANGO_APPS


# ─── Middleware ─────────────────────────────────────────────────────
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "wagtailcache.cache.UpdateCacheMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "wagtail.contrib.redirects.middleware.RedirectMiddleware",
    "wagtailcache.cache.FetchFromCacheMiddleware",
]

# wagtail-cache settings
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "wagtailcache",
        "TIMEOUT": 60 * 60,  # 1h default
    }
}
WAGTAIL_CACHE_BACKEND = "default"
WAGTAIL_CACHE_HEADER = "X-Wagtail-Cache"
WAGTAIL_CACHE_IGNORE_QS = ["utm_*", "fbclid", "gclid", "ref"]


# ─── Templates ──────────────────────────────────────────────────────
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.site_globals",
            ],
        },
    },
]


# ─── Database ───────────────────────────────────────────────────────
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://bilouro:bilouro@localhost:5432/bilouro",
    ),
}


# ─── Auth ───────────────────────────────────────────────────────────
AUTH_USER_MODEL = "core.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# ─── i18n / l10n ────────────────────────────────────────────────────
LANGUAGE_CODE = "en"
TIME_ZONE = "Europe/Lisbon"
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ("en", "English"),
    ("pt", "Português"),
]

LOCALE_PATHS = [BASE_DIR / "locale"]

# Wagtail i18n
WAGTAIL_I18N_ENABLED = True
WAGTAIL_CONTENT_LANGUAGES = LANGUAGES

# wagtail-localize machine translator (using our OpenAI prompt below)
WAGTAILLOCALIZE_MACHINE_TRANSLATORS = []  # we run translations via custom command, not the admin button


# ─── Static & media ─────────────────────────────────────────────────
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"


# ─── Wagtail ────────────────────────────────────────────────────────
WAGTAIL_SITE_NAME = "bilouro.com"
WAGTAILADMIN_BASE_URL = env("WAGTAILADMIN_BASE_URL", default="http://localhost:8000")

WAGTAILSEARCH_BACKENDS = {
    "default": {
        "BACKEND": "wagtail.search.backends.database",
    }
}


# ─── Comments / Analytics (optional, set via env) ─────────────────
# Giscus (GitHub Discussions). Get IDs from giscus.app after enabling
# Discussions on bilouro/bilouro-comments.
GISCUS_REPO_ID = env("GISCUS_REPO_ID", default="")
GISCUS_CATEGORY_ID = env("GISCUS_CATEGORY_ID", default="")

# Plausible Analytics — set PLAUSIBLE_DOMAIN to enable.
PLAUSIBLE_DOMAIN = env("PLAUSIBLE_DOMAIN", default="")
PLAUSIBLE_SCRIPT = env("PLAUSIBLE_SCRIPT", default="https://plausible.io/js/script.js")


# ─── Email ──────────────────────────────────────────────────────────
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="hello@bilouro.com")
SERVER_EMAIL = DEFAULT_FROM_EMAIL


# ─── Logging ────────────────────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": env("DJANGO_LOG_LEVEL", default="INFO"),
            "propagate": False,
        },
    },
}
