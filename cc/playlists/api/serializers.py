from __future__ import annotations

from rest_framework import serializers

from cc.playlists.models import Playlist, PlaylistSong
from cc.songs.api.serializers import SongSerializer


class PlaylistSerializer(serializers.ModelSerializer[Playlist]):
    class Meta:
        model = Playlist
        fields = [
            "uuid",
            "name",
            "description",
            "is_public",
            "is_collaborative",
            "owner_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class PlaylistWriteSerializer(serializers.ModelSerializer[Playlist]):
    description = serializers.CharField(required=False, allow_blank=True, default="", max_length=1000)
    is_public = serializers.BooleanField(required=False, default=False)
    is_collaborative = serializers.BooleanField(required=False, default=False)

    class Meta:
        model = Playlist
        fields = ["name", "description", "is_public", "is_collaborative"]


class PlaylistSongItemSerializer(serializers.ModelSerializer[PlaylistSong]):
    song = SongSerializer(read_only=True)

    class Meta:
        model = PlaylistSong
        fields = ["order", "song"]


class AttachSongsSerializer(serializers.Serializer):
    song_ids = serializers.ListField(child=serializers.IntegerField(), min_length=1)


class ReorderSongsSerializer(serializers.Serializer):
    song_ids = serializers.ListField(child=serializers.IntegerField(), min_length=1)
