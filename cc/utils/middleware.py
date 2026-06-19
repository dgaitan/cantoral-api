from __future__ import annotations

from typing import TYPE_CHECKING

from django.http import JsonResponse

if TYPE_CHECKING:
    from collections.abc import Callable

    from django.http import HttpRequest, HttpResponse

_REQUIRE_JSON_CONTENT_TYPE = frozenset({"POST", "PUT", "PATCH"})


class JSONContentTypeMiddleware:
    """Reject non-JSON bodies on mutating API requests with HTTP 415."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        content_length = int(request.META.get("CONTENT_LENGTH") or 0)
        if (
            request.path.startswith("/api/")
            and request.method in _REQUIRE_JSON_CONTENT_TYPE
            and content_length > 0
            and not (request.content_type or "").startswith("application/json")
        ):
            return JsonResponse(
                {
                    "data": {},
                    "message": "",
                    "errors": ["Content-Type must be application/json."],
                    "success": False,
                },
                status=415,
            )
        return self.get_response(request)
