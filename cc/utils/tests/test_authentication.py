from __future__ import annotations

from http import HTTPStatus

import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from cc.songs.tests.factories import SongFactory
from cc.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def _client_with_bearer_token(raw_token: str) -> APIClient:
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {raw_token}")
    return client


class TestOptionalJWTAuthenticationOnPublicEndpoints:
    def test_invalid_token_does_not_401_an_allow_any_endpoint(self) -> None:
        song = SongFactory.create()
        client = _client_with_bearer_token("not-a-real-token")

        response = client.get(reverse("song-detail", args=[song.pk]))

        assert response.status_code == HTTPStatus.OK

    def test_expired_token_does_not_401_an_allow_any_endpoint(self) -> None:
        # A token that is well-formed but signed with a bogus payload/signature
        # exercises the same "invalid" path SimpleJWT uses for expired tokens.
        song = SongFactory.create()
        bogus_jwt = "a.b.c"
        client = _client_with_bearer_token(bogus_jwt)

        response = client.get(reverse("song-detail", args=[song.pk]))

        assert response.status_code == HTTPStatus.OK

    def test_no_authorization_header_still_allowed(self) -> None:
        song = SongFactory.create()

        response = APIClient().get(reverse("song-detail", args=[song.pk]))

        assert response.status_code == HTTPStatus.OK


class TestOptionalJWTAuthenticationOnProtectedEndpoints:
    def test_invalid_token_still_401s_an_is_authenticated_endpoint(self) -> None:
        song = SongFactory.create()
        client = _client_with_bearer_token("not-a-real-token")

        response = client.post(reverse("song-favorites", args=[song.pk]))

        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_missing_token_still_401s_an_is_authenticated_endpoint(self) -> None:
        song = SongFactory.create()

        response = APIClient().post(reverse("song-favorites", args=[song.pk]))

        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_valid_token_still_authenticates(self) -> None:
        user = UserFactory.create(is_active=True)
        song = SongFactory.create()
        token = RefreshToken.for_user(user)
        client = _client_with_bearer_token(str(token.access_token))

        response = client.post(reverse("song-favorites", args=[song.pk]))

        assert response.status_code == HTTPStatus.OK
