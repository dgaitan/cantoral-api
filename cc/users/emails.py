from __future__ import annotations

from cc.utils.emails import BaseEmail


class EmailTokenMail(BaseEmail):
    """One-time login / verification code email."""

    subject = "Your verification code"
    template_name = "users/emails/email_token"

    def __init__(self, to: str, token: str, name: str) -> None:
        super().__init__(to=to, token=token, name=name)
