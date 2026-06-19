from __future__ import annotations

from typing import TYPE_CHECKING

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from cc.songs.api.serializers import SongSerializer
from cc.songs.queries import SongQuerySet
from cc.users.api.serializers import ProfileSerializer
from cc.utils.pagination import ApiPageNumberPagination
from cc.utils.responses import ApiResponse

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from rest_framework.request import Request
    from rest_framework.response import Response

    from cc.songs.models import Song


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> ApiResponse:
        serializer = ProfileSerializer(request.user)
        return ApiResponse(data=serializer.data, status=status.HTTP_200_OK)

    def put(self, request: Request) -> ApiResponse:
        serializer = ProfileSerializer(request.user, data=request.data, partial=True)
        if not serializer.is_valid():
            return ApiResponse(
                errors=serializer.errors,
                success=False,
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer.save()
        return ApiResponse(data=serializer.data, status=status.HTTP_200_OK)


class FavoriteSongsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> ApiResponse | Response:
        try:
            qs: QuerySet[Song] = (
                SongQuerySet().with_filters(**request.query_params).get_queryset()
            )
        except ValueError as exc:
            return ApiResponse(
                errors=[str(exc)],
                success=False,
                status=status.HTTP_400_BAD_REQUEST,
            )
        qs = qs.filter(favorites__user=request.user).order_by("-favorites__created_at")
        paginator = ApiPageNumberPagination()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            serializer = SongSerializer(page, many=True, context={"request": request})
            return paginator.get_paginated_response(serializer.data)  # type: ignore[arg-type]
        serializer = SongSerializer(qs, many=True, context={"request": request})
        return ApiResponse(data=serializer.data, status=status.HTTP_200_OK)
