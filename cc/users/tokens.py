from __future__ import annotations

import secrets
import string
from datetime import timedelta

from django.core.mail import send_mail
from django.utils import timezone

from cc.users.models import EmailToken
from cc.users.models import User

_TOKEN_CHARS = string.ascii_uppercase + string.digits
TOKEN_TTL_MINUTES = 20


def _generate_token() -> str:
    return "".join(secrets.choice(_TOKEN_CHARS) for _ in range(6))


def create_email_token(user: User) -> EmailToken:
    user.email_tokens.filter(is_used=False).update(is_used=True)
    return EmailToken.objects.create(
        user=user,
        token=_generate_token(),
        expires_at=timezone.now() + timedelta(minutes=TOKEN_TTL_MINUTES),
    )


def verify_email_token(user: User, token: str) -> EmailToken | None:
    return user.email_tokens.filter(
        token=token,
        is_used=False,
        expires_at__gt=timezone.now(),
    ).first()


def send_email_token(user: User, token: str) -> None:
    send_mail(
        subject="Your login code",
        message=(
            f"Your login code is: {token}\n\n"
            f"It expires in {TOKEN_TTL_MINUTES} minutes."
        ),
        from_email=None,  # uses DEFAULT_FROM_EMAIL
        recipient_list=[user.email],
    )
