from __future__ import annotations

from http import HTTPStatus

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from cc.playlists.models import Playlist, PlaylistSong
from cc.playlists.tests.factories import PlaylistFactory, PlaylistSongFactory
from cc.songs.tests.factories import SongFactory
from cc.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def _auth_client(user: object) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


# ── Archive (public list) ─────────────────────────────────────────────────────

class TestListPlaylists:
    def test_anonymous_sees_only_public_playlists(self) -> None:
        PlaylistFactory.create_batch(2, is_public=True)
        private = PlaylistFactory.create(is_public=False)

        response = APIClient().get(reverse("playlist-list"))

        assert response.status_code == HTTPStatus.OK
        uuids = [str(p["uuid"]) for p in response.data["data"]["results"]]
        assert str(private.uuid) not in uuids
        assert len(uuids) == 2

    def test_authenticated_sees_public_plus_own_private(self) -> None:
        user = UserFactory.create()
        other = UserFactory.create()
        PlaylistFactory.create_batch(2, is_public=True, owner=other)
        my_private = PlaylistFactory.create(is_public=False, owner=user)

        response = _auth_client(user).get(reverse("playlist-list"))

        assert response.status_code == HTTPStatus.OK
        uuids = [str(p["uuid"]) for p in response.data["data"]["results"]]
        assert str(my_private.uuid) in uuids
        assert len(uuids) == 3

    def test_authenticated_does_not_see_other_users_private_playlists(self) -> None:
        user = UserFactory.create()
        other = UserFactory.create()
        other_private = PlaylistFactory.create(is_public=False, owner=other)

        response = _auth_client(user).get(reverse("playlist-list"))

        assert response.status_code == HTTPStatus.OK
        uuids = [str(p["uuid"]) for p in response.data["data"]["results"]]
        assert str(other_private.uuid) not in uuids

    def test_search_by_name(self) -> None:
        PlaylistFactory.create(name="Adviento 2024", is_public=True)
        PlaylistFactory.create(name="Pascua", is_public=True)

        response = APIClient().get(reverse("playlist-list"), {"name": "Adviento"})

        assert response.status_code == HTTPStatus.OK
        results = response.data["data"]["results"]
        assert len(results) == 1
        assert results[0]["name"] == "Adviento 2024"

    def test_search_by_description(self) -> None:
        PlaylistFactory.create(description="Cantos para la misa del gallo", is_public=True)
        PlaylistFactory.create(description="Cantos de alabanza", is_public=True)

        response = APIClient().get(reverse("playlist-list"), {"description": "misa del gallo"})

        assert response.status_code == HTTPStatus.OK
        results = response.data["data"]["results"]
        assert len(results) == 1
        assert "misa del gallo" in results[0]["description"]

    def test_soft_deleted_playlists_are_excluded(self) -> None:
        from django.utils import timezone

        playlist = PlaylistFactory.create(is_public=True)
        Playlist.all_objects.filter(pk=playlist.pk).update(deleted_at=timezone.now())

        response = APIClient().get(reverse("playlist-list"))

        assert response.status_code == HTTPStatus.OK
        uuids = [str(p["uuid"]) for p in response.data["data"]["results"]]
        assert str(playlist.uuid) not in uuids


# ── Create ────────────────────────────────────────────────────────────────────

class TestCreatePlaylist:
    def test_authenticated_creates_playlist_with_defaults(self) -> None:
        user = UserFactory.create()

        response = _auth_client(user).post(reverse("playlist-list"), {"name": "Mi lista"})

        assert response.status_code == HTTPStatus.CREATED
        data = response.data["data"]
        assert "uuid" in data
        assert data["is_public"] is False
        assert data["is_collaborative"] is False
        assert data["owner_id"] == user.pk

    def test_authenticated_creates_public_collaborative_playlist(self) -> None:
        user = UserFactory.create()

        response = _auth_client(user).post(
            reverse("playlist-list"),
            {"name": "Lista compartida", "is_public": True, "is_collaborative": True},
        )

        assert response.status_code == HTTPStatus.CREATED
        data = response.data["data"]
        assert data["is_public"] is True
        assert data["is_collaborative"] is True

    def test_create_without_authentication_returns_401(self) -> None:
        response = APIClient().post(reverse("playlist-list"), {"name": "Sin sesión"})

        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_create_without_name_returns_400(self) -> None:
        user = UserFactory.create()

        response = _auth_client(user).post(reverse("playlist-list"), {})

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_create_with_name_exceeding_258_chars_returns_400(self) -> None:
        user = UserFactory.create()

        response = _auth_client(user).post(reverse("playlist-list"), {"name": "x" * 259})

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_create_with_description_exceeding_1000_chars_returns_400(self) -> None:
        user = UserFactory.create()

        response = _auth_client(user).post(
            reverse("playlist-list"), {"name": "Ok", "description": "x" * 1001}
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST


# ── Retrieve ──────────────────────────────────────────────────────────────────

class TestRetrievePlaylist:
    def test_anyone_can_retrieve_public_playlist(self) -> None:
        playlist = PlaylistFactory.create(is_public=True)

        response = APIClient().get(reverse("playlist-detail", kwargs={"uuid": playlist.uuid}))

        assert response.status_code == HTTPStatus.OK
        data = response.data["data"]
        assert str(data["uuid"]) == str(playlist.uuid)

    def test_owner_can_retrieve_own_private_playlist(self) -> None:
        user = UserFactory.create()
        playlist = PlaylistFactory.create(is_public=False, owner=user)

        response = _auth_client(user).get(reverse("playlist-detail", kwargs={"uuid": playlist.uuid}))

        assert response.status_code == HTTPStatus.OK

    def test_non_owner_cannot_retrieve_private_playlist(self) -> None:
        user = UserFactory.create()
        other = UserFactory.create()
        playlist = PlaylistFactory.create(is_public=False, owner=other)

        response = _auth_client(user).get(reverse("playlist-detail", kwargs={"uuid": playlist.uuid}))

        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_anonymous_cannot_retrieve_private_playlist(self) -> None:
        playlist = PlaylistFactory.create(is_public=False)

        response = APIClient().get(reverse("playlist-detail", kwargs={"uuid": playlist.uuid}))

        # DRF returns 401 (not 403) for unauthenticated requests when authenticators are configured.
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_retrieve_nonexistent_playlist_returns_404(self) -> None:
        import uuid

        response = APIClient().get(reverse("playlist-detail", kwargs={"uuid": uuid.uuid4()}))

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_retrieve_soft_deleted_playlist_returns_404(self) -> None:
        from django.utils import timezone

        playlist = PlaylistFactory.create(is_public=True)
        Playlist.all_objects.filter(pk=playlist.pk).update(deleted_at=timezone.now())

        response = APIClient().get(reverse("playlist-detail", kwargs={"uuid": playlist.uuid}))

        assert response.status_code == HTTPStatus.NOT_FOUND


# ── Update ────────────────────────────────────────────────────────────────────

class TestUpdatePlaylist:
    def test_owner_can_update_playlist(self) -> None:
        user = UserFactory.create()
        playlist = PlaylistFactory.create(owner=user, name="Old name")

        response = _auth_client(user).post(
            reverse("playlist-detail", kwargs={"uuid": playlist.uuid}),
            {"name": "Nuevo nombre", "description": "<p>Nueva descripción</p>"},
        )

        assert response.status_code == HTTPStatus.OK
        assert response.data["data"]["name"] == "Nuevo nombre"
        assert response.data["data"]["description"] == "<p>Nueva descripción</p>"

    def test_non_owner_cannot_update_playlist(self) -> None:
        user = UserFactory.create()
        other = UserFactory.create()
        playlist = PlaylistFactory.create(owner=other)

        response = _auth_client(user).post(
            reverse("playlist-detail", kwargs={"uuid": playlist.uuid}),
            {"name": "Intento"},
        )

        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_update_without_authentication_returns_401(self) -> None:
        playlist = PlaylistFactory.create(is_public=True)

        response = APIClient().post(
            reverse("playlist-detail", kwargs={"uuid": playlist.uuid}),
            {"name": "X"},
        )

        assert response.status_code == HTTPStatus.UNAUTHORIZED


# ── Delete (soft) ─────────────────────────────────────────────────────────────

class TestDeletePlaylist:
    def test_owner_can_soft_delete_playlist(self) -> None:
        user = UserFactory.create()
        playlist = PlaylistFactory.create(owner=user, is_public=True)

        response = _auth_client(user).delete(
            reverse("playlist-detail", kwargs={"uuid": playlist.uuid})
        )

        assert response.status_code == HTTPStatus.NO_CONTENT
        playlist.refresh_from_db()
        # Fetching via all_objects bypasses the soft-delete manager
        from cc.playlists.models import Playlist as P
        raw = P.all_objects.get(pk=playlist.pk)
        assert raw.deleted_at is not None

    def test_non_owner_cannot_delete_playlist(self) -> None:
        user = UserFactory.create()
        other = UserFactory.create()
        playlist = PlaylistFactory.create(owner=other)

        response = _auth_client(user).delete(
            reverse("playlist-detail", kwargs={"uuid": playlist.uuid})
        )

        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_delete_without_authentication_returns_401(self) -> None:
        playlist = PlaylistFactory.create(is_public=True)

        response = APIClient().delete(
            reverse("playlist-detail", kwargs={"uuid": playlist.uuid})
        )

        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_soft_deleted_playlist_no_longer_appears_in_archive(self) -> None:
        user = UserFactory.create()
        playlist = PlaylistFactory.create(owner=user, is_public=True)

        _auth_client(user).delete(reverse("playlist-detail", kwargs={"uuid": playlist.uuid}))

        response = APIClient().get(reverse("playlist-list"))
        uuids = [str(p["uuid"]) for p in response.data["data"]["results"]]
        assert str(playlist.uuid) not in uuids


# ── Songs in a playlist ───────────────────────────────────────────────────────

class TestPlaylistSongs:
    def test_anyone_can_list_songs_of_public_playlist(self) -> None:
        playlist = PlaylistFactory.create(is_public=True)
        songs = SongFactory.create_batch(3)
        for i, song in enumerate(songs):
            PlaylistSongFactory.create(playlist=playlist, song=song, order=i + 1)

        response = APIClient().get(reverse("playlist-songs", kwargs={"uuid": playlist.uuid}))

        assert response.status_code == HTTPStatus.OK
        assert len(response.data["data"]["results"]) == 3

    def test_owner_can_list_songs_of_private_playlist(self) -> None:
        user = UserFactory.create()
        playlist = PlaylistFactory.create(is_public=False, owner=user)
        PlaylistSongFactory.create_batch(2, playlist=playlist)

        response = _auth_client(user).get(reverse("playlist-songs", kwargs={"uuid": playlist.uuid}))

        assert response.status_code == HTTPStatus.OK
        assert len(response.data["data"]["results"]) == 2

    def test_non_owner_cannot_list_songs_of_private_playlist(self) -> None:
        user = UserFactory.create()
        other = UserFactory.create()
        playlist = PlaylistFactory.create(is_public=False, owner=other)

        response = _auth_client(user).get(reverse("playlist-songs", kwargs={"uuid": playlist.uuid}))

        assert response.status_code == HTTPStatus.FORBIDDEN


# ── Attach / Detach songs ─────────────────────────────────────────────────────

class TestAttachSongs:
    def test_owner_attaches_songs_to_playlist(self) -> None:
        user = UserFactory.create()
        playlist = PlaylistFactory.create(owner=user)
        songs = SongFactory.create_batch(3)

        response = _auth_client(user).post(
            reverse("playlist-songs-attach", kwargs={"uuid": playlist.uuid}),
            {"song_ids": [s.pk for s in songs]},
        )

        assert response.status_code == HTTPStatus.OK
        assert PlaylistSong.objects.filter(playlist=playlist).count() == 3

    def test_owner_detaches_song_already_in_playlist(self) -> None:
        user = UserFactory.create()
        playlist = PlaylistFactory.create(owner=user)
        song = SongFactory.create()
        PlaylistSongFactory.create(playlist=playlist, song=song)

        response = _auth_client(user).post(
            reverse("playlist-songs-attach", kwargs={"uuid": playlist.uuid}),
            {"song_ids": [song.pk]},
        )

        assert response.status_code == HTTPStatus.OK
        assert not PlaylistSong.objects.filter(playlist=playlist, song=song).exists()

    def test_collaborator_can_attach_songs_to_collaborative_playlist(self) -> None:
        owner = UserFactory.create()
        collaborator = UserFactory.create()
        playlist = PlaylistFactory.create(owner=owner, is_collaborative=True)
        song = SongFactory.create()

        response = _auth_client(collaborator).post(
            reverse("playlist-songs-attach", kwargs={"uuid": playlist.uuid}),
            {"song_ids": [song.pk]},
        )

        assert response.status_code == HTTPStatus.OK
        assert PlaylistSong.objects.filter(playlist=playlist, song=song).exists()

    def test_non_owner_cannot_attach_to_non_collaborative_playlist(self) -> None:
        owner = UserFactory.create()
        other = UserFactory.create()
        playlist = PlaylistFactory.create(owner=owner, is_collaborative=False, is_public=True)
        song = SongFactory.create()

        response = _auth_client(other).post(
            reverse("playlist-songs-attach", kwargs={"uuid": playlist.uuid}),
            {"song_ids": [song.pk]},
        )

        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_attach_without_authentication_returns_401(self) -> None:
        playlist = PlaylistFactory.create(is_public=True)

        response = APIClient().post(
            reverse("playlist-songs-attach", kwargs={"uuid": playlist.uuid}),
            {"song_ids": [1]},
        )

        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_attach_nonexistent_song_id_returns_400(self) -> None:
        user = UserFactory.create()
        playlist = PlaylistFactory.create(owner=user)

        response = _auth_client(user).post(
            reverse("playlist-songs-attach", kwargs={"uuid": playlist.uuid}),
            {"song_ids": [99999]},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST


# ── Reorder songs ─────────────────────────────────────────────────────────────

class TestReorderSongs:
    def test_owner_reorders_songs(self) -> None:
        user = UserFactory.create()
        playlist = PlaylistFactory.create(owner=user)
        s1, s2, s3 = SongFactory.create_batch(3)
        PlaylistSongFactory.create(playlist=playlist, song=s1, order=1)
        PlaylistSongFactory.create(playlist=playlist, song=s2, order=2)
        PlaylistSongFactory.create(playlist=playlist, song=s3, order=3)

        response = _auth_client(user).post(
            reverse("playlist-songs-reorder", kwargs={"uuid": playlist.uuid}),
            {"song_ids": [s3.pk, s1.pk, s2.pk]},
        )

        assert response.status_code == HTTPStatus.OK
        ordered = list(
            PlaylistSong.objects.filter(playlist=playlist).order_by("order").values_list("song_id", flat=True)
        )
        assert ordered == [s3.pk, s1.pk, s2.pk]

    def test_collaborator_can_reorder_songs_in_collaborative_playlist(self) -> None:
        owner = UserFactory.create()
        collaborator = UserFactory.create()
        playlist = PlaylistFactory.create(owner=owner, is_collaborative=True)
        s1, s2 = SongFactory.create_batch(2)
        PlaylistSongFactory.create(playlist=playlist, song=s1, order=1)
        PlaylistSongFactory.create(playlist=playlist, song=s2, order=2)

        response = _auth_client(collaborator).post(
            reverse("playlist-songs-reorder", kwargs={"uuid": playlist.uuid}),
            {"song_ids": [s2.pk, s1.pk]},
        )

        assert response.status_code == HTTPStatus.OK

    def test_non_owner_cannot_reorder_non_collaborative_playlist(self) -> None:
        owner = UserFactory.create()
        other = UserFactory.create()
        playlist = PlaylistFactory.create(owner=owner, is_collaborative=False, is_public=True)
        s1, s2 = SongFactory.create_batch(2)
        PlaylistSongFactory.create(playlist=playlist, song=s1, order=1)
        PlaylistSongFactory.create(playlist=playlist, song=s2, order=2)

        response = _auth_client(other).post(
            reverse("playlist-songs-reorder", kwargs={"uuid": playlist.uuid}),
            {"song_ids": [s1.pk, s2.pk]},
        )

        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_reorder_without_authentication_returns_401(self) -> None:
        playlist = PlaylistFactory.create(is_public=True)

        response = APIClient().post(
            reverse("playlist-songs-reorder", kwargs={"uuid": playlist.uuid}),
            {"song_ids": [1]},
        )

        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_reorder_with_mismatched_song_ids_returns_400(self) -> None:
        user = UserFactory.create()
        playlist = PlaylistFactory.create(owner=user)
        s1, s2 = SongFactory.create_batch(2)
        PlaylistSongFactory.create(playlist=playlist, song=s1, order=1)
        PlaylistSongFactory.create(playlist=playlist, song=s2, order=2)

        response = _auth_client(user).post(
            reverse("playlist-songs-reorder", kwargs={"uuid": playlist.uuid}),
            {"song_ids": [s1.pk, 99999]},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST


# ── Profile: my playlists ─────────────────────────────────────────────────────

class TestProfilePlaylists:
    def test_authenticated_retrieves_own_playlists(self) -> None:
        user = UserFactory.create()
        other = UserFactory.create()
        PlaylistFactory.create(owner=user, is_public=True)
        PlaylistFactory.create(owner=user, is_public=False)
        PlaylistFactory.create(owner=other, is_public=True)

        response = _auth_client(user).get(reverse("profile-playlists"))

        assert response.status_code == HTTPStatus.OK
        results = response.data["data"]["results"]
        assert len(results) == 2
        owner_ids = {p["owner_id"] for p in results}
        assert owner_ids == {user.pk}

    def test_soft_deleted_playlists_not_in_profile(self) -> None:
        from django.utils import timezone

        user = UserFactory.create()
        playlist = PlaylistFactory.create(owner=user)
        Playlist.all_objects.filter(pk=playlist.pk).update(deleted_at=timezone.now())

        response = _auth_client(user).get(reverse("profile-playlists"))

        assert response.status_code == HTTPStatus.OK
        uuids = [str(p["uuid"]) for p in response.data["data"]["results"]]
        assert str(playlist.uuid) not in uuids

    def test_profile_playlists_without_authentication_returns_401(self) -> None:
        response = APIClient().get(reverse("profile-playlists"))

        assert response.status_code == HTTPStatus.UNAUTHORIZED
