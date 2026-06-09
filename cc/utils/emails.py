from __future__ import annotations

from typing import Any

from cc.utils.tasks import send_email_task


class BaseEmail:
    """
    Base class for transactional emails.

    Subclass it, declare `subject` and `template_name`, and call `.send()`.
    Templates are resolved as `<template_name>.html` and `<template_name>.txt`.

    Usage:
        class WelcomeMail(BaseEmail):
            subject = "Welcome!"
            template_name = "users/emails/welcome"

            def __init__(self, to: str, name: str) -> None:
                super().__init__(to=to, name=name)

        WelcomeMail(to="user@example.com", name="Alice").send()
    """

    subject: str
    template_name: str

    def __init__(self, to: str, **context: Any) -> None:
        self.to = to
        self.context = context

    def send(self) -> None:
        send_email_task.delay(
            to=self.to,
            subject=self.subject,
            template_name=self.template_name,
            context=self.context,
        )
