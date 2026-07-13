"""
Base Django settings for the budgetsplit project — shared by both
development.py and production.py. Never import this file directly;
DJANGO_SETTINGS_MODULE should always point to either
budgetsplit.settings.development or budgetsplit.settings.production.
"""

from pathlib import Path
from decouple import config

# BASE_DIR is the project root — three .parent calls because this file
# lives at budgetsplit/budgetsplit/settings/base.py:
#   settings/ -> budgetsplit/ (inner package) -> budgetsplit/ (project root)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
# Loaded from the environment (.env file locally, real env vars in
# production) rather than hardcoded — see .env.example.
SECRET_KEY = config("SECRET_KEY")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",  # nice number/currency formatting in templates

    # Local apps
    "accounts",
    "budgets",
    "groups",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # serves static files efficiently, even in prod without Nginx
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "budgetsplit.urls"

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
            ],
        },
    },
]

WSGI_APPLICATION = "budgetsplit.wsgi.application"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static & media files
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"  # collectstatic target for production

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        # Plain (non-manifest) WhiteNoise storage here in base.py: this
        # serves static files directly without needing collectstatic to
        # have been run first, which matters for local development where
        # you're constantly editing CSS/JS. production.py overrides this
        # with the hashed/manifest version, which DOES require
        # collectstatic -- appropriate there since deployment platforms
        # always run collectstatic as part of the build step anyway.
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Auth flow redirects
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "accounts:dashboard"
LOGOUT_REDIRECT_URL = "accounts:login"

# Max upload size for profile avatars (2 MB) — validated again in forms.py,
# but capping it here too means Django rejects oversized uploads before
# they're even fully read into memory.
DATA_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024
