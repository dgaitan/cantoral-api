from __future__ import annotations

import pytest

from cc.songs.lyrics.parser import LyricsParser
from cc.songs.models import Verse
from cc.songs.services import sync_song_verses
from cc.songs.tests.factories import SongFactory

pytestmark = pytest.mark.django_db


class TestVerseCreation:
    def test_song_factory_creates_verses(self) -> None:
        song = SongFactory.create()
        assert song.verses.count() > 0

    def test_verse_has_html_lyrics(self) -> None:
        song = SongFactory.create()
        verse = song.verses.first()
        assert verse is not None
        assert "<p>" in verse.lyrics_html
        assert "\n" not in verse.lyrics_html

    def test_verse_has_html_chords(self) -> None:
        song = SongFactory.create()
        verse = song.verses.first()
        assert verse is not None
        assert "<p>" in verse.chords_html
        assert "\n" not in verse.chords_html

    def test_verse_ordering_is_sequential(self) -> None:
        song = SongFactory.create()
        orders = list(song.verses.values_list("order", flat=True))
        assert orders == list(range(len(orders)))

    def test_verse_types_match_sections(self) -> None:
        song = SongFactory.create()
        types = list(song.verses.values_list("type", flat=True))
        assert "verse" in types
        assert "chorus" in types

    def test_delete_song_cascades_to_verses(self) -> None:
        song = SongFactory.create()
        song_id = song.id
        assert Verse.objects.filter(song_id=song_id).exists()
        song.delete()
        assert not Verse.objects.filter(song_id=song_id).exists()

    def test_sync_replaces_existing_verses(self) -> None:
        song = SongFactory.create()
        original_count = song.verses.count()
        new_lyrics = "---\ntone: A\n---\n[verse]\nOnly one section\n"
        parsed = LyricsParser(new_lyrics).parse()
        sync_song_verses(song, parsed)
        assert song.verses.count() == 1
        assert song.verses.count() < original_count

    def test_no_code_fence_in_content(self) -> None:
        song = SongFactory.create()
        lyrics_with_fence = "---\ntone: G\n---\n[verse]\n{G}\nLine one\n```\n"
        parsed = LyricsParser(lyrics_with_fence).parse()
        sync_song_verses(song, parsed)
        verse = song.verses.first()
        assert verse is not None
        assert "```" not in verse.lyrics_html
        assert "```" not in verse.chords_html

    def test_empty_sections_create_no_verses(self) -> None:
        song = SongFactory.create()
        sync_song_verses(song, {"lyric": [], "chords": []})
        assert song.verses.count() == 0
