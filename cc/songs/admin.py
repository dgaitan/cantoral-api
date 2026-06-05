from django.contrib import admin

from cc.songs.models import Author
from cc.songs.models import Song
from cc.songs.models import Tag


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ["id", "name"]
    search_fields = ["name"]


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ["id", "name"]
    search_fields = ["name"]


@admin.register(Song)
class SongAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ["id", "name", "tone", "is_public", "created_by", "created_at"]
    list_filter = ["is_public", "tone"]
    search_fields = ["name"]
    filter_horizontal = ["tags", "authors"]
    readonly_fields = ["views", "created_at", "updated_at"]
