from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class PlaylistManager(models.Manager["Playlist"]):
    def get_queryset(self) -> models.QuerySet[Playlist]:
        return super().get_queryset().filter(deleted_at__isnull=True)


class Playlist(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=258)
    description = models.TextField(max_length=1000, blank=True, default="")
    is_public = models.BooleanField(default=False)
    is_collaborative = models.BooleanField(default=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="playlists",
    )
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects: PlaylistManager = PlaylistManager()  # type: ignore[assignment]
    all_objects = models.Manager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name


class PlaylistSong(models.Model):
    playlist = models.ForeignKey(
        Playlist,
        on_delete=models.CASCADE,
        related_name="playlist_songs",
    )
    song = models.ForeignKey(
        "songs.Song",
        on_delete=models.CASCADE,
        related_name="playlist_songs",
    )
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["order"]
        unique_together = [("playlist", "song")]

    def __str__(self) -> str:
        return f"{self.playlist_id} — {self.song_id}"
