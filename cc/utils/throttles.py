from __future__ import annotations

from rest_framework.throttling import UserRateThrottle


class AuthRateThrottle(UserRateThrottle):
    """Throttle for auth endpoints — uses the 'auth' scope in DEFAULT_THROTTLE_RATES."""

    scope = "auth"
