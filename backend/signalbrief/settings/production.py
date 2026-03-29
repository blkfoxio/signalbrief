"""
Production settings for SignalBrief.
Uses PostgreSQL via DATABASE_URL from Railway.
"""

import dj_database_url

from .base import *  # noqa: F401, F403

DEBUG = False

DATABASES = {
    "default": dj_database_url.config(
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# Security
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True

# No dev auth in production
DEV_AUTH_ENABLED = False

# Report generation throttle
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {
    "user": "100/minute",
    "anon": "20/minute",
    "report_generation": "10/hour",
}
