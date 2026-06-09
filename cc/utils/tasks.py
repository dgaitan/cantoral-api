from __future__ import annotations

from typing import Any

from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_email_task(
    self: Any,
    to: str,
    subject: str,
    template_name: str,
    context: dict[str, Any],
) -> None:
    """Render and send an HTML+plain-text email. Retries up to 3 times on failure."""
    html_body = render_to_string(f"{template_name}.html", context)
    plain_body = render_to_string(f"{template_name}.txt", context)
    msg = EmailMultiAlternatives(subject=subject, body=plain_body, to=[to])
    msg.attach_alternative(html_body, "text/html")
    try:
        msg.send()
    except Exception as exc:
        raise self.retry(exc=exc) from exc
