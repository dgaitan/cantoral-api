from __future__ import annotations

from django.core.management.base import BaseCommand

from cc.songs.importer import ImportSongsService


class Command(BaseCommand):
    help = "Import songs from a PostgreSQL SQL dump"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--file", required=True, help="Path to .sql dump file")
        parser.add_argument("--user", required=True, help="Email of created_by user")
        parser.add_argument("--default-tone", default="C", help="Default tone")
        parser.add_argument("--dry-run", action="store_true", help="Preview only")

    def handle(self, *args, **options) -> None:
        service = ImportSongsService(
            sql_path=options["file"],
            user_email=options["user"],
            default_tone=options["default_tone"],
            dry_run=options["dry_run"],
            stdout=self.stdout,  # type: ignore[arg-type]
        )
        stats = service.dispatch()
        prefix = "[DRY RUN] " if options["dry_run"] else ""
        self.stdout.write(self.style.SUCCESS(f"{prefix}Done: {stats}"))
