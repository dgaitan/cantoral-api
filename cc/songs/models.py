from __future__ import annotations

from django.conf import settings
from django.db import models


class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True, max_length=255)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
    )

    def __str__(self) -> str:
        return self.name


class Author(models.Model):
    name = models.CharField(max_length=255)
    image = models.URLField(blank=True, default="")
    bio = models.TextField(blank=True, default="")
    slug = models.SlugField(unique=False, blank=True, max_length=255)

    def __str__(self) -> str:
        return self.name


class Song(models.Model):
    name = models.CharField(max_length=255)
    views = models.PositiveIntegerField(default=0)
    tags = models.ManyToManyField(Tag, blank=True, related_name="songs")
    authors = models.ManyToManyField(Author, blank=True, related_name="songs")
    plain_lyrics = models.TextField()
    tone = models.CharField(max_length=10)
    is_public = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="songs",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name
