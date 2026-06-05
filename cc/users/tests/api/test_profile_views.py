from __future__ import annotations

from http import HTTPStatus

import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from cc.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def _auth_client(user: object) -> APIClient:
    refresh = RefreshToken.for_user(user)  # type: ignore[arg-type]
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


class TestGetProfile:
    def test_returns_all_profile_fields(self) -> None:
        user = UserFactory.create(can_create_songs=True, is_active=True)
        client = _auth_client(user)
        response = client.get(reverse("profile"))
        assert response.status_code == HTTPStatus.OK
        data = response.data["data"]
        assert data["email"] == user.email
        assert data["name"] == user.name
        assert data["can_create_songs"] is True
        assert data["can_publish_songs"] is False
        assert data["can_create_playlists"] is False

    def test_unauthenticated_returns_401(self) -> None:
        client = APIClient()
        response = client.get(reverse("profile"))
        assert response.status_code == HTTPStatus.UNAUTHORIZED


class TestUpdateProfile:
    def test_update_name_succeeds(self) -> None:
        user = UserFactory.create(is_active=True)
        client = _auth_client(user)
        response = client.put(reverse("profile"), {"name": "New Name"})
        assert response.status_code == HTTPStatus.OK
        assert response.data["data"]["name"] == "New Name"
        user.refresh_from_db()
        assert user.name == "New Name"

    def test_email_is_not_updated(self) -> None:
        user = UserFactory.create(email="original@example.com", is_active=True)
        client = _auth_client(user)
        client.put(reverse("profile"), {"email": "changed@example.com"})
        user.refresh_from_db()
        assert user.email == "original@example.com"

    def test_permission_flags_are_not_updated(self) -> None:
        user = UserFactory.create(can_create_songs=False, is_active=True)
        client = _auth_client(user)
        client.put(reverse("profile"), {"can_create_songs": True})
        user.refresh_from_db()
        assert user.can_create_songs is False

    def test_unauthenticated_returns_401(self) -> None:
        client = APIClient()
        response = client.put(reverse("profile"), {"name": "Hacker"})
        assert response.status_code == HTTPStatus.UNAUTHORIZED
