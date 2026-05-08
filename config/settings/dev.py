"""Local development settings."""
from .base import *  # noqa: F401,F403
from .base import INSTALLED_APPS, MIDDLEWARE, env

DEBUG = True
ALLOWED_HOSTS = ["*"]

# Reset to console email even if base read it from env
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Debug toolbar (only if installed)
try:
    import debug_toolbar  # noqa: F401

    INSTALLED_APPS = [*INSTALLED_APPS, "debug_toolbar"]
    MIDDLEWARE = [
        "debug_toolbar.middleware.DebugToolbarMiddleware",
        *MIDDLEWARE,
    ]
    INTERNAL_IPS = ["127.0.0.1"]
    DEBUG_TOOLBAR_CONFIG = {
        "SHOW_TOOLBAR_CALLBACK": lambda request: DEBUG,
    }
except ImportError:
    pass

# Wagtail admin should be reachable on local
WAGTAILADMIN_BASE_URL = env("WAGTAILADMIN_BASE_URL", default="http://localhost:8000")
