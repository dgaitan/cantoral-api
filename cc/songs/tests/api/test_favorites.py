from __future__ import annotations

from http import HTTPStatus

import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from cc.songs.models import Favorite
from cc.songs.tests.factories import (
    AuthorFactory,
    SongFactory,
    TagFactory,
)
from cc.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def _auth_client(user: object) -> APIClient:
    client = APIClient()
    token = RefreshToken.for_user(user)  # type: ignore[arg-type]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return client


class TestToggleFavorite:
    def test_add_song_to_favorites_returns_200_with_is_favorite_true(self) -> None:
        user = UserFactory.create(is_active=True)
        song = SongFactory.create()
        client = _auth_client(user)

        response = client.post(reverse("song-favorites", kwargs={"pk": song.pk}))

        assert response.status_code == HTTPStatus.OK
        assert response.data["success"] is True
        assert response.data["data"]["is_favorite"] is True
        assert Favorite.objects.filter(user=user, song=song).exists()

    def test_remove_song_from_favorites_returns_200_with_is_favorite_false(
        self,
    ) -> None:
        user = UserFactory.create(is_active=True)
        song = SongFactory.create()
        Favorite.objects.create(user=user, song=song)
        client = _auth_client(user)

        response = client.post(reverse("song-favorites", kwargs={"pk": song.pk}))

        assert response.status_code == HTTPStatus.OK
        assert response.data["success"] is True
        assert response.data["data"]["is_favorite"] is False
        assert not Favorite.objects.filter(user=user, song=song).exists()

    def test_toggle_on_nonexistent_song_returns_404(self) -> None:
        user = UserFactory.create(is_active=True)
        client = _auth_client(user)

        response = client.post(reverse("song-favorites", kwargs={"pk": 99999}))

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_toggle_without_authentication_returns_401(self) -> None:
        song = SongFactory.create()
        client = APIClient()

        response = client.post(reverse("song-favorites", kwargs={"pk": song.pk}))

        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert not Favorite.objects.filter(song=song).exists()


class TestListFavorites:
    def test_list_returns_200_with_paginated_songs(self) -> None:
        user = UserFactory.create(is_active=True)
        song = SongFactory.create()
        Favorite.objects.create(user=user, song=song)
        client = _auth_client(user)

        response = client.get(reverse("profile-favorites"))

        assert response.status_code == HTTPStatus.OK
        assert response.data["success"] is True
        data = response.data["data"]
        assert data["count"] == 1
        assert len(data["results"]) == 1
        result = data["results"][0]
        assert result["id"] == song.pk
        assert result["name"] == song.name
        assert "is_public" in result
        assert "lyrics" in result

    def test_list_returns_only_my_favorites(self) -> None:
        me = UserFactory.create(is_active=True)
        other = UserFactory.create(is_active=True)
        my_song = SongFactory.create()
        other_song = SongFactory.create()
        Favorite.objects.create(user=me, song=my_song)
        Favorite.objects.create(user=other, song=other_song)
        client = _auth_client(me)

        response = client.get(reverse("profile-favorites"))

        assert response.status_code == HTTPStatus.OK
        data = response.data["data"]
        assert data["count"] == 1
        returned_ids = [result["id"] for result in data["results"]]
        assert returned_ids == [my_song.pk]
        assert other_song.pk not in returned_ids

    def test_list_when_no_favorites_returns_empty_results(self) -> None:
        user = UserFactory.create(is_active=True)
        SongFactory.create()
        client = _auth_client(user)

        response = client.get(reverse("profile-favorites"))

        assert response.status_code == HTTPStatus.OK
        data = response.data["data"]
        assert data["count"] == 0
        assert data["results"] == []

    def test_filter_by_search(self) -> None:
        user = UserFactory.create(is_active=True)
        match = SongFactory.create(name="Pescador de Hombres")
        miss = SongFactory.create(name="Vienen con Alegria")
        Favorite.objects.create(user=user, song=match)
        Favorite.objects.create(user=user, song=miss)
        client = _auth_client(user)

        response = client.get(reverse("profile-favorites"), {"search": "Pescador"})

        assert response.status_code == HTTPStatus.OK
        data = response.data["data"]
        assert data["count"] == 1
        assert data["results"][0]["id"] == match.pk

    def test_filter_by_author_id(self) -> None:
        user = UserFactory.create(is_active=True)
        author = AuthorFactory.create()
        match = SongFactory.create()
        match.authors.set([author])
        miss = SongFactory.create()
        Favorite.objects.create(user=user, song=match)
        Favorite.objects.create(user=user, song=miss)
        client = _auth_client(user)

        response = client.get(reverse("profile-favorites"), {"author_id": author.pk})

        assert response.status_code == HTTPStatus.OK
        data = response.data["data"]
        assert data["count"] == 1
        assert data["results"][0]["id"] == match.pk

    def test_filter_by_tag_id(self) -> None:
        user = UserFactory.create(is_active=True)
        tag = TagFactory.create()
        match = SongFactory.create()
        match.tags.set([tag])
        miss = SongFactory.create()
        Favorite.objects.create(user=user, song=match)
        Favorite.objects.create(user=user, song=miss)
        client = _auth_client(user)

        response = client.get(reverse("profile-favorites"), {"tag_id": tag.pk})

        assert response.status_code == HTTPStatus.OK
        data = response.data["data"]
        assert data["count"] == 1
        assert data["results"][0]["id"] == match.pk

    def test_filter_with_no_match_returns_empty(self) -> None:
        user = UserFactory.create(is_active=True)
        song = SongFactory.create()
        Favorite.objects.create(user=user, song=song)
        client = _auth_client(user)

        response = client.get(
            reverse("profile-favorites"),
            {"search": "xyznonexistent"},
        )

        assert response.status_code == HTTPStatus.OK
        data = response.data["data"]
        assert data["count"] == 0
        assert data["results"] == []

    def test_filter_by_invalid_author_id_returns_400(self) -> None:
        user = UserFactory.create(is_active=True)
        client = _auth_client(user)

        response = client.get(reverse("profile-favorites"), {"author_id": "abc"})

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_filter_by_invalid_tag_id_returns_400(self) -> None:
        user = UserFactory.create(is_active=True)
        client = _auth_client(user)

        response = client.get(reverse("profile-favorites"), {"tag_id": "abc"})

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_list_without_authentication_returns_401(self) -> None:
        client = APIClient()

        response = client.get(reverse("profile-favorites"))

        assert response.status_code == HTTPStatus.UNAUTHORIZED
