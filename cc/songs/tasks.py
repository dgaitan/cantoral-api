from __future__ import annotations

from celery import shared_task

from cc.songs.models import Song
from cc.songs.services import CreateSongFromImageService
from cc.users.models import User


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def assign_song_lyrics_task(
    self,
    *,
    slug: str,
    user_id: int,
    image_url: str,
    agent: str = "",
) -> None:
    song = Song.objects.filter(slug=slug).first()
    if song is None:
        print(f"SKIPPED slug {slug!r}: song no longer found")  # noqa: T201
        return
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return

    try:
        CreateSongFromImageService(
            user=user,
            image_url=image_url,
            agent=agent,
            song=song,
        ).dispatch()
    except ValueError as exc:
        print(f"SKIPPED song {song.pk} ({song.name!r}): {exc}")  # noqa: T201
        return
    except Exception as exc:
        raise self.retry(exc=exc) from exc

    print(f"UPDATED song {song.pk} ({song.name!r}) lyrics from {image_url}")  # noqa: T201
