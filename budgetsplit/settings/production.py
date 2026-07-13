"""
Production settings — used when deployed (Render, Railway,
PythonAnywhere, Fly.io, etc.). See the README's Deployment section for
how to set the required environment variables on each platform.
"""

import dj_database_url
from .base import *  # noqa: F401, F403
from decouple import config, Csv

DEBUG = False

ALLOWED_HOSTS = config("ALLOWED_HOSTS", cast=Csv())

# Hashed, cache-busted filenames (e.g. custom.a1b2c3.css) + gzip/brotli
# compression. Requires `python manage.py collectstatic` to have been
# run during deployment to generate the manifest -- every platform in
# this project's README deployment guide does this automatically as
# part of its build step.
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# DATABASE_URL is provided automatically by Render/Railway/Fly.io when
# you attach a PostgreSQL addon. Locally in development we use SQLite
# instead (see development.py) — see the README's "SQLite -> PostgreSQL
# migration" section for how to move existing data across.
DATABASES = {
    "default": dj_database_url.config(
        default=config("DATABASE_URL"),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# ----- Security hardening (all OFF in development, ON here) -----
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=31536000, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# Trust the platform's reverse proxy for HTTPS detection (Render,
# Railway, Fly.io, and PythonAnywhere all terminate TLS in front of
# your app and forward requests over plain HTTP internally).
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# A real email backend would go here in a fully deployed app, e.g.:
# EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
# EMAIL_HOST = config("EMAIL_HOST")
# EMAIL_HOST_USER = config("EMAIL_HOST_USER")
# EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD")
# Left as the console backend here to keep this project deployable
# without requiring you to set up a real mail provider first.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
