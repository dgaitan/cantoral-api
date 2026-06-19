from __future__ import annotations

from datetime import timedelta
from http import HTTPStatus

import pytest
from django.core import mail
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from cc.users.models import EmailToken, User
from cc.users.tests.factories import EmailTokenFactory, UserFactory

pytestmark = pytest.mark.django_db

_TEST_PASSWORD = "StrongTestPass1!"  # noqa: S105


class TestRegister:
    @pytest.mark.django_db(transaction=True)
    def test_creates_inactive_user_and_sends_email(self) -> None:
        client = APIClient()
        response = client.post(
            reverse("auth-register"),
            {"name": "New User", "email": "new@example.com", "password": _TEST_PASSWORD},  # noqa: E501
        )
        assert response.status_code == HTTPStatus.CREATED
        assert response.data["success"] is True
        assert len(mail.outbox) == 1
        assert "new@example.com" in mail.outbox[0].to
        user = User.objects.get(email="new@example.com")
        assert not user.is_active

    def test_lowercases_email(self) -> None:
        client = APIClient()
        client.post(
            reverse("auth-register"),
            {"name": "Upper User", "email": "UPPER@EXAMPLE.COM", "password": _TEST_PASSWORD},  # noqa: E501
        )
        assert User.objects.filter(email="upper@example.com").exists()

    def test_duplicate_email_returns_error(self) -> None:
        UserFactory.create(email="existing@example.com")
        client = APIClient()
        response = client.post(
            reverse("auth-register"),
            {"email": "existing@example.com", "password": _TEST_PASSWORD},
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.data["success"] is False
        assert len(mail.outbox) == 0

    def test_missing_password_returns_error(self) -> None:
        client = APIClient()
        response = client.post(
            reverse("auth-register"),
            {"email": "no-pass@example.com"},
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.data["success"] is False


class TestLogin:
    @pytest.mark.django_db(transaction=True)
    def test_valid_credentials_sends_email_token(self) -> None:
        user = UserFactory.create(password=_TEST_PASSWORD, is_active=True)
        client = APIClient()
        response = client.post(
            reverse("auth-login"),
            {"email": user.email, "password": _TEST_PASSWORD},
        )
        assert response.status_code == HTTPStatus.OK
        assert response.data["success"] is True
        assert len(mail.outbox) == 1
        assert EmailToken.objects.filter(user=user, is_used=False).exists()

    def test_bad_password_returns_same_response_without_email(self) -> None:
        user = UserFactory.create(password=_TEST_PASSWORD, is_active=True)
        client = APIClient()
        response = client.post(
            reverse("auth-login"),
            {"email": user.email, "password": "WrongPassword!"},
        )
        assert response.status_code == HTTPStatus.OK
        assert len(mail.outbox) == 0

    def test_inactive_user_does_not_receive_email(self) -> None:
        user = UserFactory.create(password=_TEST_PASSWORD, is_active=False)
        client = APIClient()
        client.post(
            reverse("auth-login"),
            {"email": user.email, "password": _TEST_PASSWORD},
        )
        assert len(mail.outbox) == 0


class TestVerifyEmailToken:
    def test_valid_token_activates_user_and_returns_jwt(self) -> None:
        user = UserFactory.create(is_active=False)
        email_token = EmailTokenFactory.create(user=user)
        client = APIClient()
        response = client.post(
            reverse("auth-verify"),
            {"email": user.email, "token": email_token.token},
        )
        assert response.status_code == HTTPStatus.OK
        assert "access_token" in response.data["data"]
        assert "refresh_token" in response.data["data"]
        user.refresh_from_db()
        assert user.is_active
        email_token.refresh_from_db()
        assert email_token.is_used

    def test_expired_token_returns_error(self) -> None:
        user = UserFactory.create(is_active=False)
        EmailTokenFactory.create(
            user=user, expires_at=timezone.now() - timedelta(minutes=1),
        )
        client = APIClient()
        response = client.post(
            reverse("auth-verify"),
            {"email": user.email, "token": "ANYVAL"},
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.data["success"] is False

    def test_wrong_token_returns_error(self) -> None:
        user = UserFactory.create(is_active=False)
        EmailTokenFactory.create(user=user, token="ABC123")  # noqa: S106
        client = APIClient()
        response = client.post(
            reverse("auth-verify"),
            {"email": user.email, "token": "XXXXXX"},
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_already_used_token_returns_error(self) -> None:
        user = UserFactory.create(is_active=False)
        token = EmailTokenFactory.create(user=user, is_used=True)
        client = APIClient()
        response = client.post(
            reverse("auth-verify"),
            {"email": user.email, "token": token.token},
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_unknown_email_returns_error(self) -> None:
        client = APIClient()
        response = client.post(
            reverse("auth-verify"),
            {"email": "ghost@example.com", "token": "ABC123"},
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST


class TestLogout:
    def test_valid_refresh_token_is_blacklisted(self) -> None:
        user = UserFactory.create(is_active=True)
        refresh = RefreshToken.for_user(user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        response = client.post(reverse("auth-logout"), {"refresh_token": str(refresh)})
        assert response.status_code == HTTPStatus.OK
        assert response.data["success"] is True

    def test_missing_refresh_token_returns_error(self) -> None:
        user = UserFactory.create(is_active=True)
        refresh = RefreshToken.for_user(user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        response = client.post(reverse("auth-logout"), {})
        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_unauthenticated_returns_401(self) -> None:
        client = APIClient()
        response = client.post(reverse("auth-logout"), {"refresh_token": "anything"})
        assert response.status_code == HTTPStatus.UNAUTHORIZED
