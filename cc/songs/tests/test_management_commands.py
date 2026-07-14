from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from django.core.management import CommandError, call_command

from cc.songs.management.commands.assign_song_lyrics import S3_BASE_URL
from cc.songs.tests.factories import SongFactory
from cc.users.tests.factories import UserFactory

if TYPE_CHECKING:
    from pathlib import Path

_EXPECTED_ENQUEUE_COUNT = 2
_SECOND_SONG_COUNTDOWN = 3

_COLUMNS = [
    "deleted_at",
    "id",
    "created_at",
    "updated_at",
    "is_public",
    "exclude_from_search",
    "name",
    "slug",
    "short_description",
    "lyrics",
    "youtube_url",
    "meta_title",
    "meta_description",
    "meta_keywords",
    "presentation_background_color",
    "presentation_text_color",
    "presentation_background_image",
    "font_size",
    "likes",
    "views",
    "shares",
    "image",
    "lyrics_with_chords",
    "chord_image",
]


def _row(
    *,
    legacy_id: int,
    name: str,
    slug: str,
    chord_image: str = r"\N",
    deleted_at: str = r"\N",
) -> str:
    values = dict.fromkeys(_COLUMNS, r"\N")
    values.update(
        {
            "deleted_at": deleted_at,
            "id": str(legacy_id),
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01",
            "is_public": "t",
            "exclude_from_search": "f",
            "name": name,
            "slug": slug,
            "font_size": "0",
            "likes": "0",
            "views": "0",
            "chord_image": chord_image,
        },
    )
    return "\t".join(values[col] for col in _COLUMNS)


def _build_sql(rows: list[str]) -> str:
    columns = ", ".join(_COLUMNS)
    body = "\n".join(rows)
    return f"COPY public.songs ({columns}) FROM stdin;\n{body}\n\\.\n"


@pytest.fixture
def actor():
    return UserFactory(email="actor@example.com")


@pytest.mark.django_db
class TestAssignSongLyricsCommand:
    def _write_sql(self, tmp_path: Path, rows: list[str]) -> str:
        sql_path = tmp_path / "legacy.sql"
        sql_path.write_text(_build_sql(rows))
        return str(sql_path)

    def test_enqueues_matched_songs_with_staggered_countdown(
        self,
        tmp_path: Path,
        actor,
    ) -> None:
        song_a = SongFactory(slug="song-a")
        song_b = SongFactory(slug="song-b")
        SongFactory(slug="song-e")  # matches a soft-deleted legacy row
        rows = [
            _row(
                legacy_id=101,
                name="Song A",
                slug="song-a",
                chord_image="songs_chords/AAA.jpg",
            ),
            _row(
                legacy_id=102,
                name="Song B",
                slug="song-b",
                chord_image="songs_chords/BBB.jpg",
            ),
            _row(legacy_id=103, name="Song C", slug="song-c", chord_image=r"\N"),
            _row(
                legacy_id=104,
                name="Song D",
                slug="song-d-missing",
                chord_image="songs_chords/DDD.jpg",
            ),
            _row(
                legacy_id=105,
                name="Song E",
                slug="song-e",
                chord_image="songs_chords/EEE.jpg",
                deleted_at="2024-02-01",
            ),
        ]
        sql_path = self._write_sql(tmp_path, rows)

        with patch(
            "cc.songs.management.commands.assign_song_lyrics"
            ".assign_song_lyrics_task.apply_async",
        ) as mock_apply_async:
            call_command("assign_song_lyrics", file=sql_path, user=actor.email)

        assert mock_apply_async.call_count == _EXPECTED_ENQUEUE_COUNT
        first_call, second_call = mock_apply_async.call_args_list

        assert first_call.kwargs["kwargs"] == {
            "slug": "song-a",
            "user_id": actor.pk,
            "image_url": S3_BASE_URL + "songs_chords/AAA.jpg",
            "agent": "",
        }
        assert first_call.kwargs["countdown"] == 0

        legacy_id_song_a = 101
        legacy_id_song_b = 102
        expected_image_url_b = S3_BASE_URL + "songs_chords/BBB.jpg"

        assert second_call.kwargs["kwargs"]["slug"] == "song-b"
        assert second_call.kwargs["kwargs"]["image_url"] == expected_image_url_b
        assert second_call.kwargs["countdown"] == _SECOND_SONG_COUNTDOWN

        # legacy id never matches the Django pk — proves lookup is slug-based only
        assert song_a.pk != legacy_id_song_a
        assert song_b.pk != legacy_id_song_b

    def test_skips_already_migrated_song(self, tmp_path: Path, actor) -> None:
        chord_image = "songs_chords/FFF.jpg"
        SongFactory(slug="song-f", source_image_url=S3_BASE_URL + chord_image)
        rows = [
            _row(legacy_id=106, name="Song F", slug="song-f", chord_image=chord_image),
        ]
        sql_path = self._write_sql(tmp_path, rows)

        with patch(
            "cc.songs.management.commands.assign_song_lyrics"
            ".assign_song_lyrics_task.apply_async",
        ) as mock_apply_async:
            call_command("assign_song_lyrics", file=sql_path, user=actor.email)

        mock_apply_async.assert_not_called()

    def test_dry_run_does_not_enqueue(self, tmp_path: Path, actor) -> None:
        SongFactory(slug="song-a")
        rows = [
            _row(
                legacy_id=101,
                name="Song A",
                slug="song-a",
                chord_image="songs_chords/AAA.jpg",
            ),
        ]
        sql_path = self._write_sql(tmp_path, rows)

        with patch(
            "cc.songs.management.commands.assign_song_lyrics"
            ".assign_song_lyrics_task.apply_async",
        ) as mock_apply_async:
            call_command(
                "assign_song_lyrics",
                file=sql_path,
                user=actor.email,
                dry_run=True,
            )

        mock_apply_async.assert_not_called()

    def test_limit_caps_number_enqueued(self, tmp_path: Path, actor) -> None:
        SongFactory(slug="song-a")
        SongFactory(slug="song-b")
        rows = [
            _row(
                legacy_id=101,
                name="Song A",
                slug="song-a",
                chord_image="songs_chords/AAA.jpg",
            ),
            _row(
                legacy_id=102,
                name="Song B",
                slug="song-b",
                chord_image="songs_chords/BBB.jpg",
            ),
        ]
        sql_path = self._write_sql(tmp_path, rows)

        with patch(
            "cc.songs.management.commands.assign_song_lyrics"
            ".assign_song_lyrics_task.apply_async",
        ) as mock_apply_async:
            call_command("assign_song_lyrics", file=sql_path, user=actor.email, limit=1)

        assert mock_apply_async.call_count == 1
        assert mock_apply_async.call_args.kwargs["kwargs"]["slug"] == "song-a"

    def test_missing_user_raises_command_error(self, tmp_path: Path) -> None:
        sql_path = self._write_sql(tmp_path, [])

        with pytest.raises(CommandError):
            call_command("assign_song_lyrics", file=sql_path, user="nope@example.com")
