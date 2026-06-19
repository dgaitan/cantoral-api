from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from django.urls import reverse
from rest_framework.test import APIClient, APIRequestFactory

from cc.users.api.views import UserViewSet
from cc.users.tests.factories import UserFactory

if TYPE_CHECKING:
    from cc.users.models import User

pytestmark = pytest.mark.django_db

_TEST_PASSWORD = "StrongTestPass1!"  # noqa: S105 — test credential, not real secret


class TestUserViewSet:
    @pytest.fixture
    def api_rf(self) -> APIRequestFactory:
        return APIRequestFactory()

    def test_get_queryset(self, user: User, api_rf: APIRequestFactory) -> None:
        view = UserViewSet()
        request = api_rf.get("/fake-url/")
        request.user = user
        view.request = request

        assert user in view.get_queryset()

    def test_me(self, user: User, api_rf: APIRequestFactory) -> None:
        view = UserViewSet()
        request = api_rf.get("/fake-url/")
        request.user = user
        view.request = request

        response = view.me(request)  # type: ignore[misc,call-arg,arg-type]

        assert response.data == {
            "id": user.pk,
            "email": user.email,
            "name": user.name,
        }


class TestJWTAuth:
    def test_obtain_token(self) -> None:
        user = UserFactory.create(password=_TEST_PASSWORD)
        client = APIClient()
        response = client.post(
            reverse("token_obtain_pair"),
            {"email": user.email, "password": _TEST_PASSWORD},
        )
        assert response.status_code == HTTPStatus.OK
        assert "access" in response.data
        assert "refresh" in response.data

    def test_refresh_token(self) -> None:
        user = UserFactory.create(password=_TEST_PASSWORD)
        client = APIClient()

        token_response = client.post(
            reverse("token_obtain_pair"),
            {"email": user.email, "password": _TEST_PASSWORD},
        )
        response = client.post(
            reverse("token_refresh"),
            {"refresh": token_response.data["refresh"]},
        )
        assert response.status_code == HTTPStatus.OK
        assert "access" in response.data

    def test_protected_endpoint_without_token(self) -> None:
        client = APIClient()
        response = client.get(reverse("api:user-me"))
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_protected_endpoint_with_valid_token(self) -> None:
        user = UserFactory.create(password=_TEST_PASSWORD)
        client = APIClient()

        token_response = client.post(
            reverse("token_obtain_pair"),
            {"email": user.email, "password": _TEST_PASSWORD},
        )
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token_response.data['access']}")

        response = client.get(reverse("api:user-me"))
        assert response.status_code == HTTPStatus.OK
        assert response.data["email"] == user.email
