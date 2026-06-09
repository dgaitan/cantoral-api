from __future__ import annotations

from typing import TYPE_CHECKING

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from cc.songs.api.permissions import CanCreateSongs
from cc.songs.api.permissions import CanPublishSongs
from cc.songs.api.serializers import AuthorSerializer
from cc.songs.api.serializers import AuthorWriteSerializer
from cc.songs.api.serializers import CreateSongSerializer
from cc.songs.api.serializers import SongSerializer
from cc.songs.api.serializers import TagSerializer
from cc.songs.api.serializers import TagWriteSerializer
from cc.songs.api.serializers import TransportSerializer
from cc.songs.filters import AuthorFTSFilter
from cc.songs.filters import SongFTSFilter
from cc.songs.filters import TagFTSFilter
from cc.songs.lyrics.transport import ChordTransposer
from cc.songs.models import Author
from cc.songs.models import Song
from cc.songs.models import Tag
from cc.songs.services import CreateSongService
from cc.songs.services import PublishSongService
from cc.utils.pagination import ApiPageNumberPagination
from cc.utils.responses import ApiResponse
from cc.utils.views import PublicReadCrudViewSet

if TYPE_CHECKING:
    from rest_framework.request import Request
    from rest_framework.response import Response


class SongViewSet(GenericViewSet):
    queryset = Song.objects.prefetch_related("tags", "authors").order_by("-created_at")
    permission_classes = [IsAuthenticated]
    pagination_class = ApiPageNumberPagination
    filter_backends = [SongFTSFilter]

    def get_permissions(self):  # type: ignore[override]
        if self.action in ("retrieve", "list"):
            return [AllowAny()]
        if self.action == "create":
            return [CanCreateSongs()]
        if self.action == "publish":
            return [CanPublishSongs()]
        if self.action == "transport":
            return [AllowAny()]
        return super().get_permissions()

    def list(self, request: Request) -> ApiResponse | Response:
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = SongSerializer(page, many=True, context={"request": request})
            return self.get_paginated_response(serializer.data)
        serializer = SongSerializer(queryset, many=True, context={"request": request})
        return ApiResponse(data=serializer.data, status=status.HTTP_200_OK)

    def retrieve(self, request: Request, pk: str | None = None) -> ApiResponse:
        song = self.get_object()
        serializer = SongSerializer(song, context={"request": request})
        return ApiResponse(data=serializer.data, status=status.HTTP_200_OK)

    def create(self, request: Request) -> ApiResponse:
        serializer = CreateSongSerializer(data=request.data)
        if not serializer.is_valid():
            return ApiResponse(
                errors=serializer.errors,
                success=False,
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            song = CreateSongService(
                user=request.user,
                name=serializer.validated_data["name"],
                authors_ids=serializer.validated_data["authors"],
                tags_ids=serializer.validated_data["tags"],
                lyrics=serializer.validated_data["lyrics"],
            ).dispatch()
        except ValueError as exc:
            return ApiResponse(
                errors=[str(exc)],
                success=False,
                status=status.HTTP_400_BAD_REQUEST,
            )
        return ApiResponse(
            data=SongSerializer(song, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def publish(self, request: Request, pk: str | None = None) -> ApiResponse:
        song = self.get_object()
        song = PublishSongService(song).dispatch()
        return ApiResponse(
            data=SongSerializer(song, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def transport(self, request: Request, pk: str | None = None) -> ApiResponse:
        song = self.get_object()
        serializer = TransportSerializer(data=request.data)
        if not serializer.is_valid():
            return ApiResponse(
                errors=serializer.errors,
                success=False,
                status=status.HTTP_400_BAD_REQUEST,
            )
        transposed_lyrics = ChordTransposer(
            plain_lyrics=song.plain_lyrics,
            original_tone=serializer.validated_data["original_tone"],
            current_tone=serializer.validated_data["current_tone"],
            transport=serializer.validated_data["transport"],
        ).transpose()
        song_data = SongSerializer(
            song,
            context={"request": request, "override_plain_lyrics": transposed_lyrics},
        ).data
        return ApiResponse(data=song_data, status=status.HTTP_200_OK)


class AuthorViewSet(PublicReadCrudViewSet):
    queryset = Author.objects.order_by("id")
    read_serializer_class = AuthorSerializer
    write_serializer_class = AuthorWriteSerializer
    read_actions = ("list", "retrieve", "songs")
    filter_backends = [AuthorFTSFilter]

    @action(detail=True, methods=["get"])
    def songs(self, request: Request, pk: str | None = None) -> ApiResponse | Response:
        author = self.get_object()
        qs = author.songs.prefetch_related("tags", "authors").order_by("-created_at")
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = SongSerializer(page, many=True, context={"request": request})
            return self.get_paginated_response(serializer.data)
        serializer = SongSerializer(qs, many=True, context={"request": request})
        return ApiResponse(data=serializer.data, status=status.HTTP_200_OK)


class TagViewSet(PublicReadCrudViewSet):
    queryset = Tag.objects.order_by("id")
    read_serializer_class = TagSerializer
    write_serializer_class = TagWriteSerializer
    read_actions = ("list", "retrieve", "songs", "children")
    filter_backends = [TagFTSFilter]

    @action(detail=True, methods=["get"])
    def songs(self, request: Request, pk: str | None = None) -> ApiResponse | Response:
        tag = self.get_object()
        qs = tag.songs.prefetch_related("tags", "authors").order_by("-created_at")
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = SongSerializer(page, many=True, context={"request": request})
            return self.get_paginated_response(serializer.data)
        serializer = SongSerializer(qs, many=True, context={"request": request})
        return ApiResponse(data=serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"])
    def children(self, request: Request, pk: str | None = None) -> ApiResponse:
        tag = self.get_object()
        serializer = TagSerializer(tag.children.all(), many=True)
        return ApiResponse(data=serializer.data, status=status.HTTP_200_OK)
