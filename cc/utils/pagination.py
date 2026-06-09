from __future__ import annotations

from typing import Any

from rest_framework import status
from rest_framework.pagination import PageNumberPagination

from cc.utils.responses import ApiResponse


class ApiPageNumberPagination(PageNumberPagination):
    page_size = 20

    def get_paginated_response(self, data: list[Any]) -> ApiResponse:
        assert self.page is not None
        return ApiResponse(
            data={
                "count": self.page.paginator.count,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "results": data,
            },
            status=status.HTTP_200_OK,
        )
