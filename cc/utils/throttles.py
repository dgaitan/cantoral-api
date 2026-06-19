from __future__ import annotations

from typing import TYPE_CHECKING

from rest_framework.settings import api_settings
from rest_framework.throttling import UserRateThrottle

if TYPE_CHECKING:
    from rest_framework.request import Request
    from rest_framework.views import APIView


class AuthRateThrottle(UserRateThrottle):
    """Throttle for auth endpoints — uses the 'auth' scope in DEFAULT_THROTTLE_RATES."""

    scope = "auth"


class FavoriteToggleThrottle(UserRateThrottle):
    """Throttle for the favorite toggle endpoint, keyed per user + song."""

    scope = "favorite_toggle"

    def get_rate(self) -> str | None:
        # Read at call time so override_settings works in tests.
        return api_settings.DEFAULT_THROTTLE_RATES.get(self.scope)

    def get_cache_key(self, request: Request, view: APIView) -> str | None:
        if not request.user or not request.user.is_authenticated:
            return None
        song_pk = view.kwargs.get("pk", "")  # type: ignore[union-attr]
        ident = f"{request.user.pk}_{song_pk}"
        return self.cache_format % {"scope": self.scope, "ident": ident}
