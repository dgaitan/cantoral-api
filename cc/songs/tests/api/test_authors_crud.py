from __future__ import annotations

from http import HTTPStatus

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from cc.songs.models import Author
from cc.songs.tests.api.base import AuthenticatedApiTest
from cc.songs.tests.factories import AuthorFactory, SongFactory

pytestmark = pytest.mark.django_db


class TestAuthorsCrud(AuthenticatedApiTest):
    # ── List ──────────────────────────────────────────────────────────────────

    def test_list_all_authors_returns_200_with_all_authors(self) -> None:
        AuthorFactory.create_batch(3)
        client = APIClient()
        response = client.get(reverse("author-list"))
        assert response.status_code == HTTPStatus.OK
        assert response.data["success"] is True
        data = response.data["data"]
        assert data["count"] == 3
        results = data["results"]
        assert len(results) == 3
        for field in ("id", "name", "image", "bio", "slug"):
            assert field in results[0]

    def test_list_authors_is_publicly_accessible(self) -> None:
        response = APIClient().get(reverse("author-list"))
        assert response.status_code == HTTPStatus.OK

    # ── Retrieve ──────────────────────────────────────────────────────────────

    def test_retrieve_existing_author_returns_200(self) -> None:
        author = AuthorFactory.create()
        response = APIClient().get(reverse("author-detail", kwargs={"pk": author.pk}))
        assert response.status_code == HTTPStatus.OK
        assert response.data["success"] is True
        data = response.data["data"]
        assert data["id"] == author.pk
        for field in ("name", "image", "bio", "slug"):
            assert field in data

    def test_retrieve_non_existent_author_returns_404(self) -> None:
        response = APIClient().get(reverse("author-detail", kwargs={"pk": 99999}))
        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_retrieve_author_is_publicly_accessible(self) -> None:
        author = AuthorFactory.create()
        response = APIClient().get(reverse("author-detail", kwargs={"pk": author.pk}))
        assert response.status_code == HTTPStatus.OK

    # ── Create ────────────────────────────────────────────────────────────────

    def test_create_author_with_all_fields_returns_201(self) -> None:
        client = self._auth_client()
        response = client.post(
            reverse("author-list"),
            {
                "name": "Sor Suzanne",
                "image": "https://example.com/img.jpg",
                "bio": "Compositora.",
                "slug": "sor-suzanne",
            },
            format="json",
        )
        assert response.status_code == HTTPStatus.CREATED
        assert response.data["success"] is True
        assert Author.objects.filter(name="Sor Suzanne", slug="sor-suzanne").exists()

    def test_create_author_auto_generates_slug_from_name(self) -> None:
        client = self._auth_client()
        response = client.post(
            reverse("author-list"),
            {"name": "María de Jesús"},
            format="json",
        )
        assert response.status_code == HTTPStatus.CREATED
        assert response.data["data"]["slug"] == "maria-de-jesus"

    def test_create_author_with_only_name_returns_201(self) -> None:
        client = self._auth_client()
        response = client.post(
            reverse("author-list"),
            {"name": "Anonymous"},
            format="json",
        )
        assert response.status_code == HTTPStatus.CREATED
        data = response.data["data"]
        assert data["image"] == ""
        assert data["bio"] == ""

    def test_create_author_without_name_returns_400(self) -> None:
        client = self._auth_client()
        response = client.post(reverse("author-list"), {}, format="json")
        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_create_author_without_permission_returns_403(self) -> None:
        client = self._auth_client(can_create_songs=False)
        response = client.post(
            reverse("author-list"),
            {"name": "Test"},
            format="json",
        )
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_create_author_unauthenticated_returns_401(self) -> None:
        response = APIClient().post(
            reverse("author-list"),
            {"name": "Test"},
            format="json",
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    # ── Author songs ──────────────────────────────────────────────────────────

    def test_retrieve_author_songs_returns_associated_songs(self) -> None:
        author = AuthorFactory.create()
        songs = SongFactory.create_batch(2)
        for song in songs:
            song.authors.add(author)
        response = APIClient().get(reverse("author-songs", kwargs={"pk": author.pk}))
        assert response.status_code == HTTPStatus.OK
        data = response.data["data"]
        results = data["results"]
        assert len(results) == 2
        assert all("id" in s and "name" in s for s in results)

    def test_retrieve_author_songs_empty_list_when_no_songs(self) -> None:
        author = AuthorFactory.create()
        response = APIClient().get(reverse("author-songs", kwargs={"pk": author.pk}))
        assert response.status_code == HTTPStatus.OK
        assert response.data["data"]["results"] == []

    def test_retrieve_songs_for_non_existent_author_returns_404(self) -> None:
        response = APIClient().get(reverse("author-songs", kwargs={"pk": 99999}))
        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_retrieve_author_songs_is_publicly_accessible(self) -> None:
        author = AuthorFactory.create()
        song = SongFactory.create()
        song.authors.add(author)
        response = APIClient().get(reverse("author-songs", kwargs={"pk": author.pk}))
        assert response.status_code == HTTPStatus.OK

    # ── Full update ───────────────────────────────────────────────────────────

    def test_full_update_author_returns_200(self) -> None:
        author = AuthorFactory.create(name="Old Name")
        client = self._auth_client()
        response = client.put(
            reverse("author-detail", kwargs={"pk": author.pk}),
            {"name": "New Name", "bio": "Updated bio", "image": "", "slug": "new-name"},
            format="json",
        )
        assert response.status_code == HTTPStatus.OK
        author.refresh_from_db()
        assert author.name == "New Name"
        assert author.slug == "new-name"

    def test_full_update_regenerates_slug_when_slug_omitted(self) -> None:
        author = AuthorFactory.create()
        client = self._auth_client()
        response = client.put(
            reverse("author-detail", kwargs={"pk": author.pk}),
            {"name": "Juan Nicolás"},
            format="json",
        )
        assert response.status_code == HTTPStatus.OK
        author.refresh_from_db()
        assert author.slug == "juan-nicolas"

    def test_full_update_non_existent_author_returns_404(self) -> None:
        client = self._auth_client()
        response = client.put(
            reverse("author-detail", kwargs={"pk": 99999}),
            {"name": "Someone"},
            format="json",
        )
        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_full_update_without_permission_returns_403(self) -> None:
        author = AuthorFactory.create()
        client = self._auth_client(can_create_songs=False)
        response = client.put(
            reverse("author-detail", kwargs={"pk": author.pk}),
            {"name": "Updated"},
            format="json",
        )
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_full_update_unauthenticated_returns_401(self) -> None:
        author = AuthorFactory.create()
        response = APIClient().put(
            reverse("author-detail", kwargs={"pk": author.pk}),
            {"name": "Updated"},
            format="json",
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    # ── Partial update ────────────────────────────────────────────────────────

    def test_partial_update_bio_only_returns_200(self) -> None:
        author = AuthorFactory.create(name="Original", bio="Old bio")
        original_slug = author.slug
        client = self._auth_client()
        response = client.patch(
            reverse("author-detail", kwargs={"pk": author.pk}),
            {"bio": "New bio"},
            format="json",
        )
        assert response.status_code == HTTPStatus.OK
        author.refresh_from_db()
        assert author.bio == "New bio"
        assert author.name == "Original"
        assert author.slug == original_slug

    def test_partial_update_without_permission_returns_403(self) -> None:
        author = AuthorFactory.create()
        client = self._auth_client(can_create_songs=False)
        response = client.patch(
            reverse("author-detail", kwargs={"pk": author.pk}),
            {"bio": "New bio"},
            format="json",
        )
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_partial_update_unauthenticated_returns_401(self) -> None:
        author = AuthorFactory.create()
        response = APIClient().patch(
            reverse("author-detail", kwargs={"pk": author.pk}),
            {"bio": "New bio"},
            format="json",
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    # ── Delete ────────────────────────────────────────────────────────────────

    def test_delete_author_returns_204(self) -> None:
        author = AuthorFactory.create()
        pk = author.pk
        client = self._auth_client()
        response = client.delete(reverse("author-detail", kwargs={"pk": pk}))
        assert response.status_code == HTTPStatus.NO_CONTENT
        assert not Author.objects.filter(pk=pk).exists()

    def test_delete_non_existent_author_returns_404(self) -> None:
        client = self._auth_client()
        response = client.delete(reverse("author-detail", kwargs={"pk": 99999}))
        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_delete_without_permission_returns_403(self) -> None:
        author = AuthorFactory.create()
        client = self._auth_client(can_create_songs=False)
        response = client.delete(reverse("author-detail", kwargs={"pk": author.pk}))
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_delete_unauthenticated_returns_401(self) -> None:
        author = AuthorFactory.create()
        response = APIClient().delete(
            reverse("author-detail", kwargs={"pk": author.pk}),
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED
