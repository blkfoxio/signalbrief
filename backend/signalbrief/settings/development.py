"""
Development settings for SignalBrief.
Uses SQLite for local development.
"""

from .base import *  # noqa: F401, F403

DEBUG = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Allow dev auth endpoints
DEV_AUTH_ENABLED = True

# Relaxed throttling for development
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {
    "user": "1000/minute",
    "anon": "100/minute",
}
