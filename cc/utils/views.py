from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from cc.songs.api.permissions import CanCreateSongs
from cc.utils.pagination import ApiPageNumberPagination
from cc.utils.responses import ApiResponse

if TYPE_CHECKING:
    from rest_framework.request import Request
    from rest_framework.throttling import BaseThrottle


class BaseViewSet(GenericViewSet):
    permission_classes_mapping: ClassVar[dict[str, list[type[BasePermission]]]] = {}
    throttle_classes_mapping: ClassVar[dict[str, list[type[BaseThrottle]]]] = {}

    def get_permissions(self):
        if classes := self.permission_classes_mapping.get(self.action):
            return [cls() for cls in classes]
        return super().get_permissions()

    def get_throttles(self):
        if classes := self.throttle_classes_mapping.get(self.action):
            return [cls() for cls in classes]
        return super().get_throttles()

class PublicReadCrudViewSet(GenericViewSet):
    """Base viewset: read actions are public; writes require CanCreateSongs.

    Subclasses set read_serializer_class, write_serializer_class, and
    optionally extend read_actions with any extra public @action names.
    """

    read_actions: ClassVar[tuple[str, ...]] = ("list", "retrieve")
    read_serializer_class: ClassVar[type[serializers.BaseSerializer]]
    write_serializer_class: ClassVar[type[serializers.BaseSerializer]]
    pagination_class = ApiPageNumberPagination

    def get_permissions(self):  # type: ignore[override]
        if self.action in self.read_actions:
            return [AllowAny()]
        return [CanCreateSongs()]

    def list(self, request: Request) -> ApiResponse | Response:
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.read_serializer_class(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.read_serializer_class(queryset, many=True)
        return ApiResponse(data=serializer.data, status=status.HTTP_200_OK)

    def retrieve(self, request: Request, pk: str | None = None) -> ApiResponse:
        serializer = self.read_serializer_class(self.get_object())
        return ApiResponse(data=serializer.data, status=status.HTTP_200_OK)

    def create(self, request: Request) -> ApiResponse:
        serializer = self.write_serializer_class(data=request.data)
        if not serializer.is_valid():
            return ApiResponse(
                errors=serializer.errors,
                success=False,
                status=status.HTTP_400_BAD_REQUEST,
            )
        obj = serializer.save()
        return ApiResponse(
            data=self.read_serializer_class(obj).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request: Request, pk: str | None = None) -> ApiResponse:
        obj = self.get_object()
        serializer = self.write_serializer_class(obj, data=request.data)
        if not serializer.is_valid():
            return ApiResponse(
                errors=serializer.errors,
                success=False,
                status=status.HTTP_400_BAD_REQUEST,
            )
        obj = serializer.save()
        return ApiResponse(
            data=self.read_serializer_class(obj).data, status=status.HTTP_200_OK,
        )

    def partial_update(self, request: Request, pk: str | None = None) -> ApiResponse:
        obj = self.get_object()
        serializer = self.write_serializer_class(obj, data=request.data, partial=True)
        if not serializer.is_valid():
            return ApiResponse(
                errors=serializer.errors,
                success=False,
                status=status.HTTP_400_BAD_REQUEST,
            )
        obj = serializer.save()
        return ApiResponse(
            data=self.read_serializer_class(obj).data, status=status.HTTP_200_OK,
        )

    def destroy(self, request: Request, pk: str | None = None) -> Response:
        self.get_object().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
