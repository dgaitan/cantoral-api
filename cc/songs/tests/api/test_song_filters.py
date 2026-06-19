from __future__ import annotations

from http import HTTPStatus

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from cc.songs.tests.factories import AuthorFactory, SongFactory, TagFactory

pytestmark = pytest.mark.django_db


class TestSongFilters:
    # ── Filter by author_id ──────────────────────────────────────────────────────

    def test_filter_by_author_id_returns_only_songs_by_that_author(self) -> None:
        author1 = AuthorFactory.create()
        author2 = AuthorFactory.create()
        song1 = SongFactory.create()
        song1.authors.add(author1)
        song2 = SongFactory.create()
        song2.authors.add(author2)
        song3 = SongFactory.create()
        song3.authors.add(author1, author2)

        response = APIClient().get(reverse("song-list"), {"author_id": author1.pk})

        assert response.status_code == HTTPStatus.OK
        result_ids = {s["id"] for s in response.data["data"]["results"]}
        assert result_ids == {song1.pk, song3.pk}
        assert song2.pk not in result_ids

    def test_filter_by_author_id_returns_empty_when_author_has_no_songs(self) -> None:
        author = AuthorFactory.create()
        SongFactory.create()

        response = APIClient().get(reverse("song-list"), {"author_id": author.pk})

        assert response.status_code == HTTPStatus.OK
        assert response.data["data"]["count"] == 0

    def test_filter_by_nonexistent_author_id_returns_empty_list(self) -> None:
        SongFactory.create()

        response = APIClient().get(reverse("song-list"), {"author_id": 99999})

        assert response.status_code == HTTPStatus.OK
        assert response.data["data"]["count"] == 0

    def test_filter_by_non_integer_author_id_returns_400(self) -> None:
        response = APIClient().get(reverse("song-list"), {"author_id": "abc"})

        assert response.status_code == HTTPStatus.BAD_REQUEST

    # ── Filter by tag_id ─────────────────────────────────────────────────────────

    def test_filter_by_tag_id_returns_only_songs_with_that_tag(self) -> None:
        tag1 = TagFactory.create()
        tag2 = TagFactory.create()
        song1 = SongFactory.create()
        song1.tags.add(tag1)
        song2 = SongFactory.create()
        song2.tags.add(tag2)
        song3 = SongFactory.create()
        song3.tags.add(tag1, tag2)

        response = APIClient().get(reverse("song-list"), {"tag_id": tag2.pk})

        assert response.status_code == HTTPStatus.OK
        result_ids = {s["id"] for s in response.data["data"]["results"]}
        assert result_ids == {song2.pk, song3.pk}
        assert song1.pk not in result_ids

    def test_filter_by_tag_id_returns_empty_when_tag_has_no_songs(self) -> None:
        tag = TagFactory.create()
        SongFactory.create()

        response = APIClient().get(reverse("song-list"), {"tag_id": tag.pk})

        assert response.status_code == HTTPStatus.OK
        assert response.data["data"]["count"] == 0

    def test_filter_by_nonexistent_tag_id_returns_empty_list(self) -> None:
        SongFactory.create()

        response = APIClient().get(reverse("song-list"), {"tag_id": 99999})

        assert response.status_code == HTTPStatus.OK
        assert response.data["data"]["count"] == 0

    def test_filter_by_non_integer_tag_id_returns_400(self) -> None:
        response = APIClient().get(reverse("song-list"), {"tag_id": "abc"})

        assert response.status_code == HTTPStatus.BAD_REQUEST

    # ── Combined author_id + tag_id ───────────────────────────────────────────────

    def test_filter_by_author_and_tag_returns_songs_matching_both(self) -> None:
        author1 = AuthorFactory.create()
        author2 = AuthorFactory.create()
        tag1 = TagFactory.create()
        tag2 = TagFactory.create()
        song1 = SongFactory.create()
        song1.authors.add(author1)
        song1.tags.add(tag1)
        song2 = SongFactory.create()
        song2.authors.add(author2)
        song2.tags.add(tag2)
        song3 = SongFactory.create()
        song3.authors.add(author1)
        song3.tags.add(tag1, tag2)

        response = APIClient().get(
            reverse("song-list"),
            {"author_id": author1.pk, "tag_id": tag1.pk},
        )

        assert response.status_code == HTTPStatus.OK
        result_ids = {s["id"] for s in response.data["data"]["results"]}
        assert result_ids == {song1.pk, song3.pk}
        assert song2.pk not in result_ids

    def test_filter_by_author_and_tag_with_no_intersection_returns_empty(self) -> None:
        author1 = AuthorFactory.create()
        tag1 = TagFactory.create()
        song = SongFactory.create()
        song.authors.add(author1)

        response = APIClient().get(
            reverse("song-list"),
            {"author_id": author1.pk, "tag_id": tag1.pk},
        )

        assert response.status_code == HTTPStatus.OK
        assert response.data["data"]["count"] == 0

    # ── Combined with ?search ─────────────────────────────────────────────────────

    def test_search_combined_with_author_id_narrows_results(self) -> None:
        author1 = AuthorFactory.create()
        author2 = AuthorFactory.create()
        # Both song names contain "Magna"; only song_a belongs to author1
        song_a = SongFactory.create(name="Hosanna Magna")
        song_a.authors.add(author1)
        song_b = SongFactory.create(name="Gloria Magna")
        song_b.authors.add(author2)

        response = APIClient().get(
            reverse("song-list"),
            {"search": "Magna", "author_id": author1.pk},
        )

        assert response.status_code == HTTPStatus.OK
        result_ids = {s["id"] for s in response.data["data"]["results"]}
        assert result_ids == {song_a.pk}

    def test_search_combined_with_tag_id_narrows_results(self) -> None:
        tag1 = TagFactory.create()
        tag2 = TagFactory.create()
        # Both song names contain "Sanctus"; only song_a has tag1
        song_a = SongFactory.create(name="Sanctus Primus")
        song_a.tags.add(tag1)
        song_b = SongFactory.create(name="Sanctus Alter")
        song_b.tags.add(tag2)

        response = APIClient().get(
            reverse("song-list"),
            {"search": "Sanctus", "tag_id": tag1.pk},
        )

        assert response.status_code == HTTPStatus.OK
        result_ids = {s["id"] for s in response.data["data"]["results"]}
        assert result_ids == {song_a.pk}

    def test_search_combined_with_author_and_tag_narrows_to_intersection(self) -> None:
        author1 = AuthorFactory.create()
        author2 = AuthorFactory.create()
        tag1 = TagFactory.create()
        tag2 = TagFactory.create()
        # All three song names contain "Agnus"; only song_a has author1 + tag1
        song_a = SongFactory.create(name="Agnus Prima")
        song_a.authors.add(author1)
        song_a.tags.add(tag1)
        song_b = SongFactory.create(name="Agnus Secunda")
        song_b.authors.add(author2)
        song_b.tags.add(tag1)
        song_c = SongFactory.create(name="Agnus Tertia")
        song_c.authors.add(author1)
        song_c.tags.add(tag2)

        response = APIClient().get(
            reverse("song-list"),
            {"search": "Agnus", "author_id": author1.pk, "tag_id": tag1.pk},
        )

        assert response.status_code == HTTPStatus.OK
        result_ids = {s["id"] for s in response.data["data"]["results"]}
        assert result_ids == {song_a.pk}

    def test_search_combined_with_author_id_returns_empty_when_no_match(self) -> None:
        author1 = AuthorFactory.create()
        author2 = AuthorFactory.create()
        # Song matches the search but belongs to author2, not author1
        song = SongFactory.create(name="Kyrie Eleison")
        song.authors.add(author2)

        response = APIClient().get(
            reverse("song-list"),
            {"search": "Kyrie", "author_id": author1.pk},
        )

        assert response.status_code == HTTPStatus.OK
        assert response.data["data"]["count"] == 0

    # ── General behaviour ─────────────────────────────────────────────────────────

    def test_filtered_results_are_paginated(self) -> None:
        author = AuthorFactory.create()
        total_songs = 25
        page_size = 20
        songs = SongFactory.create_batch(total_songs)
        for song in songs:
            song.authors.add(author)

        response = APIClient().get(reverse("song-list"), {"author_id": author.pk})

        assert response.status_code == HTTPStatus.OK
        data = response.data["data"]
        assert data["count"] == total_songs
        assert len(data["results"]) == page_size
        assert data["next"] is not None

    def test_filtering_requires_no_authentication(self) -> None:
        author = AuthorFactory.create()

        response = APIClient().get(reverse("song-list"), {"author_id": author.pk})

        assert response.status_code == HTTPStatus.OK
