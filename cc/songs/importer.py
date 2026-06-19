from __future__ import annotations

import html
import io
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import TYPE_CHECKING

from django.db import transaction
from django.utils.text import slugify

from cc.songs.models import Author, Song, Tag
from cc.users.models import User

if TYPE_CHECKING:
    from django.core.management.base import OutputWrapper


_COPY_BLOCK_RE = re.compile(
    r"COPY public\.(\w+)\s*\(([^)]+)\)\s*FROM stdin;\n(.*?)\n\\\.",
    re.DOTALL,
)
_INLINE_CHORD_RE = re.compile(r"\[([^\]]+)\]")
_VERSE_TYPE_MAP = {
    "1": "verse",
    "2": "chorus",
    "3": "bridge",
    "4": "verse",
    "5": "verse",
}


class _HTMLStripper(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self._parts.append(data)

    def result(self) -> str:
        return "".join(self._parts)


def _strip_html(text: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    stripper = _HTMLStripper()
    stripper.feed(text)
    return html.unescape(stripper.result())


class PostgresSqlDumpParser:
    def parse_table(
        self,
        sql_text: str,
        table_name: str,
    ) -> list[dict[str, str | None]]:
        for match in _COPY_BLOCK_RE.finditer(sql_text):
            if match.group(1) != table_name:
                continue
            columns = [c.strip() for c in match.group(2).split(",")]
            rows: list[dict[str, str | None]] = []
            for line in match.group(3).splitlines():
                if not line:
                    continue
                values = line.split("\t")
                row: dict[str, str | None] = {
                    col: None if val == r"\N" else val
                    for col, val in zip(columns, values, strict=False)
                }
                rows.append(row)
            return rows
        return []


class InlineChordConverter:
    @staticmethod
    def convert_line(line: str) -> str:
        chords: list[tuple[int, str]] = []
        clean = io.StringIO()
        cursor = 0

        for m in _INLINE_CHORD_RE.finditer(line):
            clean.write(line[cursor : m.start()])
            chords.append((clean.tell(), m.group(1)))
            cursor = m.end()
        clean.write(line[cursor:])

        clean_text = clean.getvalue()
        if not chords:
            return line

        chord_chars: list[str] = []
        prev_end = 0
        for pos, chord in chords:
            token = "{" + chord + "}"
            start = max(pos, prev_end)
            while len(chord_chars) < start:
                chord_chars.append(" ")
            for ch in token:
                if start < len(chord_chars):
                    chord_chars[start] = ch
                else:
                    chord_chars.append(ch)
                start += 1
            prev_end = start

        return "".join(chord_chars).rstrip() + "\n" + clean_text


class LyricsConverter:
    @staticmethod
    def from_verses(
        verses_rows: list[dict[str, str | None]],
        default_tone: str = "C",
    ) -> str:
        sorted_rows = sorted(verses_rows, key=lambda r: int(r.get("order") or 0))
        parts = [f"---\ntone: {default_tone}\n---\n"]
        for row in sorted_rows:
            vtype = _VERSE_TYPE_MAP.get(str(row.get("verse_type") or "1"), "verse")
            content = row.get("content") or ""
            converted = "\n".join(
                InlineChordConverter.convert_line(ln) for ln in content.splitlines()
            )
            parts.append(f"[{vtype}]\n{converted}")
        return "\n\n".join(parts) + "\n"

    @staticmethod
    def from_lyrics_json(
        lyrics_json: str | None,
        default_tone: str = "C",
    ) -> str:
        header = f"---\ntone: {default_tone}\n---\n"
        if lyrics_json is None:
            return header

        sections: list[dict] = json.loads(lyrics_json)
        parts = [header]
        for section in sections:
            raw_type = section.get("type", "verse")
            vtype = raw_type if raw_type in ("verse", "chorus", "bridge") else "verse"
            raw_content: str = section.get("data", {}).get("content", "")
            content = _strip_html(raw_content).strip()
            parts.append(f"[{vtype}]\n{content}")
        return "\n\n".join(parts) + "\n"


# ---------------------------------------------------------------------------
# Import service
# ---------------------------------------------------------------------------

_IdMap = dict[str, int]
_SongRelMap = dict[str, list[int]]


def _import_authors(rows: list[_Row]) -> _IdMap:
    id_map: _IdMap = {}
    for row in rows:
        if row.get("deleted_at") is not None:
            continue
        author, _ = Author.objects.get_or_create(name=row["name"] or "")
        author.slug = row.get("slug") or ""
        author.bio = row.get("biography") or ""
        author.save(update_fields=["slug", "bio"])
        id_map[str(row["id"])] = author.pk
    return id_map


def _import_tags(
    categories_rows: list[_Row],
    folders_rows: list[_Row],
) -> tuple[_IdMap, _IdMap]:
    """Returns (category_id_map, folder_id_map) keyed by old source IDs."""
    cat_map: _IdMap = {}
    for row in categories_rows:
        if row.get("deleted_at") is not None:
            continue
        tag, _ = Tag.objects.get_or_create(name=row["name"] or "")
        tag.slug = row.get("slug") or ""
        tag.save(update_fields=["slug"])
        cat_map[str(row["id"])] = tag.pk

    folder_map: _IdMap = {}
    for row in folders_rows:
        if row.get("deleted_at") is not None:
            continue
        tag, _ = Tag.objects.get_or_create(name=row["name"] or "")
        tag.slug = row.get("slug") or ""
        tag.save(update_fields=["slug"])
        folder_map[str(row["id"])] = tag.pk

    return cat_map, folder_map


_Row = dict[str, str | None]


def _build_song_relations(
    authors_songs: list[_Row],
    categories_songs: list[_Row],
    folder_song_rows: list[_Row],
    tag_map: _IdMap,
    author_map: _IdMap,
) -> tuple[_SongRelMap, _SongRelMap]:
    song_authors: _SongRelMap = {}
    for row in authors_songs:
        sid, aid = str(row["song_id"]), str(row["author_id"])
        if aid in author_map:
            song_authors.setdefault(sid, []).append(author_map[aid])

    song_tags: _SongRelMap = {}
    for row in categories_songs:
        sid, cid = str(row["song_id"]), str(row["category_id"])
        if cid in tag_map:
            song_tags.setdefault(sid, []).append(tag_map[cid])
    for row in folder_song_rows:
        sid, fid = str(row["song_id"]), str(row["folder_id"])
        if fid in tag_map:
            song_tags.setdefault(sid, []).append(tag_map[fid])

    return song_authors, song_tags


def _convert_lyrics(
    row: dict[str, str | None],
    verses_by_song: dict[str, list[dict[str, str | None]]],
    use_verses: bool,  # noqa: FBT001
    default_tone: str,
) -> str:
    if use_verses:
        song_verses = verses_by_song.get(str(row["id"]), [])
        return LyricsConverter.from_verses(song_verses, default_tone)
    return LyricsConverter.from_lyrics_json(row.get("lyrics"), default_tone)


class ImportSongsService:
    def __init__(
        self,
        sql_path: str,
        user_email: str,
        *,
        default_tone: str = "C",
        dry_run: bool = False,
        stdout: OutputWrapper | None = None,
    ) -> None:
        self.sql_path = sql_path
        self.user_email = user_email
        self.default_tone = default_tone
        self.dry_run = dry_run
        self._stdout = stdout

    def _warn(self, msg: str) -> None:
        if self._stdout:
            self._stdout.write(msg)

    @transaction.atomic
    def dispatch(self) -> dict[str, int]:
        from django.core.management.base import CommandError  # noqa: PLC0415

        sql_text = Path(self.sql_path).read_text()
        parser = PostgresSqlDumpParser()

        songs_rows = parser.parse_table(sql_text, "songs")
        verses_rows = parser.parse_table(sql_text, "verses")
        authors_rows = parser.parse_table(sql_text, "authors")
        categories_rows = parser.parse_table(sql_text, "categories")
        folders_rows = parser.parse_table(sql_text, "folders")
        authors_songs = parser.parse_table(sql_text, "authors_songs")
        categories_songs = parser.parse_table(sql_text, "categories_songs")
        folder_song_rows = parser.parse_table(sql_text, "folder_song")

        try:
            user = User.objects.get(email=self.user_email)
        except User.DoesNotExist as exc:
            msg = f"User '{self.user_email}' not found."
            raise CommandError(msg) from exc

        author_map = _import_authors(authors_rows)
        cat_map, folder_map = _import_tags(categories_rows, folders_rows)
        tag_map = {**cat_map, **folder_map}
        song_authors, song_tags = _build_song_relations(
            authors_songs,
            categories_songs,
            folder_song_rows,
            tag_map,
            author_map,
        )

        verses_by_song: dict[str, list[dict[str, str | None]]] = {}
        for vrow in verses_rows:
            sid = str(vrow["song_id"])
            verses_by_song.setdefault(sid, []).append(vrow)
        use_verses = len(verses_rows) > 0

        songs_count = 0
        skipped = 0
        for row in songs_rows:
            if row.get("deleted_at") is not None:
                continue
            try:
                plain_lyrics = _convert_lyrics(
                    row,
                    verses_by_song,
                    use_verses,
                    self.default_tone,
                )
            except Exception as exc:  # noqa: BLE001
                self._warn(f"Skipping song {row.get('name')!r}: {exc}")
                skipped += 1
                continue

            song_name = row["name"] or ""
            song_slug = row.get("slug") or slugify(song_name)
            song = Song.objects.create(
                name=song_name,
                slug=song_slug,
                plain_lyrics=plain_lyrics,
                tone=self.default_tone,
                is_public=row.get("is_public") == "t",
                views=int(row.get("views") or 0),
                created_by=user,
            )
            sid = str(row["id"])
            if song_authors.get(sid):
                song.authors.set(song_authors[sid])
            if song_tags.get(sid):
                song.tags.set(song_tags[sid])
            songs_count += 1

        if self.dry_run:
            transaction.set_rollback(True)

        return {
            "authors": len(author_map),
            "tags": len(tag_map),
            "songs": songs_count,
            "skipped": skipped,
        }
