from __future__ import annotations

from http import HTTPStatus

import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from cc.songs.models import Song
from cc.songs.tests.factories import AuthorFactory, SongFactory, TagFactory
from cc.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db

_LYRICS_G = """\
---
tone: G
---
[verse]
     {G}                   {D}
Porque eres la razón de mi vida
 {C}      {D}        {G}
Mi fuerza consuelo y alegría
"""

_LYRICS_A = """\
---
tone: A
---
[verse]
     {A}                   {E}
Porque eres la razón de mi vida
 {D}      {E}        {A}
Mi fuerza consuelo y alegría
"""


def _auth_client(user: object) -> APIClient:
    client = APIClient()
    token = RefreshToken.for_user(user)  # type: ignore[arg-type]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return client


# ── List ──────────────────────────────────────────────────────────────────────


class TestSongList:
    def test_returns_200_with_paginated_results(self) -> None:
        song_count = 3
        SongFactory.create_batch(song_count)
        response = APIClient().get(reverse("song-list"))
        assert response.status_code == HTTPStatus.OK
        assert response.data["success"] is True
        assert response.data["data"]["count"] == song_count

    def test_publicly_accessible(self) -> None:
        SongFactory.create()
        response = APIClient().get(reverse("song-list"))
        assert response.status_code == HTTPStatus.OK

    def test_ordered_by_created_at_descending(self) -> None:
        s1 = SongFactory.create(name="First")
        s2 = SongFactory.create(name="Second")
        s3 = SongFactory.create(name="Third")
        response = APIClient().get(reverse("song-list"))
        ids = [r["id"] for r in response.data["data"]["results"]]
        assert ids == [s3.pk, s2.pk, s1.pk]


# ── Retrieve ──────────────────────────────────────────────────────────────────


class TestSongRetrieve:
    def test_returns_200_with_full_payload(self) -> None:
        tag = TagFactory.create()
        author = AuthorFactory.create()
        song = SongFactory.create()
        song.tags.add(tag)
        song.authors.add(author)
        response = APIClient().get(reverse("song-detail", kwargs={"pk": song.pk}))
        assert response.status_code == HTTPStatus.OK
        data = response.data["data"]
        for field in (
            "id",
            "name",
            "views",
            "tags",
            "authors",
            "plain_lyrics",
            "tone",
            "is_public",
            "lyrics",
        ):
            assert field in data
        assert data["tags"][0]["id"] == tag.pk
        assert data["authors"][0]["id"] == author.pk
        assert "lyric" in data["lyrics"]
        assert "chords" in data["lyrics"]

    def test_404_on_missing(self) -> None:
        response = APIClient().get(reverse("song-detail", kwargs={"pk": 99999}))
        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_publicly_accessible(self) -> None:
        song = SongFactory.create()
        response = APIClient().get(reverse("song-detail", kwargs={"pk": song.pk}))
        assert response.status_code == HTTPStatus.OK


# ── Create ────────────────────────────────────────────────────────────────────


class TestSongCreate:
    def test_creates_with_required_fields(self) -> None:
        user = UserFactory.create(can_create_songs=True)
        author = AuthorFactory.create()
        response = _auth_client(user).post(
            reverse("song-list"),
            {"name": "Aquí Estoy Señor", "authors": [author.pk], "lyrics": _LYRICS_G},
            format="json",
        )
        assert response.status_code == HTTPStatus.CREATED
        song = Song.objects.get(pk=response.data["data"]["id"])
        assert song.name == "Aquí Estoy Señor"
        assert song.tone == "G"
        assert song.is_public is False
        assert song.created_by == user

    def test_assigns_tags(self) -> None:
        user = UserFactory.create(can_create_songs=True)
        author = AuthorFactory.create()
        tag = TagFactory.create()
        response = _auth_client(user).post(
            reverse("song-list"),
            {
                "name": "Song",
                "authors": [author.pk],
                "tags": [tag.pk],
                "lyrics": _LYRICS_G,
            },
            format="json",
        )
        assert response.status_code == HTTPStatus.CREATED
        assert (
            Song.objects.get(pk=response.data["data"]["id"])
            .tags.filter(pk=tag.pk)
            .exists()
        )

    def test_no_tags_defaults_to_empty(self) -> None:
        user = UserFactory.create(can_create_songs=True)
        author = AuthorFactory.create()
        response = _auth_client(user).post(
            reverse("song-list"),
            {"name": "Song", "authors": [author.pk], "lyrics": _LYRICS_G},
            format="json",
        )
        assert response.status_code == HTTPStatus.CREATED
        assert Song.objects.get(pk=response.data["data"]["id"]).tags.count() == 0

    def test_assigns_multiple_authors(self) -> None:
        user = UserFactory.create(can_create_songs=True)
        a1 = AuthorFactory.create()
        a2 = AuthorFactory.create()
        response = _auth_client(user).post(
            reverse("song-list"),
            {"name": "Duet", "authors": [a1.pk, a2.pk], "lyrics": _LYRICS_G},
            format="json",
        )
        assert response.status_code == HTTPStatus.CREATED
        song = Song.objects.get(pk=response.data["data"]["id"])
        assert song.authors.filter(pk=a1.pk).exists()
        assert song.authors.filter(pk=a2.pk).exists()

    def test_missing_name_returns_400(self) -> None:
        user = UserFactory.create(can_create_songs=True)
        author = AuthorFactory.create()
        response = _auth_client(user).post(
            reverse("song-list"),
            {"authors": [author.pk], "lyrics": _LYRICS_G},
            format="json",
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_missing_authors_returns_400(self) -> None:
        user = UserFactory.create(can_create_songs=True)
        response = _auth_client(user).post(
            reverse("song-list"),
            {"name": "Song", "lyrics": _LYRICS_G},
            format="json",
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_empty_authors_list_returns_400(self) -> None:
        user = UserFactory.create(can_create_songs=True)
        response = _auth_client(user).post(
            reverse("song-list"),
            {"name": "Song", "authors": [], "lyrics": _LYRICS_G},
            format="json",
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_nonexistent_author_returns_400(self) -> None:
        user = UserFactory.create(can_create_songs=True)
        response = _auth_client(user).post(
            reverse("song-list"),
            {"name": "Song", "authors": [99999], "lyrics": _LYRICS_G},
            format="json",
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_nonexistent_tag_returns_400(self) -> None:
        user = UserFactory.create(can_create_songs=True)
        author = AuthorFactory.create()
        response = _auth_client(user).post(
            reverse("song-list"),
            {
                "name": "Song",
                "authors": [author.pk],
                "tags": [99999],
                "lyrics": _LYRICS_G,
            },
            format="json",
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_invalid_lyrics_returns_400(self) -> None:
        user = UserFactory.create(can_create_songs=True)
        author = AuthorFactory.create()
        response = _auth_client(user).post(
            reverse("song-list"),
            {"name": "Song", "authors": [author.pk], "lyrics": "no frontmatter"},
            format="json",
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_no_permission_returns_403(self) -> None:
        user = UserFactory.create(can_create_songs=False)
        response = _auth_client(user).post(reverse("song-list"), {}, format="json")
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_unauthenticated_returns_401(self) -> None:
        response = APIClient().post(reverse("song-list"), {}, format="json")
        assert response.status_code == HTTPStatus.UNAUTHORIZED


# ── Update (full) ─────────────────────────────────────────────────────────────


class TestSongUpdate:
    def test_returns_200_with_updated_data(self) -> None:
        user = UserFactory.create(can_create_songs=True)
        song = SongFactory.create(name="Old Name")
        author = AuthorFactory.create()
        response = _auth_client(user).put(
            reverse("song-detail", kwargs={"pk": song.pk}),
            {"name": "New Name", "authors": [author.pk], "lyrics": _LYRICS_A},
            format="json",
        )
        assert response.status_code == HTTPStatus.OK
        assert response.data["success"] is True
        song.refresh_from_db()
        assert song.name == "New Name"
        assert song.tone == "A"
        assert song.authors.filter(pk=author.pk).exists()

    def test_replaces_tags(self) -> None:
        user = UserFactory.create(can_create_songs=True)
        tag1 = TagFactory.create()
        tag2 = TagFactory.create()
        author = AuthorFactory.create()
        song = SongFactory.create()
        song.tags.add(tag1)
        _auth_client(user).put(
            reverse("song-detail", kwargs={"pk": song.pk}),
            {
                "name": song.name,
                "authors": [author.pk],
                "tags": [tag2.pk],
                "lyrics": _LYRICS_G,
            },
            format="json",
        )
        song.refresh_from_db()
        assert song.tags.filter(pk=tag2.pk).exists()
        assert not song.tags.filter(pk=tag1.pk).exists()

    def test_empty_tags_clears_all_tags(self) -> None:
        user = UserFactory.create(can_create_songs=True)
        tag = TagFactory.create()
        author = AuthorFactory.create()
        song = SongFactory.create()
        song.tags.add(tag)
        _auth_client(user).put(
            reverse("song-detail", kwargs={"pk": song.pk}),
            {
                "name": song.name,
                "authors": [author.pk],
                "tags": [],
                "lyrics": _LYRICS_G,
            },
            format="json",
        )
        song.refresh_from_db()
        assert song.tags.count() == 0

    def test_does_not_change_created_by(self) -> None:
        original_user = UserFactory.create()
        editor = UserFactory.create(can_create_songs=True)
        song = SongFactory.create(created_by=original_user)
        author = AuthorFactory.create()
        _auth_client(editor).put(
            reverse("song-detail", kwargs={"pk": song.pk}),
            {"name": song.name, "authors": [author.pk], "lyrics": _LYRICS_G},
            format="json",
        )
        song.refresh_from_db()
        assert song.created_by == original_user

    def test_nonexistent_author_returns_400(self) -> None:
        user = UserFactory.create(can_create_songs=True)
        song = SongFactory.create()
        response = _auth_client(user).put(
            reverse("song-detail", kwargs={"pk": song.pk}),
            {"name": song.name, "authors": [99999], "lyrics": _LYRICS_G},
            format="json",
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_nonexistent_tag_returns_400(self) -> None:
        user = UserFactory.create(can_create_songs=True)
        song = SongFactory.create()
        author = AuthorFactory.create()
        response = _auth_client(user).put(
            reverse("song-detail", kwargs={"pk": song.pk}),
            {
                "name": song.name,
                "authors": [author.pk],
                "tags": [99999],
                "lyrics": _LYRICS_G,
            },
            format="json",
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_invalid_lyrics_returns_400(self) -> None:
        user = UserFactory.create(can_create_songs=True)
        song = SongFactory.create()
        author = AuthorFactory.create()
        response = _auth_client(user).put(
            reverse("song-detail", kwargs={"pk": song.pk}),
            {"name": song.name, "authors": [author.pk], "lyrics": "no frontmatter"},
            format="json",
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_nonexistent_song_returns_404(self) -> None:
        user = UserFactory.create(can_create_songs=True)
        author = AuthorFactory.create()
        response = _auth_client(user).put(
            reverse("song-detail", kwargs={"pk": 99999}),
            {"name": "Name", "authors": [author.pk], "lyrics": _LYRICS_G},
            format="json",
        )
        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_no_permission_returns_403(self) -> None:
        user = UserFactory.create(can_create_songs=False)
        song = SongFactory.create()
        response = _auth_client(user).put(
            reverse("song-detail", kwargs={"pk": song.pk}),
            {},
            format="json",
        )
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_unauthenticated_returns_401(self) -> None:
        song = SongFactory.create()
        response = APIClient().put(
            reverse("song-detail", kwargs={"pk": song.pk}),
            {},
            format="json",
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED


# ── Partial update ────────────────────────────────────────────────────────────


class TestSongPartialUpdate:
    def test_name_only_returns_200(self) -> None:
        user = UserFactory.create(can_create_songs=True)
        song = SongFactory.create(name="Old Name", plain_lyrics=_LYRICS_G, tone="G")
        response = _auth_client(user).patch(
            reverse("song-detail", kwargs={"pk": song.pk}),
            {"name": "New Name"},
            format="json",
        )
        assert response.status_code == HTTPStatus.OK
        song.refresh_from_db()
        assert song.name == "New Name"
        assert song.tone == "G"

    def test_authors_replaces_assignment(self) -> None:
        user = UserFactory.create(can_create_songs=True)
        a1 = AuthorFactory.create()
        a2 = AuthorFactory.create()
        song = SongFactory.create()
        song.authors.add(a1)
        _auth_client(user).patch(
            reverse("song-detail", kwargs={"pk": song.pk}),
            {"authors": [a2.pk]},
            format="json",
        )
        song.refresh_from_db()
        assert song.authors.filter(pk=a2.pk).exists()
        assert not song.authors.filter(pk=a1.pk).exists()

    def test_tags_replaces_assignment(self) -> None:
        user = UserFactory.create(can_create_songs=True)
        tag1 = TagFactory.create()
        tag3 = TagFactory.create()
        song = SongFactory.create()
        song.tags.add(tag1)
        _auth_client(user).patch(
            reverse("song-detail", kwargs={"pk": song.pk}),
            {"tags": [tag3.pk]},
            format="json",
        )
        song.refresh_from_db()
        assert song.tags.filter(pk=tag3.pk).exists()
        assert not song.tags.filter(pk=tag1.pk).exists()

    def test_omitting_tags_leaves_them_unchanged(self) -> None:
        user = UserFactory.create(can_create_songs=True)
        tag = TagFactory.create()
        song = SongFactory.create()
        song.tags.add(tag)
        _auth_client(user).patch(
            reverse("song-detail", kwargs={"pk": song.pk}),
            {"name": "New Name"},
            format="json",
        )
        song.refresh_from_db()
        assert song.tags.filter(pk=tag.pk).exists()

    def test_lyrics_rederives_tone(self) -> None:
        user = UserFactory.create(can_create_songs=True)
        song = SongFactory.create(plain_lyrics=_LYRICS_G, tone="G")
        _auth_client(user).patch(
            reverse("song-detail", kwargs={"pk": song.pk}),
            {"lyrics": _LYRICS_A},
            format="json",
        )
        song.refresh_from_db()
        assert song.tone == "A"

    def test_nonexistent_author_returns_400(self) -> None:
        user = UserFactory.create(can_create_songs=True)
        song = SongFactory.create()
        response = _auth_client(user).patch(
            reverse("song-detail", kwargs={"pk": song.pk}),
            {"authors": [99999]},
            format="json",
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_no_permission_returns_403(self) -> None:
        user = UserFactory.create(can_create_songs=False)
        song = SongFactory.create()
        response = _auth_client(user).patch(
            reverse("song-detail", kwargs={"pk": song.pk}),
            {},
            format="json",
        )
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_unauthenticated_returns_401(self) -> None:
        song = SongFactory.create()
        response = APIClient().patch(
            reverse("song-detail", kwargs={"pk": song.pk}),
            {},
            format="json",
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED


# ── Delete ────────────────────────────────────────────────────────────────────


class TestSongDelete:
    def test_returns_204_and_removes_record(self) -> None:
        user = UserFactory.create(can_create_songs=True)
        song = SongFactory.create()
        response = _auth_client(user).delete(
            reverse("song-detail", kwargs={"pk": song.pk}),
        )
        assert response.status_code == HTTPStatus.NO_CONTENT
        assert not Song.objects.filter(pk=song.pk).exists()

    def test_nonexistent_returns_404(self) -> None:
        user = UserFactory.create(can_create_songs=True)
        response = _auth_client(user).delete(
            reverse("song-detail", kwargs={"pk": 99999}),
        )
        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_no_permission_returns_403(self) -> None:
        user = UserFactory.create(can_create_songs=False)
        song = SongFactory.create()
        response = _auth_client(user).delete(
            reverse("song-detail", kwargs={"pk": song.pk}),
        )
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_unauthenticated_returns_401(self) -> None:
        song = SongFactory.create()
        response = APIClient().delete(reverse("song-detail", kwargs={"pk": song.pk}))
        assert response.status_code == HTTPStatus.UNAUTHORIZED
