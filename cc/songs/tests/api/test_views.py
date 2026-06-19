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

_PLAIN_LYRICS = """\
---
tone: G
---
[verse]
     {G}                   {D}
Porque eres la razón de mi vida
 {C}      {D}        {G}
Mi fuerza consuelo y alegría

[chorus]
        {G}                {D}
Aquí estoy Señor toma mi vida
"""


class TestGetSong:
    def test_returns_song_payload(self) -> None:
        song = SongFactory.create(is_public=True)
        client = APIClient()
        response = client.get(reverse("song-detail", kwargs={"pk": song.pk}))
        assert response.status_code == HTTPStatus.OK
        assert response.data["success"] is True
        data = response.data["data"]
        assert data["id"] == song.pk
        assert "lyrics" in data
        assert "lyric" in data["lyrics"]
        assert "chords" in data["lyrics"]

    def test_public_access_no_auth(self) -> None:
        song = SongFactory.create()
        client = APIClient()
        response = client.get(reverse("song-detail", kwargs={"pk": song.pk}))
        assert response.status_code == HTTPStatus.OK

    def test_404_on_missing_song(self) -> None:
        client = APIClient()
        response = client.get(reverse("song-detail", kwargs={"pk": 99999}))
        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_response_includes_tags_and_authors(self) -> None:
        tag = TagFactory.create()
        author = AuthorFactory.create()
        song = SongFactory.create()
        song.tags.add(tag)
        song.authors.add(author)
        client = APIClient()
        response = client.get(reverse("song-detail", kwargs={"pk": song.pk}))
        data = response.data["data"]
        assert any(t["id"] == tag.pk for t in data["tags"])
        assert any(a["id"] == author.pk for a in data["authors"])

    def test_lyrics_content_is_html_wrapped(self) -> None:
        song = SongFactory.create()
        client = APIClient()
        response = client.get(reverse("song-detail", kwargs={"pk": song.pk}))
        data = response.data["data"]
        lyric_content = data["lyrics"]["lyric"][0]["content"]
        chords_content = data["lyrics"]["chords"][0]["content"]
        assert "<p>" in lyric_content
        assert "\n" not in lyric_content
        assert "<p>" in chords_content
        assert "\n" not in chords_content


class TestCreateSong:
    def _client_for(self, user):  # type: ignore[no-untyped-def]
        client = APIClient()
        refresh = RefreshToken.for_user(user)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        return client

    def test_creates_song_returns_201(self) -> None:
        user = UserFactory.create(can_create_songs=True)
        author = AuthorFactory.create()
        client = self._client_for(user)
        response = client.post(
            reverse("song-list"),
            {
                "name": "My Song",
                "authors": [author.pk],
                "lyrics": _PLAIN_LYRICS,
            },
            format="json",
        )
        assert response.status_code == HTTPStatus.CREATED
        assert response.data["success"] is True
        song = Song.objects.get(pk=response.data["data"]["id"])
        assert song.is_public is False
        assert song.tone == "G"
        assert song.created_by == user

    def test_requires_can_create_songs_permission(self) -> None:
        user = UserFactory.create(can_create_songs=False)
        client = self._client_for(user)
        response = client.post(reverse("song-list"), {}, format="json")
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_unauthenticated_returns_401(self) -> None:
        client = APIClient()
        response = client.post(reverse("song-list"), {}, format="json")
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_invalid_lyrics_returns_400(self) -> None:
        user = UserFactory.create(can_create_songs=True)
        author = AuthorFactory.create()
        client = self._client_for(user)
        response = client.post(
            reverse("song-list"),
            {
                "name": "My Song",
                "authors": [author.pk],
                "lyrics": "No frontmatter here",
            },
            format="json",
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_nonexistent_author_returns_400(self) -> None:
        user = UserFactory.create(can_create_songs=True)
        client = self._client_for(user)
        response = client.post(
            reverse("song-list"),
            {
                "name": "My Song",
                "authors": [99999],
                "lyrics": _PLAIN_LYRICS,
            },
            format="json",
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_creates_with_tags(self) -> None:
        user = UserFactory.create(can_create_songs=True)
        author = AuthorFactory.create()
        tag = TagFactory.create()
        client = self._client_for(user)
        response = client.post(
            reverse("song-list"),
            {
                "name": "Tagged Song",
                "authors": [author.pk],
                "tags": [tag.pk],
                "lyrics": _PLAIN_LYRICS,
            },
            format="json",
        )
        assert response.status_code == HTTPStatus.CREATED
        song = Song.objects.get(pk=response.data["data"]["id"])
        assert song.tags.filter(pk=tag.pk).exists()


class TestPublishSong:
    def _client_for(self, user):  # type: ignore[no-untyped-def]
        client = APIClient()
        refresh = RefreshToken.for_user(user)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        return client

    def test_publishes_song(self) -> None:
        user = UserFactory.create(can_publish_songs=True)
        song = SongFactory.create(is_public=False)
        client = self._client_for(user)
        response = client.post(reverse("song-publish", kwargs={"pk": song.pk}))
        assert response.status_code == HTTPStatus.OK
        song.refresh_from_db()
        assert song.is_public is True

    def test_requires_can_publish_songs_permission(self) -> None:
        user = UserFactory.create(can_publish_songs=False)
        song = SongFactory.create()
        client = self._client_for(user)
        response = client.post(reverse("song-publish", kwargs={"pk": song.pk}))
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_unauthenticated_returns_401(self) -> None:
        song = SongFactory.create()
        client = APIClient()
        response = client.post(reverse("song-publish", kwargs={"pk": song.pk}))
        assert response.status_code == HTTPStatus.UNAUTHORIZED


class TestTransportSong:
    def test_transports_chords(self) -> None:
        song = SongFactory.create(plain_lyrics=_PLAIN_LYRICS, tone="G")
        client = APIClient()
        response = client.post(
            reverse("song-transport", kwargs={"pk": song.pk}),
            {"transport": "semi_tone", "current_tone": "G", "original_tone": "G"},
            format="json",
        )
        assert response.status_code == HTTPStatus.OK
        data = response.data["data"]
        chords_content = data["lyrics"]["chords"][0]["content"]
        assert "G#" in chords_content

    def test_invalid_tone_returns_400(self) -> None:
        song = SongFactory.create()
        client = APIClient()
        response = client.post(
            reverse("song-transport", kwargs={"pk": song.pk}),
            {"transport": "semi_tone", "current_tone": "X", "original_tone": "G"},
            format="json",
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_invalid_transport_value_returns_400(self) -> None:
        song = SongFactory.create()
        client = APIClient()
        response = client.post(
            reverse("song-transport", kwargs={"pk": song.pk}),
            {"transport": "octave", "current_tone": "G", "original_tone": "G"},
            format="json",
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_public_access_no_auth(self) -> None:
        song = SongFactory.create(plain_lyrics=_PLAIN_LYRICS, tone="G")
        client = APIClient()
        response = client.post(
            reverse("song-transport", kwargs={"pk": song.pk}),
            {"transport": "tone", "current_tone": "G", "original_tone": "G"},
            format="json",
        )
        assert response.status_code == HTTPStatus.OK
