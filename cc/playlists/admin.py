from __future__ import annotations

from django.contrib import admin

from cc.playlists.models import Playlist, PlaylistSong


class PlaylistSongInline(admin.TabularInline):
    model = PlaylistSong
    extra = 0
    ordering = ["order"]


@admin.register(Playlist)
class PlaylistAdmin(admin.ModelAdmin):
    list_display = ["name", "owner", "is_public", "is_collaborative", "deleted_at", "created_at"]
    list_filter = ["is_public", "is_collaborative"]
    search_fields = ["name", "description"]
    inlines = [PlaylistSongInline]
    readonly_fields = ["uuid", "created_at", "updated_at"]
