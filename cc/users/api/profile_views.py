from __future__ import annotations

from typing import TYPE_CHECKING

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from cc.songs.api.serializers import SongSerializer
from cc.songs.models import Song
from cc.users.api.serializers import ProfileSerializer
from cc.utils.pagination import ApiPageNumberPagination
from cc.utils.responses import ApiResponse

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from rest_framework.request import Request
    from rest_framework.response import Response


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
        qs = (
            Song.objects.filter(favorites__user=request.user)  # type: ignore[misc]
            .prefetch_related("tags", "authors", "verses")
            .order_by("-favorites__created_at")
        )
        qs = self._apply_filters(request, qs)
        paginator = ApiPageNumberPagination()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            serializer = SongSerializer(page, many=True, context={"request": request})
            return paginator.get_paginated_response(serializer.data)  # type: ignore[arg-type]
        serializer = SongSerializer(qs, many=True, context={"request": request})
        return ApiResponse(data=serializer.data, status=status.HTTP_200_OK)

    def _apply_filters(self, request: Request, qs: QuerySet) -> QuerySet:
        params = request.query_params
        needs_distinct = False
        if name := params.get("name", "").strip():
            qs = qs.filter(name__icontains=name)
        if author := params.get("author", "").strip():
            qs = qs.filter(authors__name__icontains=author)
            needs_distinct = True
        if tag := params.get("tag", "").strip():
            qs = qs.filter(tags__name__icontains=tag)
            needs_distinct = True
        if needs_distinct:
            qs = qs.distinct()
        return qs
