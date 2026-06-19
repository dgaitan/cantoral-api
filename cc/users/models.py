from __future__ import annotations

from typing import ClassVar

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import BooleanField, CharField, EmailField
from django.utils.translation import gettext_lazy as _

from .managers import UserManager


class User(AbstractUser):
    """Default custom user model for Cantoral Catolico."""

    name = CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None  # type: ignore[assignment]
    last_name = None  # type: ignore[assignment]
    email = EmailField(_("email address"), unique=True)
    username = None  # type: ignore[assignment]

    can_create_songs = BooleanField(default=False)
    can_publish_songs = BooleanField(default=False)
    can_create_playlists = BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: ClassVar[list[str]] = []

    objects: ClassVar[UserManager] = UserManager()


class EmailToken(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="email_tokens",
    )
    token = models.CharField(max_length=6)
    expires_at = models.DateTimeField()
    is_used = BooleanField(default=False)

    class Meta:
        indexes = [models.Index(fields=["user", "token"])]

    def __str__(self) -> str:
        return f"{self.user_id} — {self.token}"
