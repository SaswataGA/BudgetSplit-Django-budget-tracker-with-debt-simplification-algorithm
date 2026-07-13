"""
Development settings — used on your local machine.

Run with: DJANGO_SETTINGS_MODULE=budgetsplit.settings.development
(this is already set as the default in manage.py, so you normally
don't need to set it yourself for local work).
"""

from .base import *  # noqa: F401, F403
from decouple import config

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Show Django's debug error pages locally; production.py overrides
# this with real custom 404/500 templates instead.

# Email backend: print emails to the console instead of actually
# sending them, so password-reset flows are testable locally with zero
# email server setup.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
