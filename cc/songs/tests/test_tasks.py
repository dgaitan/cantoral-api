from __future__ import annotations

from unittest.mock import patch

import pytest

from cc.songs.tasks import assign_song_lyrics_task
from cc.songs.tests.factories import SongFactory
from cc.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestAssignSongLyricsTask:
    def test_updates_song_and_prints_confirmation(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        song = SongFactory(slug="a-song", name="A Song")
        user = UserFactory()
        image_url = "https://cancionero-catolico.s3.amazonaws.com/songs_chords/x.jpg"

        with (
            patch(
                "cc.songs.tasks.CreateSongFromImageService.dispatch",
                return_value=song,
            ) as mock_dispatch,
            patch(
                "cc.songs.tasks.CreateSongFromImageService.__init__",
                return_value=None,
            ) as mock_init,
        ):
            assign_song_lyrics_task(
                slug=song.slug,
                user_id=user.pk,
                image_url=image_url,
                agent="anthropic",
            )

        mock_init.assert_called_once_with(
            user=user,
            image_url=image_url,
            agent="anthropic",
            song=song,
        )
        mock_dispatch.assert_called_once()
        out = capsys.readouterr().out
        assert f"UPDATED song {song.pk}" in out
        assert "A Song" in out

    def test_unknown_slug_is_skipped(self, capsys: pytest.CaptureFixture[str]) -> None:
        user = UserFactory()

        assign_song_lyrics_task(
            slug="does-not-exist",
            user_id=user.pk,
            image_url="https://example.com/x.jpg",
        )

        out = capsys.readouterr().out
        assert "SKIPPED slug 'does-not-exist'" in out

    def test_unknown_user_is_noop(self) -> None:
        song = SongFactory(slug="a-song")
        missing_user_id = 999_999

        with patch("cc.songs.tasks.CreateSongFromImageService") as mock_service:
            assign_song_lyrics_task(
                slug=song.slug,
                user_id=missing_user_id,
                image_url="https://example.com/x.jpg",
            )

        mock_service.assert_not_called()

    def test_value_error_is_skipped_not_retried(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        song = SongFactory(slug="a-song")
        user = UserFactory()

        with (
            patch(
                "cc.songs.tasks.CreateSongFromImageService.dispatch",
                side_effect=ValueError("bad image"),
            ),
            patch(
                "cc.songs.tasks.CreateSongFromImageService.__init__",
                return_value=None,
            ),
        ):
            assign_song_lyrics_task(
                slug=song.slug,
                user_id=user.pk,
                image_url="https://example.com/x.jpg",
            )

        out = capsys.readouterr().out
        assert f"SKIPPED song {song.pk}" in out
        assert "bad image" in out

    def test_generic_exception_triggers_retry(self) -> None:
        song = SongFactory(slug="a-song")
        user = UserFactory()

        with (
            patch(
                "cc.songs.tasks.CreateSongFromImageService.dispatch",
                side_effect=RuntimeError("network blip"),
            ),
            patch(
                "cc.songs.tasks.CreateSongFromImageService.__init__",
                return_value=None,
            ),
            patch.object(
                assign_song_lyrics_task,
                "retry",
                side_effect=RuntimeError("network blip"),
            ) as mock_retry,
            pytest.raises(RuntimeError, match="network blip"),
        ):
            assign_song_lyrics_task(
                slug=song.slug,
                user_id=user.pk,
                image_url="https://example.com/x.jpg",
            )

        mock_retry.assert_called_once()
