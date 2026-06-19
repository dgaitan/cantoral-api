from __future__ import annotations

from http import HTTPStatus

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from cc.songs.models import Tag
from cc.songs.tests.api.base import AuthenticatedApiTest
from cc.songs.tests.factories import SongFactory, TagFactory

pytestmark = pytest.mark.django_db


class TestTagsCrud(AuthenticatedApiTest):
    # ── List ──────────────────────────────────────────────────────────────────

    def test_list_all_tags_returns_200_with_all_tags(self) -> None:
        tag_count = 3
        TagFactory.create_batch(tag_count)
        response = APIClient().get(reverse("tag-list"))
        assert response.status_code == HTTPStatus.OK
        assert response.data["success"] is True
        data = response.data["data"]
        assert data["count"] == tag_count
        results = data["results"]
        assert len(results) == tag_count
        for field in ("id", "name", "slug", "parent_id"):
            assert field in results[0]

    def test_list_tags_is_publicly_accessible(self) -> None:
        response = APIClient().get(reverse("tag-list"))
        assert response.status_code == HTTPStatus.OK

    def test_list_tags_does_not_include_children_field(self) -> None:
        parent = TagFactory.create()
        TagFactory.create_batch(2, parent=parent)
        response = APIClient().get(reverse("tag-list"))
        assert response.status_code == HTTPStatus.OK
        for tag in response.data["data"]["results"]:
            assert "children" not in tag

    # ── Retrieve ──────────────────────────────────────────────────────────────

    def test_retrieve_existing_tag_returns_200(self) -> None:
        tag = TagFactory.create()
        response = APIClient().get(reverse("tag-detail", kwargs={"pk": tag.pk}))
        assert response.status_code == HTTPStatus.OK
        assert response.data["success"] is True
        data = response.data["data"]
        assert data["id"] == tag.pk
        for field in ("name", "slug", "parent_id"):
            assert field in data

    def test_retrieve_tag_does_not_include_children(self) -> None:
        parent = TagFactory.create()
        TagFactory.create_batch(2, parent=parent)
        response = APIClient().get(reverse("tag-detail", kwargs={"pk": parent.pk}))
        assert response.status_code == HTTPStatus.OK
        assert "children" not in response.data["data"]

    def test_retrieve_non_existent_tag_returns_404(self) -> None:
        response = APIClient().get(reverse("tag-detail", kwargs={"pk": 99999}))
        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_retrieve_tag_is_publicly_accessible(self) -> None:
        tag = TagFactory.create()
        response = APIClient().get(reverse("tag-detail", kwargs={"pk": tag.pk}))
        assert response.status_code == HTTPStatus.OK

    # ── Create ────────────────────────────────────────────────────────────────

    def test_create_tag_with_all_fields_returns_201(self) -> None:
        client = self._auth_client()
        response = client.post(
            reverse("tag-list"),
            {"name": "Liturgia", "slug": "liturgia"},
            format="json",
        )
        assert response.status_code == HTTPStatus.CREATED
        assert response.data["success"] is True
        assert Tag.objects.filter(name="Liturgia", slug="liturgia").exists()

    def test_create_tag_auto_generates_slug_from_name(self) -> None:
        client = self._auth_client()
        response = client.post(
            reverse("tag-list"),
            {"name": "Adviento y Navidad"},
            format="json",
        )
        assert response.status_code == HTTPStatus.CREATED
        assert response.data["data"]["slug"] == "adviento-y-navidad"

    def test_create_tag_with_parent_id_returns_201(self) -> None:
        client = self._auth_client()
        parent = TagFactory.create()
        response = client.post(
            reverse("tag-list"),
            {"name": "Tiempo Ordinario", "parent_id": parent.pk},
            format="json",
        )
        assert response.status_code == HTTPStatus.CREATED
        assert response.data["data"]["parent_id"] == parent.pk

    def test_create_tag_without_parent_id_creates_root_tag(self) -> None:
        client = self._auth_client()
        response = client.post(
            reverse("tag-list"),
            {"name": "Adviento"},
            format="json",
        )
        assert response.status_code == HTTPStatus.CREATED
        assert response.data["data"]["parent_id"] is None

    def test_create_tag_with_duplicate_slug_returns_400(self) -> None:
        TagFactory.create(slug="liturgia")
        client = self._auth_client()
        response = client.post(
            reverse("tag-list"),
            {"name": "Liturgia", "slug": "liturgia"},
            format="json",
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_create_tag_with_non_existent_parent_id_returns_400(self) -> None:
        client = self._auth_client()
        response = client.post(
            reverse("tag-list"),
            {"name": "Subtag", "parent_id": 99999},
            format="json",
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_create_tag_without_name_returns_400(self) -> None:
        client = self._auth_client()
        response = client.post(reverse("tag-list"), {}, format="json")
        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_create_tag_without_permission_returns_403(self) -> None:
        client = self._auth_client(can_create_songs=False)
        response = client.post(
            reverse("tag-list"),
            {"name": "Test"},
            format="json",
        )
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_create_tag_unauthenticated_returns_401(self) -> None:
        response = APIClient().post(
            reverse("tag-list"),
            {"name": "Test"},
            format="json",
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    # ── Tag songs ──────────────────────────────────────────────────────────────

    def test_retrieve_tag_songs_returns_associated_songs(self) -> None:
        tag = TagFactory.create()
        song_count = 2
        songs = SongFactory.create_batch(song_count)
        for song in songs:
            song.tags.add(tag)
        response = APIClient().get(reverse("tag-songs", kwargs={"pk": tag.pk}))
        assert response.status_code == HTTPStatus.OK
        data = response.data["data"]
        results = data["results"]
        assert len(results) == song_count
        assert all("id" in s and "name" in s for s in results)

    def test_retrieve_tag_songs_empty_list_when_no_songs(self) -> None:
        tag = TagFactory.create()
        response = APIClient().get(reverse("tag-songs", kwargs={"pk": tag.pk}))
        assert response.status_code == HTTPStatus.OK
        assert response.data["data"]["results"] == []

    def test_retrieve_songs_for_non_existent_tag_returns_404(self) -> None:
        response = APIClient().get(reverse("tag-songs", kwargs={"pk": 99999}))
        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_retrieve_tag_songs_is_publicly_accessible(self) -> None:
        tag = TagFactory.create()
        song = SongFactory.create()
        song.tags.add(tag)
        response = APIClient().get(reverse("tag-songs", kwargs={"pk": tag.pk}))
        assert response.status_code == HTTPStatus.OK

    # ── Tag children ──────────────────────────────────────────────────────────

    def test_retrieve_tag_children_returns_direct_children_only(self) -> None:
        parent = TagFactory.create()
        child_count = 2
        children = TagFactory.create_batch(child_count, parent=parent)
        grandchild = TagFactory.create(parent=children[0])
        response = APIClient().get(reverse("tag-children", kwargs={"pk": parent.pk}))
        assert response.status_code == HTTPStatus.OK
        data = response.data["data"]
        assert len(data) == child_count
        child_ids = {c["id"] for c in data}
        assert grandchild.pk not in child_ids
        for child in data:
            for field in ("id", "name", "slug", "parent_id"):
                assert field in child

    def test_retrieve_tag_children_empty_list_when_no_children(self) -> None:
        tag = TagFactory.create()
        response = APIClient().get(reverse("tag-children", kwargs={"pk": tag.pk}))
        assert response.status_code == HTTPStatus.OK
        assert response.data["data"] == []

    def test_retrieve_children_for_non_existent_tag_returns_404(self) -> None:
        response = APIClient().get(reverse("tag-children", kwargs={"pk": 99999}))
        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_retrieve_tag_children_is_publicly_accessible(self) -> None:
        parent = TagFactory.create()
        TagFactory.create(parent=parent)
        response = APIClient().get(reverse("tag-children", kwargs={"pk": parent.pk}))
        assert response.status_code == HTTPStatus.OK

    # ── Full update ───────────────────────────────────────────────────────────

    def test_full_update_tag_returns_200(self) -> None:
        tag = TagFactory.create(name="Old Name", slug="old-name")
        client = self._auth_client()
        response = client.put(
            reverse("tag-detail", kwargs={"pk": tag.pk}),
            {"name": "New Name", "slug": "new-name"},
            format="json",
        )
        assert response.status_code == HTTPStatus.OK
        tag.refresh_from_db()
        assert tag.name == "New Name"
        assert tag.slug == "new-name"

    def test_full_update_regenerates_slug_when_slug_omitted(self) -> None:
        tag = TagFactory.create()
        client = self._auth_client()
        response = client.put(
            reverse("tag-detail", kwargs={"pk": tag.pk}),
            {"name": "Semana Santa"},
            format="json",
        )
        assert response.status_code == HTTPStatus.OK
        tag.refresh_from_db()
        assert tag.slug == "semana-santa"

    def test_full_update_can_assign_a_parent(self) -> None:
        tag = TagFactory.create()
        parent = TagFactory.create()
        client = self._auth_client()
        response = client.put(
            reverse("tag-detail", kwargs={"pk": tag.pk}),
            {"name": tag.name, "parent_id": parent.pk},
            format="json",
        )
        assert response.status_code == HTTPStatus.OK
        tag.refresh_from_db()
        assert tag.parent_id == parent.pk

    def test_full_update_with_duplicate_slug_returns_400(self) -> None:
        TagFactory.create(slug="existing-slug")
        tag = TagFactory.create()
        client = self._auth_client()
        response = client.put(
            reverse("tag-detail", kwargs={"pk": tag.pk}),
            {"name": "Something", "slug": "existing-slug"},
            format="json",
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_full_update_non_existent_tag_returns_404(self) -> None:
        client = self._auth_client()
        response = client.put(
            reverse("tag-detail", kwargs={"pk": 99999}),
            {"name": "Someone"},
            format="json",
        )
        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_full_update_without_permission_returns_403(self) -> None:
        tag = TagFactory.create()
        client = self._auth_client(can_create_songs=False)
        response = client.put(
            reverse("tag-detail", kwargs={"pk": tag.pk}),
            {"name": "Updated"},
            format="json",
        )
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_full_update_unauthenticated_returns_401(self) -> None:
        tag = TagFactory.create()
        response = APIClient().put(
            reverse("tag-detail", kwargs={"pk": tag.pk}),
            {"name": "Updated"},
            format="json",
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    # ── Partial update ────────────────────────────────────────────────────────

    def test_partial_update_name_only_returns_200(self) -> None:
        tag = TagFactory.create(name="Old Name", slug="old-name")
        original_slug = tag.slug
        client = self._auth_client()
        response = client.patch(
            reverse("tag-detail", kwargs={"pk": tag.pk}),
            {"name": "New Name"},
            format="json",
        )
        assert response.status_code == HTTPStatus.OK
        tag.refresh_from_db()
        assert tag.name == "New Name"
        assert tag.slug == original_slug

    def test_partial_update_without_permission_returns_403(self) -> None:
        tag = TagFactory.create()
        client = self._auth_client(can_create_songs=False)
        response = client.patch(
            reverse("tag-detail", kwargs={"pk": tag.pk}),
            {"name": "New Name"},
            format="json",
        )
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_partial_update_unauthenticated_returns_401(self) -> None:
        tag = TagFactory.create()
        response = APIClient().patch(
            reverse("tag-detail", kwargs={"pk": tag.pk}),
            {"name": "New Name"},
            format="json",
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    # ── Delete ────────────────────────────────────────────────────────────────

    def test_delete_tag_returns_204(self) -> None:
        tag = TagFactory.create()
        pk = tag.pk
        client = self._auth_client()
        response = client.delete(reverse("tag-detail", kwargs={"pk": pk}))
        assert response.status_code == HTTPStatus.NO_CONTENT
        assert not Tag.objects.filter(pk=pk).exists()

    def test_delete_non_existent_tag_returns_404(self) -> None:
        client = self._auth_client()
        response = client.delete(reverse("tag-detail", kwargs={"pk": 99999}))
        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_delete_without_permission_returns_403(self) -> None:
        tag = TagFactory.create()
        client = self._auth_client(can_create_songs=False)
        response = client.delete(reverse("tag-detail", kwargs={"pk": tag.pk}))
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_delete_unauthenticated_returns_401(self) -> None:
        tag = TagFactory.create()
        response = APIClient().delete(reverse("tag-detail", kwargs={"pk": tag.pk}))
        assert response.status_code == HTTPStatus.UNAUTHORIZED
