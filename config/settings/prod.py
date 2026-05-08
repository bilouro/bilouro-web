"""Production settings (App Runner + RDS + S3 + SES)."""
from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")

# ─── Security headers ──────────────────────────────────────────────
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])


# ─── Storage (S3 for media, whitenoise for static) ─────────────────
AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="eu-west-1")
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default="")
AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = None
AWS_QUERYSTRING_AUTH = True

STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": AWS_STORAGE_BUCKET_NAME,
            "region_name": AWS_S3_REGION_NAME,
            "default_acl": None,
            "querystring_auth": True,
            "file_overwrite": False,
        },
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}


# ─── Email (SES) ───────────────────────────────────────────────────
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django_ses.SESBackend")
AWS_SES_REGION_NAME = env("AWS_SES_REGION_NAME", default="eu-west-1")
AWS_SES_REGION_ENDPOINT = f"email.{AWS_SES_REGION_NAME}.amazonaws.com"
