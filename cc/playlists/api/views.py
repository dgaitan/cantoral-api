from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import Q
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from cc.playlists.api.permissions import (
    CanMutatePlaylistSongs,
    IsPlaylistOwner,
    PlaylistAccessPermission,
)
from cc.playlists.api.serializers import (
    AttachSongsSerializer,
    PlaylistSerializer,
    PlaylistSongItemSerializer,
    PlaylistWriteSerializer,
    ReorderSongsSerializer,
)
from cc.playlists.models import Playlist
from cc.playlists.services import (
    AttachSongsService,
    CreatePlaylistService,
    DeletePlaylistService,
    ReorderSongsService,
    UpdatePlaylistService,
)
from cc.utils.pagination import ApiPageNumberPagination
from cc.utils.responses import ApiResponse
from cc.utils.views import BaseViewSet

if TYPE_CHECKING:
    from rest_framework.request import Request


class PlaylistViewSet(BaseViewSet):
    queryset = Playlist.objects.select_related("owner")
    lookup_field = "uuid"
    pagination_class = ApiPageNumberPagination

    permission_classes_mapping = {
        "list": [AllowAny],
        "create": [IsAuthenticated],
        "retrieve": [PlaylistAccessPermission],
        "update": [IsAuthenticated, IsPlaylistOwner],
        "destroy": [IsAuthenticated, IsPlaylistOwner],
        "songs": [PlaylistAccessPermission],
        "attach": [IsAuthenticated, CanMutatePlaylistSongs],
        "reorder": [IsAuthenticated, CanMutatePlaylistSongs],
    }

    def list(self, request: Request) -> ApiResponse:
        qs = Playlist.objects.select_related("owner")
        if request.user.is_authenticated:
            qs = qs.filter(Q(is_public=True) | Q(owner=request.user))
        else:
            qs = qs.filter(is_public=True)

        name = request.query_params.get("name")
        description = request.query_params.get("description")
        if name:
            qs = qs.filter(name__icontains=name)
        if description:
            qs = qs.filter(description__icontains=description)

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = PlaylistSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        return ApiResponse(data=PlaylistSerializer(qs, many=True).data, status=status.HTTP_200_OK)

    def create(self, request: Request) -> ApiResponse:
        serializer = PlaylistWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return ApiResponse(errors=serializer.errors, success=False, status=status.HTTP_400_BAD_REQUEST)
        playlist = CreatePlaylistService(
            user=request.user,  # type: ignore[arg-type]
            **serializer.validated_data,
        ).dispatch()
        return ApiResponse(data=PlaylistSerializer(playlist).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request: Request, uuid: str | None = None) -> ApiResponse:
        playlist = self.get_object()
        return ApiResponse(data=PlaylistSerializer(playlist).data, status=status.HTTP_200_OK)

    def update(self, request: Request, uuid: str | None = None) -> ApiResponse:
        playlist = self.get_object()
        serializer = PlaylistWriteSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return ApiResponse(errors=serializer.errors, success=False, status=status.HTTP_400_BAD_REQUEST)
        playlist = UpdatePlaylistService(playlist=playlist, **serializer.validated_data).dispatch()
        return ApiResponse(data=PlaylistSerializer(playlist).data, status=status.HTTP_200_OK)

    def destroy(self, request: Request, uuid: str | None = None) -> ApiResponse:
        playlist = self.get_object()
        DeletePlaylistService(playlist).dispatch()
        from rest_framework.response import Response
        return Response(status=status.HTTP_204_NO_CONTENT)

    def songs(self, request: Request, uuid: str | None = None) -> ApiResponse:
        playlist = self.get_object()
        qs = playlist.playlist_songs.select_related("song").order_by("order")
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = PlaylistSongItemSerializer(page, many=True, context={"request": request})
            return self.get_paginated_response(serializer.data)
        return ApiResponse(
            data=PlaylistSongItemSerializer(qs, many=True, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def attach(self, request: Request, uuid: str | None = None) -> ApiResponse:
        playlist = self.get_object()
        serializer = AttachSongsSerializer(data=request.data)
        if not serializer.is_valid():
            return ApiResponse(errors=serializer.errors, success=False, status=status.HTTP_400_BAD_REQUEST)
        try:
            AttachSongsService(playlist=playlist, song_ids=serializer.validated_data["song_ids"]).dispatch()
        except ValueError as exc:
            return ApiResponse(errors=[str(exc)], success=False, status=status.HTTP_400_BAD_REQUEST)
        return ApiResponse(data={}, status=status.HTTP_200_OK)

    def reorder(self, request: Request, uuid: str | None = None) -> ApiResponse:
        playlist = self.get_object()
        serializer = ReorderSongsSerializer(data=request.data)
        if not serializer.is_valid():
            return ApiResponse(errors=serializer.errors, success=False, status=status.HTTP_400_BAD_REQUEST)
        try:
            ReorderSongsService(playlist=playlist, song_ids=serializer.validated_data["song_ids"]).dispatch()
        except ValueError as exc:
            return ApiResponse(errors=[str(exc)], success=False, status=status.HTTP_400_BAD_REQUEST)
        return ApiResponse(data={}, status=status.HTTP_200_OK)


class ProfilePlaylistsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> ApiResponse:
        qs = Playlist.objects.filter(owner=request.user).order_by("-created_at")
        paginator = ApiPageNumberPagination()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            serializer = PlaylistSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)  # type: ignore[return-value]
        return ApiResponse(data=PlaylistSerializer(qs, many=True).data, status=status.HTTP_200_OK)
