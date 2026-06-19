"""
With these settings, tests run faster.
"""

from .base import *  # noqa: F403
from .base import TEMPLATES, env

# GENERAL
# ------------------------------------------------------------------------------
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="EDZNL4Uoz1eShkkehnDGov2aw3vMRYMcunlPyVjhY3TYTXsOmLc3nNVQEYPKRBHZ",
)
TEST_RUNNER = "django.test.runner.DiscoverRunner"

# PASSWORDS
# ------------------------------------------------------------------------------
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# EMAIL
# ------------------------------------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# DEBUGGING FOR TEMPLATES
# ------------------------------------------------------------------------------
TEMPLATES[0]["OPTIONS"]["debug"] = True  # type: ignore[index]

# CELERY
# ------------------------------------------------------------------------------
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# DRF — default to JSON in test client so APIClient.post(url, data) sends JSON
# ------------------------------------------------------------------------------
REST_FRAMEWORK = {  # type: ignore[name-defined]
    **REST_FRAMEWORK,  # type: ignore[name-defined]  # noqa: F405
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "10000/minute",
        "user": "10000/minute",
        "auth": "10000/minute",  # use @override_settings to test actual limits
        "favorite_toggle": "10000/minute",  # use @override_settings to test actual limits
    },
}
# CACHES
# ------------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    },
}

# Your stuff...
# ------------------------------------------------------------------------------
