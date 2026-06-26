from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone

from cc.playlists.models import Playlist, PlaylistSong
from cc.songs.models import Song

if TYPE_CHECKING:
    from cc.users.models import User


class CreatePlaylistService:
    def __init__(
        self,
        user: User,
        name: str,
        description: str = "",
        is_public: bool = False,
        is_collaborative: bool = False,
    ) -> None:
        self.user = user
        self.name = name
        self.description = description
        self.is_public = is_public
        self.is_collaborative = is_collaborative

    @transaction.atomic
    def dispatch(self) -> Playlist:
        return Playlist.objects.create(
            owner=self.user,
            name=self.name,
            description=self.description,
            is_public=self.is_public,
            is_collaborative=self.is_collaborative,
        )


class UpdatePlaylistService:
    def __init__(
        self,
        playlist: Playlist,
        name: str | None = None,
        description: str | None = None,
        is_public: bool | None = None,
        is_collaborative: bool | None = None,
    ) -> None:
        self.playlist = playlist
        self.name = name
        self.description = description
        self.is_public = is_public
        self.is_collaborative = is_collaborative

    @transaction.atomic
    def dispatch(self) -> Playlist:
        fields: list[str] = []
        if self.name is not None:
            self.playlist.name = self.name
            fields.append("name")
        if self.description is not None:
            self.playlist.description = self.description
            fields.append("description")
        if self.is_public is not None:
            self.playlist.is_public = self.is_public
            fields.append("is_public")
        if self.is_collaborative is not None:
            self.playlist.is_collaborative = self.is_collaborative
            fields.append("is_collaborative")
        if fields:
            fields.append("updated_at")
            self.playlist.save(update_fields=fields)
        return self.playlist


class DeletePlaylistService:
    def __init__(self, playlist: Playlist) -> None:
        self.playlist = playlist

    @transaction.atomic
    def dispatch(self) -> None:
        self.playlist.deleted_at = timezone.now()
        self.playlist.save(update_fields=["deleted_at"])


class AttachSongsService:
    """Toggle songs in/out of a playlist: adds if absent, removes if present."""

    def __init__(self, playlist: Playlist, song_ids: list[int]) -> None:
        self.playlist = playlist
        self.song_ids = song_ids

    @transaction.atomic
    def dispatch(self) -> None:
        missing = set(self.song_ids) - set(
            Song.objects.filter(id__in=self.song_ids).values_list("id", flat=True)
        )
        if missing:
            raise ValueError(f"Songs not found: {sorted(missing)}")

        existing: set[int] = set(
            PlaylistSong.objects.filter(playlist=self.playlist).values_list(
                "song_id", flat=True
            )
        )
        to_remove = [sid for sid in self.song_ids if sid in existing]
        to_add = [sid for sid in self.song_ids if sid not in existing]

        if to_remove:
            PlaylistSong.objects.filter(
                playlist=self.playlist, song_id__in=to_remove
            ).delete()

        if to_add:
            max_order: int = (
                PlaylistSong.objects.filter(playlist=self.playlist)
                .order_by("-order")
                .values_list("order", flat=True)
                .first()
                or 0
            )
            PlaylistSong.objects.bulk_create(
                [
                    PlaylistSong(
                        playlist=self.playlist,
                        song_id=sid,
                        order=max_order + i + 1,
                    )
                    for i, sid in enumerate(to_add)
                ]
            )


class ReorderSongsService:
    """Reorder playlist songs by providing the full ordered list of song IDs."""

    def __init__(self, playlist: Playlist, song_ids: list[int]) -> None:
        self.playlist = playlist
        self.song_ids = song_ids

    @transaction.atomic
    def dispatch(self) -> None:
        existing: set[int] = set(
            PlaylistSong.objects.filter(playlist=self.playlist).values_list(
                "song_id", flat=True
            )
        )
        if set(self.song_ids) != existing:
            raise ValueError(
                "song_ids must match exactly the songs currently in the playlist."
            )

        by_song_id = {
            ps.song_id: ps
            for ps in PlaylistSong.objects.filter(playlist=self.playlist)
        }
        for order, song_id in enumerate(self.song_ids, start=1):
            by_song_id[song_id].order = order

        PlaylistSong.objects.bulk_update(list(by_song_id.values()), ["order"])
