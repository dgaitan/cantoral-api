from __future__ import annotations

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("songs", "0006_alter_song_slug"),
    ]

    operations = [
        migrations.CreateModel(
            name="Verse",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("verse", "Verse"),
                            ("chorus", "Chorus"),
                            ("bridge", "Bridge"),
                        ],
                        max_length=10,
                    ),
                ),
                ("order", models.PositiveIntegerField()),
                ("lyrics_html", models.TextField()),
                ("chords_html", models.TextField()),
                (
                    "song",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="verses",
                        to="songs.song",
                    ),
                ),
            ],
            options={
                "ordering": ["order"],
            },
        ),
    ]
