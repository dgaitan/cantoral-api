from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import F
from django.utils.text import slugify

from cc.songs.extraction import ChordSheetExtractor, get_agent
from cc.songs.lyrics.parser import LyricsParser
from cc.songs.models import Author, Favorite, Song, Tag, Verse

if TYPE_CHECKING:
    from cc.users.models import User


class CreateSongService:
    def __init__(  # noqa: PLR0913
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
        sync_song_verses(song, parsed)
        return song


class UpdateSongService:
    def __init__(  # noqa: PLR0913
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
        parsed = None
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
        if parsed is not None:
            sync_song_verses(self.song, parsed)
        return self.song


def sync_song_verses(song: Song, parsed: dict) -> None:
    song.verses.all().delete()
    verses = [
        Verse(
            song=song,
            type=lyric_section["type"],
            order=i,
            lyrics_html=lyric_section["content"],
            chords_html=chord_section["content"],
        )
        for i, (lyric_section, chord_section) in enumerate(
            zip(parsed["lyric"], parsed["chords"], strict=True),
        )
    ]
    if verses:
        Verse.objects.bulk_create(verses)


def _sync_song_verses(song: Song) -> None:
    parsed = LyricsParser(song.plain_lyrics).parse()
    sync_song_verses(song, parsed)


class PublishSongService:
    def __init__(self, song: Song) -> None:
        self.song = song

    @transaction.atomic
    def dispatch(self) -> Song:
        self.song.is_public = True
        self.song.save(update_fields=["is_public"])
        return self.song


class RegisterSongViewService:
    def __init__(self, song: Song) -> None:
        self.song = song

    @transaction.atomic
    def dispatch(self) -> Song:
        Song.objects.filter(pk=self.song.pk).update(views=F("views") + 1)
        self.song.refresh_from_db(fields=["views"])
        return self.song


class ToggleFavoriteService:
    def __init__(self, user: User, song: Song) -> None:
        self.user = user
        self.song = song

    @transaction.atomic
    def dispatch(self) -> bool:
        favorite, created = Favorite.objects.get_or_create(
            user=self.user,
            song=self.song,
        )
        if not created:
            favorite.delete()
            result = False
        else:
            result = True
        cache.set(
            f"user_{self.user.pk}_favorited_song_{self.song.pk}",
            result,
            timeout=3600,
        )
        return result


class CreateSongFromImageService:
    def __init__(  # noqa: PLR0913
        self,
        user: User,
        image_url: str = "",
        name: str = "",
        agent: str = "",
        authors_ids: list[int] | None = None,
        tags_ids: list[int] | None = None,
        image_data: tuple[bytes, str] | None = None,
        song: Song | None = None,
    ) -> None:
        self.user = user
        self.image_url = image_url
        self.image_data = image_data
        self.name = name
        self.agent = agent
        self.authors_ids = authors_ids or []
        self.tags_ids = tags_ids or []
        self.song = song

    @transaction.atomic
    def dispatch(self) -> Song:
        agent_name = self.agent or settings.CHORD_EXTRACTION_DEFAULT_AGENT
        agent = get_agent(agent_name)
        extracted = ChordSheetExtractor(
            self.image_url or None,
            agent,
            self.image_data,
        ).extract()
        plain_lyrics = extracted["plain_lyrics"]
        if self.song is not None:
            song = UpdateSongService(
                song=self.song,
                name=None,
                authors_ids=self.authors_ids or None,
                tags_ids=self.tags_ids or None,
                lyrics=plain_lyrics,
            ).dispatch()
        else:
            song = CreateSongService(
                user=self.user,
                name=self.name or extracted["name"],
                authors_ids=self.authors_ids,
                tags_ids=self.tags_ids,
                lyrics=plain_lyrics,
            ).dispatch()
        if self.image_url:
            song.source_image_url = self.image_url
            song.save(update_fields=["source_image_url"])
        return song
