from __future__ import annotations

from typing import TYPE_CHECKING

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from cc.songs.api.permissions import CanCreateSongs, CanPublishSongs
from cc.songs.api.serializers import (
    AuthorSerializer,
    AuthorWriteSerializer,
    SongSerializer,
    SongWriteSerializer,
    TagSerializer,
    TagWriteSerializer,
    TransportSerializer,
)
from cc.songs.filters import AuthorFTSFilter, TagFTSFilter
from cc.songs.lyrics.transport import ChordTransposer
from cc.songs.models import Author, Song, Tag
from cc.songs.queries import SongQuerySet
from cc.songs.services import (
    CreateSongService,
    PublishSongService,
    ToggleFavoriteService,
    UpdateSongService,
)
from cc.utils.pagination import ApiPageNumberPagination
from cc.utils.responses import ApiResponse
from cc.utils.throttles import FavoriteToggleThrottle
from cc.utils.views import PublicReadCrudViewSet, BaseViewSet

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from rest_framework.request import Request


class SongViewSet(BaseViewSet):
    queryset = SongQuerySet().get_queryset()
    permission_classes_mapping = {
        "retrieve": [AllowAny],
        "list": [AllowAny],
        "create": [CanCreateSongs],
        "update": [CanCreateSongs],
        "partial_update": [CanCreateSongs],
        "destroy": [CanCreateSongs],
        "publish": [CanPublishSongs],
        "transport": [AllowAny],
        "favorites": [IsAuthenticated],
    }
    throttle_classes_mapping = {
        "favorites": [FavoriteToggleThrottle],
    }
    pagination_class = ApiPageNumberPagination

    def list(self, request: Request) -> ApiResponse | Response:
        try:
            queryset: QuerySet[Song] = SongQuerySet().with_filters(**request.query_params).get_queryset()
        except ValueError as exc:
            return ApiResponse(errors=[str(exc)], success=False, status=status.HTTP_400_BAD_REQUEST)
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
        serializer = SongWriteSerializer(data=request.data)
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
                slug=serializer.validated_data.get("slug", ""),
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

    def update(self, request: Request, pk: str | None = None) -> ApiResponse:
        song = self.get_object()
        serializer = SongWriteSerializer(
            data=request.data, context={"song_instance": song},
        )
        if not serializer.is_valid():
            return ApiResponse(
                errors=serializer.errors,
                success=False,
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            song = UpdateSongService(
                song=song,
                name=serializer.validated_data["name"],
                slug=serializer.validated_data.get("slug") or None,
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
            status=status.HTTP_200_OK,
        )

    def partial_update(self, request: Request, pk: str | None = None) -> ApiResponse:
        song = self.get_object()
        serializer = SongWriteSerializer(
            data=request.data, partial=True, context={"song_instance": song},
        )
        if not serializer.is_valid():
            return ApiResponse(
                errors=serializer.errors,
                success=False,
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            song = UpdateSongService(
                song=song,
                name=serializer.validated_data.get("name"),
                slug=serializer.validated_data.get("slug") or None,
                authors_ids=serializer.validated_data.get("authors"),
                tags_ids=serializer.validated_data.get("tags"),
                lyrics=serializer.validated_data.get("lyrics"),
            ).dispatch()
        except ValueError as exc:
            return ApiResponse(
                errors=[str(exc)],
                success=False,
                status=status.HTTP_400_BAD_REQUEST,
            )
        return ApiResponse(
            data=SongSerializer(song, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def destroy(self, request: Request, pk: str | None = None) -> Response:
        self.get_object().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def publish(self, request: Request, pk: str | None = None) -> ApiResponse:
        song = self.get_object()
        song = PublishSongService(song).dispatch()
        return ApiResponse(
            data=SongSerializer(song, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def favorites(self, request: Request, pk: str | None = None) -> ApiResponse:
        song = self.get_object()
        is_favorite = ToggleFavoriteService(user=request.user, song=song).dispatch()  # type: ignore[arg-type]
        return ApiResponse(data={"is_favorite": is_favorite}, status=status.HTTP_200_OK)

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
        qs: QuerySet[Song] = SongQuerySet().with_filters(author_id=author.id).get_queryset()
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
        qs: QuerySet[Song] = SongQuerySet().with_filters(tag_id=tag.id).get_queryset()
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
