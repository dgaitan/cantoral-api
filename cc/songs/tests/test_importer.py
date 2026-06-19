from __future__ import annotations

import json
import textwrap

import pytest

from cc.songs.importer import (
    ImportSongsService,
    InlineChordConverter,
    LyricsConverter,
    PostgresSqlDumpParser,
)
from cc.songs.models import Author, Song, Tag
from cc.users.tests.factories import UserFactory

# ---------------------------------------------------------------------------
# Inline SQL fixtures
# ---------------------------------------------------------------------------

_SONGS_COLS = (
    "deleted_at, id, created_at, updated_at, is_public, exclude_from_search,"
    " name, slug, short_description, lyrics, youtube_url, meta_title,"
    " meta_description, meta_keywords, presentation_background_color,"
    " presentation_text_color, presentation_background_image, font_size,"
    " likes, views, shares, image, lyrics_with_chords, chord_image"
)
_SONG_ROW_SUFFIX = r"\N\t\N\t\N\t\N\t\N\t\N\t\N\t\N\t0\t0\t0\t\N\t\N\t\N"

_SONGS_BLOCK = (
    f"COPY public.songs ({_SONGS_COLS}) FROM stdin;\n"
    r"\N" + "\t1\t2024-01-01\t2024-01-01\tt\tf\tSong One\tsong-one\t"
    r"\N" + "\t"
    r'[{"type":"verse","data":{"content":"<p>Line one</p><p>Line two</p>"}}]'
    "\t" + r"\N\t\N\t\N\t\N\t\N\t\N\t\N\t\N\t0\t100\t0\t\N\t\N\t\N" + "\n"
    r"\N" + "\t2\t2024-01-01\t2024-01-01\tt\tf\tSong Two\tsong-two\t"
    r"\N" + "\t"
    r'[{"type":"chorus","data":{"content":"<p>Chorus line</p>"}}]'
    "\t" + r"\N\t\N\t\N\t\N\t\N\t\N\t\N\t\N\t0\t50\t0\t\N\t\N\t\N" + "\n"
    "2024-01-02\t3\t2024-01-01\t2024-01-01\tt\tf\tDeleted Song\tdeleted-song\t"
    r"\N\t\N\t\N\t\N\t\N\t\N\t\N\t\N\t\N\t\N\t0\t0\t0\t\N\t\N\t\N" + "\n"
    r"\."
)

_AUTHORS_BLOCK = textwrap.dedent("""\
    COPY public.authors (id, created_at, updated_at, deleted_at, is_public, name, slug, short_description, biography, image, meta_title, meta_description, meta_keywords, views) FROM stdin;
    1\t2024-01-01\t2024-01-01\t\\N\tt\tJohn Doe\tjohn-doe\t\\N\tBio text\t\\N\t\\N\t\\N\t\\N\t0
    2\t2024-01-01\t2024-01-01\t\\N\tt\tJane Smith\tjane-smith\t\\N\t\\N\t\\N\t\\N\t\\N\t\\N\t0
    \\.
""")  # noqa: E501

_CATEGORIES_BLOCK = textwrap.dedent("""\
    COPY public.categories (id, created_at, updated_at, deleted_at, is_archived, name, slug, description, image, meta_title, meta_description, meta_keywords) FROM stdin;
    1\t2024-01-01\t2024-01-01\t\\N\tf\tAdoracion\tadoracion\tDesc\t\\N\t\\N\t\\N\t\\N
    2\t2024-01-01\t2024-01-01\t\\N\tf\tAlabanza\talabanza\tDesc\t\\N\t\\N\t\\N\t\\N
    \\.
""")  # noqa: E501

_AUTHORS_SONGS_BLOCK = textwrap.dedent("""\
    COPY public.authors_songs (id, created_at, updated_at, author_id, song_id) FROM stdin;
    1\t\\N\t\\N\t1\t1
    2\t\\N\t\\N\t2\t1
    \\.
""")  # noqa: E501

_CATEGORIES_SONGS_BLOCK = textwrap.dedent("""\
    COPY public.categories_songs (id, created_at, updated_at, category_id, song_id) FROM stdin;
    1\t\\N\t\\N\t1\t1
    2\t\\N\t\\N\t2\t2
    \\.
""")  # noqa: E501

_VERSES_BLOCK = textwrap.dedent("""\
    COPY public.verses (id, created_at, updated_at, song_id, order, verse_type, content) FROM stdin;
    1\t2024-01-01\t2024-01-01\t1\t1\t1\tPorque[C] eres la razon[G] de mi vida
    2\t2024-01-01\t2024-01-01\t1\t2\t2\tAqui estoy[D] Senor
    \\.
""")  # noqa: E501

_SQL_BLOCKS = [
    _SONGS_BLOCK,
    _AUTHORS_BLOCK,
    _CATEGORIES_BLOCK,
    _AUTHORS_SONGS_BLOCK,
    _CATEGORIES_SONGS_BLOCK,
]
_SQL_NO_VERSES = "\n".join(_SQL_BLOCKS)
_SQL_WITH_VERSES = f"{_SQL_NO_VERSES}\n{_VERSES_BLOCK}"


# ---------------------------------------------------------------------------
# Unit tests — PostgresSqlDumpParser
# ---------------------------------------------------------------------------


class TestPostgresSqlDumpParser:
    def test_parse_table_extracts_rows(self):
        rows = PostgresSqlDumpParser().parse_table(_AUTHORS_BLOCK, "authors")
        assert len(rows) == 2  # noqa: PLR2004
        assert rows[0]["name"] == "John Doe"
        assert rows[1]["name"] == "Jane Smith"

    def test_parse_table_handles_null(self):
        rows = PostgresSqlDumpParser().parse_table(_AUTHORS_BLOCK, "authors")
        assert rows[0]["deleted_at"] is None
        assert rows[0]["image"] is None

    def test_parse_table_returns_empty_when_table_missing(self):
        rows = PostgresSqlDumpParser().parse_table(_AUTHORS_BLOCK, "nonexistent")
        assert rows == []


# ---------------------------------------------------------------------------
# Unit tests — InlineChordConverter
# ---------------------------------------------------------------------------


class TestInlineChordConverter:
    def test_inline_chord_no_chords(self):
        line = "plain text no chords"
        assert InlineChordConverter.convert_line(line) == line

    def test_inline_chord_single_chord(self):
        result = InlineChordConverter.convert_line("text[C] more")
        lines = result.split("\n")
        assert len(lines) == 2  # noqa: PLR2004
        assert "{C}" in lines[0]
        assert lines[1] == "text more"

    def test_inline_chord_multiple_chords(self):
        line = "Porque[C] eres la razon[G] de mi vida"
        result = InlineChordConverter.convert_line(line)
        lines = result.split("\n")
        assert "{C}" in lines[0]
        assert "{G}" in lines[0]
        assert lines[1] == "Porque eres la razon de mi vida"

    def test_inline_chord_chord_at_start(self):
        result = InlineChordConverter.convert_line("[C]text")
        lines = result.split("\n")
        assert lines[0].startswith("{C}")
        assert lines[1] == "text"

    def test_inline_chord_positional_order(self):
        result = InlineChordConverter.convert_line("ab[C]cd[G]ef")
        chord_line, text_line = result.split("\n")
        c_pos = chord_line.index("{C}")
        g_pos = chord_line.index("{G}")
        assert c_pos < g_pos
        assert text_line == "abcdef"


# ---------------------------------------------------------------------------
# Unit tests — LyricsConverter.from_verses
# ---------------------------------------------------------------------------


class TestLyricsConverterFromVerses:
    def _row(self, order: int, verse_type: str, content: str) -> dict:
        return {
            "id": "1",
            "created_at": None,
            "updated_at": None,
            "song_id": "1",
            "order": str(order),
            "verse_type": verse_type,
            "content": content,
        }

    def test_maps_verse_type_to_section(self):
        rows = [self._row(1, "1", "text"), self._row(2, "2", "chorus")]
        result = LyricsConverter.from_verses(rows)
        assert "[verse]" in result
        assert "[chorus]" in result

    def test_bridge_type(self):
        rows = [self._row(1, "3", "bridge text")]
        result = LyricsConverter.from_verses(rows)
        assert "[bridge]" in result

    def test_intro_maps_to_verse(self):
        rows = [self._row(1, "4", "intro text"), self._row(2, "5", "outro text")]
        result = LyricsConverter.from_verses(rows)
        assert result.count("[verse]") == 2  # noqa: PLR2004
        assert "[intro]" not in result
        assert "[outro]" not in result

    def test_orders_sections_by_order_field(self):
        rows = [self._row(2, "2", "second"), self._row(1, "1", "first")]
        result = LyricsConverter.from_verses(rows)
        assert result.index("[verse]") < result.index("[chorus]")

    def test_includes_chord_lines(self):
        rows = [self._row(1, "1", "Porque[C] eres")]
        result = LyricsConverter.from_verses(rows)
        assert "{C}" in result

    def test_default_tone_in_frontmatter(self):
        result = LyricsConverter.from_verses([], default_tone="G")
        assert "tone: G" in result


# ---------------------------------------------------------------------------
# Unit tests — LyricsConverter.from_lyrics_json
# ---------------------------------------------------------------------------


class TestLyricsConverterFromLyricsJson:
    def test_strips_html_tags(self):
        section = {"type": "verse", "data": {"content": "<p>Hello world</p>"}}
        data = json.dumps([section])
        result = LyricsConverter.from_lyrics_json(data)
        assert "<p>" not in result
        assert "Hello world" in result

    def test_br_becomes_newline(self):
        data = json.dumps([{"type": "verse", "data": {"content": "line1<br>line2"}}])
        result = LyricsConverter.from_lyrics_json(data)
        assert "line1\nline2" in result

    def test_none_returns_valid_frontmatter(self):
        result = LyricsConverter.from_lyrics_json(None)
        assert result.startswith("---\ntone:")

    def test_default_tone_in_frontmatter(self):
        result = LyricsConverter.from_lyrics_json(None, default_tone="D")
        assert "tone: D" in result

    def test_unknown_type_maps_to_verse(self):
        data = json.dumps([{"type": "unknown_type", "data": {"content": "text"}}])
        result = LyricsConverter.from_lyrics_json(data)
        assert "[verse]" in result
        assert "[unknown_type]" not in result


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


@pytest.fixture
def admin_user(db):
    return UserFactory(can_create_songs=True, can_publish_songs=True)


@pytest.fixture
def sql_file_no_verses(tmp_path):
    f = tmp_path / "test.sql"
    f.write_text(_SQL_NO_VERSES)
    return str(f)


@pytest.fixture
def sql_file_with_verses(tmp_path):
    f = tmp_path / "test_verses.sql"
    f.write_text(_SQL_WITH_VERSES)
    return str(f)


def _svc(sql_path: str, user_email: str, **kwargs) -> ImportSongsService:
    return ImportSongsService(sql_path=sql_path, user_email=user_email, **kwargs)


@pytest.mark.django_db
class TestImportSongsService:
    def test_import_creates_authors(self, sql_file_no_verses, admin_user):
        _svc(sql_file_no_verses, admin_user.email).dispatch()
        assert Author.objects.filter(name="John Doe").exists()
        assert Author.objects.filter(name="Jane Smith").exists()

    def test_import_creates_tags_from_categories(self, sql_file_no_verses, admin_user):
        _svc(sql_file_no_verses, admin_user.email).dispatch()
        assert Tag.objects.filter(name="Adoracion").exists()
        assert Tag.objects.filter(name="Alabanza").exists()

    def test_import_creates_songs(self, sql_file_no_verses, admin_user):
        stats = _svc(sql_file_no_verses, admin_user.email).dispatch()
        assert stats["songs"] == 2  # noqa: PLR2004
        assert Song.objects.count() == 2  # noqa: PLR2004

    def test_import_skips_deleted_songs(self, sql_file_no_verses, admin_user):
        _svc(sql_file_no_verses, admin_user.email).dispatch()
        assert not Song.objects.filter(name="Deleted Song").exists()

    def test_import_links_authors_to_songs(self, sql_file_no_verses, admin_user):
        _svc(sql_file_no_verses, admin_user.email).dispatch()
        song = Song.objects.get(name="Song One")
        assert song.authors.count() == 2  # noqa: PLR2004

    def test_import_links_tags_to_songs(self, sql_file_no_verses, admin_user):
        _svc(sql_file_no_verses, admin_user.email).dispatch()
        assert Song.objects.get(name="Song One").tags.filter(name="Adoracion").exists()
        assert Song.objects.get(name="Song Two").tags.filter(name="Alabanza").exists()

    def test_import_dry_run_creates_nothing(self, sql_file_no_verses, admin_user):
        stats = _svc(sql_file_no_verses, admin_user.email, dry_run=True).dispatch()
        assert stats["songs"] == 2  # noqa: PLR2004
        assert Song.objects.count() == 0
        assert Author.objects.count() == 0

    def test_import_uses_verses_when_present(self, sql_file_with_verses, admin_user):
        _svc(sql_file_with_verses, admin_user.email).dispatch()
        song = Song.objects.get(name="Song One")
        assert "{C}" in song.plain_lyrics
        assert "[chorus]" in song.plain_lyrics

    def test_import_falls_back_to_lyrics_json(self, sql_file_no_verses, admin_user):
        _svc(sql_file_no_verses, admin_user.email).dispatch()
        song = Song.objects.get(name="Song One")
        assert "Line one" in song.plain_lyrics
        assert "[verse]" in song.plain_lyrics

    def test_import_skips_songs_with_conversion_errors(self, tmp_path, admin_user):
        bad_row = (
            r"\N" + "\t2\t2024-01-01\t2024-01-01\tt\tf\tBad Song\tbad-song\t"
            r"\N" + "\tnot valid json {{{"
            "\t" + r"\N\t\N\t\N\t\N\t\N\t\N\t\N\t\N\t0\t0\t0\t\N\t\N\t\N"
        )
        good_row = (
            r"\N" + "\t1\t2024-01-01\t2024-01-01\tt\tf\tGood Song\tgood-song\t"
            r"\N" + "\t"
            r'[{"type":"verse","data":{"content":"<p>Good</p>"}}]'
            "\t" + r"\N\t\N\t\N\t\N\t\N\t\N\t\N\t\N\t0\t0\t0\t\N\t\N\t\N"
        )
        songs_block = (
            f"COPY public.songs ({_SONGS_COLS}) FROM stdin;\n"
            f"{good_row}\n{bad_row}\n" + r"\."
        )
        sql = f"{songs_block}\n{_AUTHORS_BLOCK}\n{_CATEGORIES_BLOCK}\n"
        sql += f"{_AUTHORS_SONGS_BLOCK}\n{_CATEGORIES_SONGS_BLOCK}"
        f = tmp_path / "bad.sql"
        f.write_text(sql)
        stats = _svc(str(f), admin_user.email).dispatch()
        assert stats["songs"] == 1
        assert stats["skipped"] == 1
        assert Song.objects.count() == 1

    def test_import_imports_slug_from_dump(self, sql_file_no_verses, admin_user):
        _svc(sql_file_no_verses, admin_user.email).dispatch()
        assert Song.objects.get(name="Song One").slug == "song-one"
        assert Song.objects.get(name="Song Two").slug == "song-two"

    def test_import_falls_back_to_slugified_name_when_slug_null(
        self,
        tmp_path,
        admin_user,
    ):
        # Row with \N (NULL) in the slug column — importer must derive from name.
        row = (
            r"\N" + "\t1\t2024-01-01\t2024-01-01\tt\tf\tMy Test Song\t"
            r"\N" + "\t"
            r"\N" + "\t"
            r'[{"type":"verse","data":{"content":"<p>Hello</p>"}}]'
            "\t" + r"\N\t\N\t\N\t\N\t\N\t\N\t\N\t\N\t0\t0\t0\t\N\t\N\t\N"
        )
        songs_block = f"COPY public.songs ({_SONGS_COLS}) FROM stdin;\n{row}\n" + r"\."
        sql = f"{songs_block}\n{_AUTHORS_BLOCK}\n{_CATEGORIES_BLOCK}\n"
        sql += f"{_AUTHORS_SONGS_BLOCK}\n{_CATEGORIES_SONGS_BLOCK}"
        f = tmp_path / "null_slug.sql"
        f.write_text(sql)
        _svc(str(f), admin_user.email).dispatch()
        assert Song.objects.get(name="My Test Song").slug == "my-test-song"
