from __future__ import annotations

from typing import TYPE_CHECKING

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from cc.songs.api.permissions import CanCreateSongs
from cc.songs.api.permissions import CanPublishSongs
from cc.songs.api.serializers import AuthorSerializer
from cc.songs.api.serializers import AuthorWriteSerializer
from cc.songs.api.serializers import CreateSongSerializer
from cc.songs.api.serializers import SongSerializer
from cc.songs.api.serializers import TransportSerializer
from cc.songs.lyrics.transport import ChordTransposer
from cc.songs.models import Author
from cc.songs.models import Song
from cc.songs.services import CreateSongService
from cc.songs.services import PublishSongService
from cc.utils.responses import ApiResponse

if TYPE_CHECKING:
    from rest_framework.request import Request


class SongViewSet(GenericViewSet):
    queryset = Song.objects.prefetch_related("tags", "authors").all()
    permission_classes = [IsAuthenticated]

    def get_permissions(self):  # type: ignore[override]
        if self.action == "retrieve":
            return [AllowAny()]
        if self.action == "create":
            return [CanCreateSongs()]
        if self.action == "publish":
            return [CanPublishSongs()]
        if self.action == "transport":
            return [AllowAny()]
        return super().get_permissions()

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


class AuthorViewSet(GenericViewSet):
    queryset = Author.objects.all()

    def get_permissions(self):  # type: ignore[override]
        if self.action in ("list", "retrieve", "songs"):
            return [AllowAny()]
        return [CanCreateSongs()]

    def list(self, request: Request) -> ApiResponse:
        authors = self.get_queryset()
        serializer = AuthorSerializer(authors, many=True)
        return ApiResponse(data=serializer.data, status=status.HTTP_200_OK)

    def retrieve(self, request: Request, pk: str | None = None) -> ApiResponse:
        author = self.get_object()
        serializer = AuthorSerializer(author)
        return ApiResponse(data=serializer.data, status=status.HTTP_200_OK)

    def create(self, request: Request) -> ApiResponse:
        serializer = AuthorWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return ApiResponse(
                errors=serializer.errors,
                success=False,
                status=status.HTTP_400_BAD_REQUEST,
            )
        author = serializer.save()
        return ApiResponse(
            data=AuthorSerializer(author).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request: Request, pk: str | None = None) -> ApiResponse:
        author = self.get_object()
        serializer = AuthorWriteSerializer(author, data=request.data)
        if not serializer.is_valid():
            return ApiResponse(
                errors=serializer.errors,
                success=False,
                status=status.HTTP_400_BAD_REQUEST,
            )
        author = serializer.save()
        return ApiResponse(data=AuthorSerializer(author).data, status=status.HTTP_200_OK)

    def partial_update(self, request: Request, pk: str | None = None) -> ApiResponse:
        author = self.get_object()
        serializer = AuthorWriteSerializer(author, data=request.data, partial=True)
        if not serializer.is_valid():
            return ApiResponse(
                errors=serializer.errors,
                success=False,
                status=status.HTTP_400_BAD_REQUEST,
            )
        author = serializer.save()
        return ApiResponse(data=AuthorSerializer(author).data, status=status.HTTP_200_OK)

    def destroy(self, request: Request, pk: str | None = None) -> Response:
        author = self.get_object()
        author.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"])
    def songs(self, request: Request, pk: str | None = None) -> ApiResponse:
        author = self.get_object()
        qs = author.songs.all()
        serializer = SongSerializer(qs, many=True, context={"request": request})
        return ApiResponse(data=serializer.data, status=status.HTTP_200_OK)
