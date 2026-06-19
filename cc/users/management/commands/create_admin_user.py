from __future__ import annotations

import sys

from django.core.management.base import BaseCommand

from cc.users.models import User


class Command(BaseCommand):
    help = "Create a superuser with all content permissions enabled"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--email", required=True)
        parser.add_argument("--password", required=True)
        parser.add_argument("--name", default="Admin")

    def handle(self, *args, **options) -> None:
        email: str = options["email"]
        password: str = options["password"]
        name: str = options["name"]

        if User.objects.filter(email=email).exists():
            self.stderr.write(self.style.ERROR(f"User '{email}' already exists."))
            sys.exit(1)

        user = User.objects.create_superuser(email=email, password=password, name=name)
        user.can_create_songs = True
        user.can_publish_songs = True
        user.can_create_playlists = True
        user.save(
            update_fields=[
                "can_create_songs",
                "can_publish_songs",
                "can_create_playlists",
            ],
        )

        self.stdout.write(self.style.SUCCESS(f"Admin user created: {email}"))
