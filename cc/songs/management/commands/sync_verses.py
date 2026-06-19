from __future__ import annotations

from django.core.management.base import BaseCommand

from cc.songs.lyrics.parser import LyricsParser
from cc.songs.models import Song
from cc.songs.services import sync_song_verses


class Command(BaseCommand):
    help = "Parse plain_lyrics for all songs and (re)populate Verse rows."

    def add_arguments(self, parser):
        parser.add_argument(
            "--song-id",
            type=int,
            help="Only sync the song with this ID.",
        )

    def handle(self, *args, **options):
        qs = Song.objects.all()
        if song_id := options.get("song_id"):
            qs = qs.filter(pk=song_id)

        total = qs.count()
        synced = skipped = 0

        for song in qs.iterator():
            try:
                parsed = LyricsParser(song.plain_lyrics).parse()
                sync_song_verses(song, parsed)
                synced += 1
            except ValueError as exc:
                self.stderr.write(f"  skip song {song.pk} ({song.name}): {exc}")
                skipped += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Done — {synced}/{total} synced, {skipped} skipped.",
            ),
        )
