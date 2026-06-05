from __future__ import annotations

from typing import Any

from rest_framework.response import Response
from rest_framework.serializers import Serializer


class ApiResponse(Response):
    def __init__(
        self,
        data: Any = None,
        message: str = "",
        errors: list[Any] | None = None,
        success: bool = True,  # noqa: FBT001, FBT002
        status: int | None = None,
        **kwargs: Any,
    ) -> None:
        envelope = {
            "data": data if data is not None else {},
            "message": message,
            "errors": errors or [],
            "success": success,
        }
        super().__init__(data=envelope, status=status, **kwargs)        
