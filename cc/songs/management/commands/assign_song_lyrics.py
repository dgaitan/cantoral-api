from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from cc.songs.importer import PostgresSqlDumpParser
from cc.songs.models import Song
from cc.songs.tasks import assign_song_lyrics_task
from cc.users.models import User

S3_BASE_URL = "https://cancionero-catolico.s3.amazonaws.com/"
STAGGER_SECONDS = 3


class Command(BaseCommand):
    help = "Re-extract chord-sheet lyrics for legacy songs via the AI vision pipeline"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--file",
            default=str(settings.BASE_DIR / "cc.sql"),
            help="Path to the legacy .sql dump file",
        )
        parser.add_argument(
            "--user",
            required=True,
            help="Email of user attributed as actor",
        )
        parser.add_argument(
            "--agent",
            default="",
            help="Extraction agent: anthropic|gemini|openai (default: settings)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview matches without enqueueing tasks",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Enqueue at most N songs (for testing against real data)",
        )

    def handle(self, *args, **options) -> None:
        try:
            user = User.objects.get(email=options["user"])
        except User.DoesNotExist as exc:
            msg = f"User '{options['user']}' not found."
            raise CommandError(msg) from exc

        sql_text = Path(options["file"]).read_text()
        rows = PostgresSqlDumpParser().parse_table(sql_text, "songs")
        limit = options["limit"]

        enqueued = no_chord_image = not_found = deleted = already_migrated = 0
        for row in rows:
            if limit is not None and enqueued >= limit:
                break
            if row.get("deleted_at") is not None:
                deleted += 1
                continue
            chord_image = row.get("chord_image")
            if not chord_image:
                no_chord_image += 1
                continue
            slug = row.get("slug") or ""
            song = Song.objects.filter(slug=slug).first()
            if song is None:
                not_found += 1
                self.stdout.write(f"  skip (slug not found): {slug}")
                continue

            image_url = S3_BASE_URL + chord_image
            if song.source_image_url == image_url:
                already_migrated += 1
                self.stdout.write(f"  skip (already migrated): {slug}")
                continue

            self.stdout.write(
                f"  enqueue song {song.pk} ({song.name!r}) slug={slug} -> {image_url}",
            )
            if not options["dry_run"]:
                assign_song_lyrics_task.apply_async(
                    kwargs={
                        "slug": slug,
                        "user_id": user.pk,
                        "image_url": image_url,
                        "agent": options["agent"],
                    },
                    countdown=STAGGER_SECONDS * enqueued,
                )
            enqueued += 1

        prefix = "[DRY RUN] " if options["dry_run"] else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"{prefix}Done: {enqueued} enqueued, {not_found} slug-not-found, "
                f"{no_chord_image} no-chord-image, {deleted} soft-deleted-skipped, "
                f"{already_migrated} already-migrated-skipped (total: {len(rows)})",
            ),
        )
