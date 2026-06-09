from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import transaction
from django.utils.text import slugify

from cc.songs.lyrics.parser import LyricsParser
from cc.songs.models import Author
from cc.songs.models import Song
from cc.songs.models import Tag

if TYPE_CHECKING:
    from cc.users.models import User


class CreateSongService:
    def __init__(
        self,
        user: User,
        name: str,
        authors_ids: list[int],
        tags_ids: list[int],
        lyrics: str,
        slug: str = "",
    ) -> None:
        self.user = user
        self.name = name
        self.slug = slug
        self.authors_ids = authors_ids
        self.tags_ids = tags_ids
        self.lyrics = lyrics

    @transaction.atomic
    def dispatch(self) -> Song:
        parsed = LyricsParser(self.lyrics).parse()
        song = Song.objects.create(
            name=self.name,
            slug=self.slug or slugify(self.name),
            plain_lyrics=self.lyrics,
            tone=parsed["tone"],
            is_public=False,
            created_by=self.user,
        )
        if self.authors_ids:
            song.authors.set(Author.objects.filter(pk__in=self.authors_ids))
        if self.tags_ids:
            song.tags.set(Tag.objects.filter(pk__in=self.tags_ids))
        return song


class UpdateSongService:
    def __init__(
        self,
        song: Song,
        name: str | None,
        authors_ids: list[int] | None,
        tags_ids: list[int] | None,
        lyrics: str | None,
        slug: str | None = None,
    ) -> None:
        self.song = song
        self.name = name
        self.slug = slug
        self.authors_ids = authors_ids
        self.tags_ids = tags_ids
        self.lyrics = lyrics

    @transaction.atomic
    def dispatch(self) -> Song:
        dirty = False
        if self.name is not None:
            self.song.name = self.name
            dirty = True
        if self.slug is not None:
            self.song.slug = self.slug
            dirty = True
        if self.lyrics is not None:
            parsed = LyricsParser(self.lyrics).parse()
            self.song.plain_lyrics = self.lyrics
            self.song.tone = parsed["tone"]
            dirty = True
        if dirty:
            self.song.save()
        if self.authors_ids is not None:
            self.song.authors.set(Author.objects.filter(pk__in=self.authors_ids))
        if self.tags_ids is not None:
            self.song.tags.set(Tag.objects.filter(pk__in=self.tags_ids))
        return self.song


class PublishSongService:
    def __init__(self, song: Song) -> None:
        self.song = song

    @transaction.atomic
    def dispatch(self) -> Song:
        self.song.is_public = True
        self.song.save(update_fields=["is_public"])
        return self.song
