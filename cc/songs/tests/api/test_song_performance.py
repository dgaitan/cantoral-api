from __future__ import annotations

import threading
from datetime import timedelta
from http import HTTPStatus

import pytest
from django.db import connection, connections
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from cc.songs.models import Song
from cc.songs.tests.factories import AuthorFactory, SongFactory, TagFactory

pytestmark = pytest.mark.django_db

_LIST_QUERY_BUDGET = 7
_PAGE_SIZE = 20


def _set_created_at(song: Song, when: object) -> None:
    Song.objects.filter(pk=song.pk).update(created_at=when)


class TestRegisterSongView:
    def test_registering_a_view_increments_the_songs_view_count_by_one(self) -> None:
        initial_views = 20
        song = SongFactory.create(views=initial_views)

        response = APIClient().post(reverse("song-view", kwargs={"pk": song.pk}))

        assert response.status_code == HTTPStatus.OK
        assert response.data["data"]["views"] == initial_views + 1
        song.refresh_from_db()
        assert song.views == initial_views + 1

    def test_registering_a_view_returns_the_full_updated_song_payload(self) -> None:
        song = SongFactory.create(views=5)

        response = APIClient().post(reverse("song-view", kwargs={"pk": song.pk}))

        assert response.status_code == HTTPStatus.OK
        data = response.data["data"]
        expected_keys = {
            "id",
            "slug",
            "name",
            "views",
            "tags",
            "authors",
            "plain_lyrics",
            "tone",
            "is_public",
            "lyrics",
            "is_favorited",
        }
        assert expected_keys.issubset(data.keys())

    def test_registering_a_view_requires_no_authentication(self) -> None:
        initial_views = 5
        song = SongFactory.create(views=initial_views)

        response = APIClient().post(reverse("song-view", kwargs={"pk": song.pk}))

        assert response.status_code == HTTPStatus.OK
        assert response.data["data"]["views"] == initial_views + 1

    def test_registering_a_view_on_a_non_public_song_still_increments_it(self) -> None:
        song = SongFactory.create(views=0, is_public=False)

        response = APIClient().post(reverse("song-view", kwargs={"pk": song.pk}))

        assert response.status_code == HTTPStatus.OK
        assert response.data["data"]["views"] == 1

    def test_registering_a_view_on_a_non_existent_song_returns_404(self) -> None:
        response = APIClient().post(reverse("song-view", kwargs={"pk": 99999}))

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_registering_a_view_does_not_require_a_request_body(self) -> None:
        song = SongFactory.create(views=0)

        response = APIClient().post(
            reverse("song-view", kwargs={"pk": song.pk}),
            data=None,
        )

        assert response.status_code == HTTPStatus.OK

    @pytest.mark.django_db(transaction=True)
    def test_two_concurrent_view_registrations_on_the_same_song_both_persist(
        self,
    ) -> None:
        initial_views = 1
        concurrent_requests = 2
        song = SongFactory.create(views=initial_views)
        results: list[int] = []

        def _post_view() -> None:
            connections.close_all()
            response = APIClient().post(reverse("song-view", kwargs={"pk": song.pk}))
            results.append(response.status_code)
            connections.close_all()

        threads = [
            threading.Thread(target=_post_view) for _ in range(concurrent_requests)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert results == [HTTPStatus.OK] * concurrent_requests
        song.refresh_from_db()
        assert song.views == initial_views + concurrent_requests

    def test_repeated_view_registrations_accumulate(self) -> None:
        initial_views = 5
        repeat_count = 3
        song = SongFactory.create(views=initial_views)
        client = APIClient()
        url = reverse("song-view", kwargs={"pk": song.pk})

        for _ in range(repeat_count):
            response = client.post(url)
            assert response.status_code == HTTPStatus.OK

        song.refresh_from_db()
        assert song.views == initial_views + repeat_count

    def test_registering_a_view_is_a_single_atomic_update_query(self) -> None:
        song = SongFactory.create(views=0)

        with CaptureQueriesContext(connection) as ctx:
            response = APIClient().post(reverse("song-view", kwargs={"pk": song.pk}))

        assert response.status_code == HTTPStatus.OK
        views_update_queries = [
            q
            for q in ctx.captured_queries
            if q["sql"].strip().upper().startswith("UPDATE") and "views" in q["sql"]
        ]
        assert len(views_update_queries) == 1
        assert "+" in views_update_queries[0]["sql"]


class TestSongListLimit:
    def test_limit_caps_the_number_of_songs_returned(self) -> None:
        total_songs = 25
        limit = 10
        SongFactory.create_batch(total_songs)

        response = APIClient().get(reverse("song-list"), {"limit": limit})

        assert response.status_code == HTTPStatus.OK
        assert len(response.data["data"]) == limit

    def test_limit_response_is_a_plain_list_not_a_paginated_envelope(self) -> None:
        SongFactory.create_batch(25)

        response = APIClient().get(reverse("song-list"), {"limit": 5})

        assert response.status_code == HTTPStatus.OK
        assert isinstance(response.data["data"], list)

    def test_limit_greater_than_the_total_song_count_returns_all_songs(self) -> None:
        total_songs = 3
        SongFactory.create_batch(total_songs)

        response = APIClient().get(reverse("song-list"), {"limit": 50})

        assert response.status_code == HTTPStatus.OK
        assert len(response.data["data"]) == total_songs

    def test_limit_0_returns_a_validation_error(self) -> None:
        response = APIClient().get(reverse("song-list"), {"limit": 0})

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_negative_limit_returns_a_validation_error(self) -> None:
        response = APIClient().get(reverse("song-list"), {"limit": -5})

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_non_integer_limit_returns_a_validation_error(self) -> None:
        response = APIClient().get(reverse("song-list"), {"limit": "abc"})

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_omitting_limit_preserves_existing_paginated_behaviour(self) -> None:
        SongFactory.create_batch(25)

        response = APIClient().get(reverse("song-list"))

        assert response.status_code == HTTPStatus.OK
        data = response.data["data"]
        assert set(data.keys()) == {"count", "next", "previous", "results"}
        assert len(data["results"]) == _PAGE_SIZE

    def test_limit_combined_with_search_returns_at_most_limit_matching_songs(
        self,
    ) -> None:
        matching_songs = 10
        limit = 3
        for _ in range(matching_songs):
            SongFactory.create(name="Aleluya Gloriosa")

        response = APIClient().get(
            reverse("song-list"),
            {"search": "Aleluya", "limit": limit},
        )

        assert response.status_code == HTTPStatus.OK
        assert len(response.data["data"]) == limit

    def test_limit_combined_with_author_id_returns_at_most_limit_songs(self) -> None:
        author_songs = 10
        limit = 4
        author = AuthorFactory.create()
        for _ in range(author_songs):
            song = SongFactory.create()
            song.authors.add(author)

        response = APIClient().get(
            reverse("song-list"),
            {"author_id": author.pk, "limit": limit},
        )

        assert response.status_code == HTTPStatus.OK
        assert isinstance(response.data["data"], list)
        assert len(response.data["data"]) == limit

    def test_limit_requires_no_authentication(self) -> None:
        SongFactory.create_batch(3)

        response = APIClient().get(reverse("song-list"), {"limit": 5})

        assert response.status_code == HTTPStatus.OK


class TestSongListOrdering:
    def _create_songs_with_views_and_ages(self) -> dict[str, Song]:
        now = timezone.now()
        oldest = SongFactory.create(views=5)
        _set_created_at(oldest, now - timedelta(days=2))
        middle = SongFactory.create(views=20)
        _set_created_at(middle, now - timedelta(days=1))
        newest = SongFactory.create(views=1)
        _set_created_at(newest, now)
        return {"oldest": oldest, "middle": middle, "newest": newest}

    def test_order_by_views_with_default_order_sorts_ascending_by_views(self) -> None:
        songs = self._create_songs_with_views_and_ages()

        response = APIClient().get(reverse("song-list"), {"order_by": "views"})

        assert response.status_code == HTTPStatus.OK
        result_ids = [s["id"] for s in response.data["data"]["results"]]
        assert result_ids == [
            songs["newest"].pk,
            songs["oldest"].pk,
            songs["middle"].pk,
        ]

    def test_order_by_views_and_order_desc_sorts_descending_by_views(self) -> None:
        songs = self._create_songs_with_views_and_ages()

        response = APIClient().get(
            reverse("song-list"),
            {"order_by": "views", "order": "desc"},
        )

        assert response.status_code == HTTPStatus.OK
        result_ids = [s["id"] for s in response.data["data"]["results"]]
        assert result_ids == [
            songs["middle"].pk,
            songs["oldest"].pk,
            songs["newest"].pk,
        ]

    def test_order_by_created_at_with_default_order_sorts_ascending(self) -> None:
        songs = self._create_songs_with_views_and_ages()

        response = APIClient().get(reverse("song-list"), {"order_by": "created_at"})

        assert response.status_code == HTTPStatus.OK
        result_ids = [s["id"] for s in response.data["data"]["results"]]
        assert result_ids == [
            songs["oldest"].pk,
            songs["middle"].pk,
            songs["newest"].pk,
        ]

    def test_order_by_created_at_and_order_desc_sorts_descending(self) -> None:
        songs = self._create_songs_with_views_and_ages()

        response = APIClient().get(
            reverse("song-list"),
            {"order_by": "created_at", "order": "desc"},
        )

        assert response.status_code == HTTPStatus.OK
        result_ids = [s["id"] for s in response.data["data"]["results"]]
        assert result_ids == [
            songs["newest"].pk,
            songs["middle"].pk,
            songs["oldest"].pk,
        ]

    def test_order_without_order_by_defaults_order_by_to_created_at(self) -> None:
        songs = self._create_songs_with_views_and_ages()

        response = APIClient().get(reverse("song-list"), {"order": "desc"})

        assert response.status_code == HTTPStatus.OK
        result_ids = [s["id"] for s in response.data["data"]["results"]]
        assert result_ids == [
            songs["newest"].pk,
            songs["middle"].pk,
            songs["oldest"].pk,
        ]

    def test_neither_order_by_nor_order_given_preserves_default_ordering(self) -> None:
        songs = self._create_songs_with_views_and_ages()

        response = APIClient().get(reverse("song-list"))

        assert response.status_code == HTTPStatus.OK
        result_ids = [s["id"] for s in response.data["data"]["results"]]
        assert result_ids == [
            songs["newest"].pk,
            songs["middle"].pk,
            songs["oldest"].pk,
        ]

    def test_invalid_order_by_value_returns_a_validation_error(self) -> None:
        response = APIClient().get(reverse("song-list"), {"order_by": "name"})

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_invalid_order_value_returns_a_validation_error(self) -> None:
        response = APIClient().get(
            reverse("song-list"),
            {"order_by": "views", "order": "upwards"},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST

    @pytest.mark.parametrize("value", ["slug", "authors", "tags"])
    def test_invalid_order_by_values_are_rejected(self, value: str) -> None:
        response = APIClient().get(reverse("song-list"), {"order_by": value})

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_empty_order_by_value_is_treated_as_not_provided(self) -> None:
        songs = self._create_songs_with_views_and_ages()

        response = APIClient().get(reverse("song-list"), {"order_by": ""})

        assert response.status_code == HTTPStatus.OK
        result_ids = [s["id"] for s in response.data["data"]["results"]]
        assert result_ids == [
            songs["newest"].pk,
            songs["middle"].pk,
            songs["oldest"].pk,
        ]


class TestSongListRandomOrder:
    def test_order_by_rand_returns_all_songs(self) -> None:
        songs = SongFactory.create_batch(10)

        response = APIClient().get(reverse("song-list"), {"order_by": "rand"})

        assert response.status_code == HTTPStatus.OK
        result_ids = {s["id"] for s in response.data["data"]["results"]}
        assert result_ids == {song.pk for song in songs}

    def test_order_by_rand_shuffles_across_requests(self) -> None:
        SongFactory.create_batch(20)
        client = APIClient()
        url = reverse("song-list")

        def _ordered_ids() -> list[int]:
            response = client.get(url, {"order_by": "rand"})
            return [s["id"] for s in response.data["data"]["results"]]

        assert _ordered_ids() != _ordered_ids()

    def test_order_by_rand_ignores_order_direction(self) -> None:
        SongFactory.create_batch(3)

        response = APIClient().get(
            reverse("song-list"),
            {"order_by": "rand", "order": "desc"},
        )

        assert response.status_code == HTTPStatus.OK

    def test_order_by_rand_combined_with_limit_returns_limit_songs(self) -> None:
        songs = SongFactory.create_batch(10)
        limit = 4

        response = APIClient().get(
            reverse("song-list"),
            {"order_by": "rand", "limit": limit},
        )

        assert response.status_code == HTTPStatus.OK
        assert isinstance(response.data["data"], list)
        result_ids = [s["id"] for s in response.data["data"]]
        assert len(result_ids) == limit
        assert set(result_ids).issubset({song.pk for song in songs})

    def test_order_by_rand_combined_with_search_has_no_duplicates(self) -> None:
        # Regression test: Postgres requires ORDER BY RANDOM() to appear in
        # the SELECT DISTINCT column list, which — without the dedup fix in
        # SongQuerySet._random_order_queryset — makes a song matched via two
        # joined rows (two matching authors here) come back twice.
        song = SongFactory.create(name="Song With Two Matching Authors")
        song.authors.add(
            AuthorFactory.create(name="Aleluya Uno"),
            AuthorFactory.create(name="Aleluya Dos"),
        )
        SongFactory.create(name="Otra Cancion")

        response = APIClient().get(
            reverse("song-list"),
            {"search": "Aleluya", "order_by": "rand"},
        )

        assert response.status_code == HTTPStatus.OK
        result_ids = [s["id"] for s in response.data["data"]["results"]]
        assert result_ids == [song.pk]

    def test_order_by_rand_requires_no_authentication(self) -> None:
        SongFactory.create_batch(3)

        response = APIClient().get(reverse("song-list"), {"order_by": "rand"})

        assert response.status_code == HTTPStatus.OK


class TestSongListLimitAndOrderingCombined:
    def test_most_viewed_songs_use_case(self) -> None:
        low = SongFactory.create(views=1)
        mid = SongFactory.create(views=5)
        high = SongFactory.create(views=20)

        response = APIClient().get(
            reverse("song-list"),
            {"limit": 2, "order_by": "views", "order": "desc"},
        )

        assert response.status_code == HTTPStatus.OK
        assert isinstance(response.data["data"], list)
        result_ids = [s["id"] for s in response.data["data"]]
        assert result_ids == [high.pk, mid.pk]
        assert low.pk not in result_ids

    def test_limit_order_by_views_order_asc_returns_least_viewed_first(self) -> None:
        low = SongFactory.create(views=1)
        mid = SongFactory.create(views=5)
        SongFactory.create(views=20)

        response = APIClient().get(
            reverse("song-list"),
            {"limit": 2, "order_by": "views", "order": "asc"},
        )

        assert response.status_code == HTTPStatus.OK
        result_ids = [s["id"] for s in response.data["data"]]
        assert result_ids == [low.pk, mid.pk]

    def test_limit_order_by_order_combined_with_search(self) -> None:
        low = SongFactory.create(name="Pascua Primera", views=1)
        high = SongFactory.create(name="Pascua Segunda", views=10)
        SongFactory.create(name="Otro Canto", views=100)

        response = APIClient().get(
            reverse("song-list"),
            {"search": "Pascua", "limit": 2, "order_by": "views", "order": "desc"},
        )

        assert response.status_code == HTTPStatus.OK
        result_ids = [s["id"] for s in response.data["data"]]
        assert result_ids == [high.pk, low.pk]

    def test_limit_order_by_order_combined_with_author_id_and_tag_id(self) -> None:
        author = AuthorFactory.create()
        tag = TagFactory.create()
        matching_low = SongFactory.create(views=1)
        matching_low.authors.add(author)
        matching_low.tags.add(tag)
        matching_high = SongFactory.create(views=10)
        matching_high.authors.add(author)
        matching_high.tags.add(tag)
        # Matches author but not tag — must be excluded.
        non_matching = SongFactory.create(views=50)
        non_matching.authors.add(author)

        response = APIClient().get(
            reverse("song-list"),
            {
                "author_id": author.pk,
                "tag_id": tag.pk,
                "limit": 2,
                "order_by": "views",
                "order": "desc",
            },
        )

        assert response.status_code == HTTPStatus.OK
        result_ids = [s["id"] for s in response.data["data"]]
        assert result_ids == [matching_high.pk, matching_low.pk]
        assert non_matching.pk not in result_ids


class TestSongListQueryBudget:
    def test_limited_ordered_list_does_not_produce_n1_queries(self) -> None:
        limit = 5
        for i in range(10):
            song = SongFactory.create(views=i)
            for author in AuthorFactory.create_batch(3):
                song.authors.add(author)
            for tag in TagFactory.create_batch(3):
                song.tags.add(tag)

        with CaptureQueriesContext(connection) as ctx:
            response = APIClient().get(
                reverse("song-list"),
                {"limit": limit, "order_by": "views", "order": "desc"},
            )

        assert response.status_code == HTTPStatus.OK
        assert isinstance(response.data["data"], list)
        assert len(response.data["data"]) == limit
        result_views = [s["views"] for s in response.data["data"]]
        assert result_views == sorted(result_views, reverse=True)
        assert len(ctx) <= _LIST_QUERY_BUDGET
