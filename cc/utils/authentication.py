from __future__ import annotations

from typing import TYPE_CHECKING

from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import AuthUser, JWTAuthentication

if TYPE_CHECKING:
    from rest_framework.request import Request
    from rest_framework_simplejwt.tokens import Token


class ApiJWTAuthentication(JWTAuthentication):
    """JWTAuthentication that treats an invalid/expired token as no credentials.

    DRF authenticates a request before checking permissions, so a stale
    Bearer token 401s even on an AllowAny view — AllowAny only skips the
    permission check, it doesn't make authentication itself lenient. Falling
    back to anonymous here makes AllowAny behave as documented; endpoints
    that require authentication still reject the resulting anonymous user.
    """

    def authenticate(self, request: Request) -> tuple[AuthUser, Token] | None:
        try:
            return super().authenticate(request)
        except AuthenticationFailed:
            return None
