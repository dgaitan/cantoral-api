from __future__ import annotations

from http import HTTPStatus

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework.test import APIClient

from cc.songs.tests.factories import AuthorFactory, SongFactory, TagFactory

pytestmark = pytest.mark.django_db

_TOTAL_ITEMS = 25
_PAGE_SIZE = 20
_SECOND_PAGE_ITEMS = 5
_DEFAULT_ITEMS = 5
_LIST_QUERY_BUDGET = 7
_DETAIL_QUERY_BUDGET = 8

_LYRICS_WITH_PASTOR = """\
---
tone: G
---
[verse]
     {G}
El Señor es mi pastor
"""

_LYRICS_WITHOUT_PASTOR = """\
---
tone: G
---
[verse]
     {G}
Cantad alegres al Señor
"""


class TestElementFilters:
    def test_list_songs_returns_paginated_envelope(self) -> None:
        SongFactory.create_batch(25)
        client = APIClient()
        response = client.get(reverse("song-list"))
        assert response.status_code == HTTPStatus.OK
        data = response.data["data"]
        assert set(data.keys()) >= {"count", "next", "previous", "results"}
        assert data["count"] == _TOTAL_ITEMS
        assert len(data["results"]) == _PAGE_SIZE
        assert data["next"] is not None
        assert data["previous"] is None

    def test_list_songs_second_page(self) -> None:
        SongFactory.create_batch(25)
        client = APIClient()
        response = client.get(reverse("song-list"), {"page": 2})
        assert response.status_code == HTTPStatus.OK
        data = response.data["data"]
        assert len(data["results"]) == _SECOND_PAGE_ITEMS
        assert data["previous"] is not None
        assert data["next"] is None

    def test_list_songs_publicly_accessible(self) -> None:
        SongFactory.create()
        client = APIClient()
        response = client.get(reverse("song-list"))
        assert response.status_code == HTTPStatus.OK

    def test_list_songs_empty_returns_paginated_envelope(self) -> None:
        client = APIClient()
        response = client.get(reverse("song-list"))
        assert response.status_code == HTTPStatus.OK
        data = response.data["data"]
        assert data["count"] == 0
        assert data["results"] == []

    def test_search_songs_by_name(self) -> None:
        SongFactory.create(name="Ave María")
        SongFactory.create(name="Padre Nuestro")
        client = APIClient()
        response = client.get(reverse("song-list"), {"search": "María"})
        assert response.status_code == HTTPStatus.OK
        results = response.data["data"]["results"]
        assert any(s["name"] == "Ave María" for s in results)
        assert not any(s["name"] == "Padre Nuestro" for s in results)

    def test_search_songs_by_author_name(self) -> None:
        author = AuthorFactory.create(name="San Juan de la Cruz")
        song = SongFactory.create(name="Noche Oscura")
        song.authors.add(author)
        SongFactory.create(name="Alabanza")
        client = APIClient()
        response = client.get(reverse("song-list"), {"search": "Juan"})
        assert response.status_code == HTTPStatus.OK
        results = response.data["data"]["results"]
        assert any(s["name"] == "Noche Oscura" for s in results)
        assert not any(s["name"] == "Alabanza" for s in results)

    def test_search_songs_by_tag_name(self) -> None:
        tag = TagFactory.create(name="Adviento")
        song = SongFactory.create(name="Ven Señor")
        song.tags.add(tag)
        SongFactory.create(name="Gloria")
        client = APIClient()
        response = client.get(reverse("song-list"), {"search": "Adviento"})
        assert response.status_code == HTTPStatus.OK
        results = response.data["data"]["results"]
        assert any(s["name"] == "Ven Señor" for s in results)
        assert not any(s["name"] == "Gloria" for s in results)

    def test_search_songs_by_lyrics(self) -> None:
        SongFactory.create(name="Salmo 22", plain_lyrics=_LYRICS_WITH_PASTOR)
        SongFactory.create(name="Himno", plain_lyrics=_LYRICS_WITHOUT_PASTOR)
        client = APIClient()
        response = client.get(reverse("song-list"), {"search": "pastor"})
        assert response.status_code == HTTPStatus.OK
        results = response.data["data"]["results"]
        assert any(s["name"] == "Salmo 22" for s in results)

    def test_search_songs_no_results(self) -> None:
        SongFactory.create_batch(3)
        client = APIClient()
        response = client.get(reverse("song-list"), {"search": "xyznonexistent"})
        assert response.status_code == HTTPStatus.OK
        data = response.data["data"]
        assert data["count"] == 0
        assert data["results"] == []

    def test_search_songs_empty_query_returns_all(self) -> None:
        SongFactory.create_batch(5)
        client = APIClient()
        response = client.get(reverse("song-list"), {"search": ""})
        assert response.status_code == HTTPStatus.OK
        assert response.data["data"]["count"] == _DEFAULT_ITEMS

    def test_list_authors_returns_paginated_envelope(self) -> None:
        AuthorFactory.create_batch(25)
        client = APIClient()
        response = client.get(reverse("author-list"))
        assert response.status_code == HTTPStatus.OK
        data = response.data["data"]
        assert data["count"] == _TOTAL_ITEMS
        assert len(data["results"]) == _PAGE_SIZE
        assert data["next"] is not None

    def test_list_authors_second_page(self) -> None:
        AuthorFactory.create_batch(25)
        client = APIClient()
        response = client.get(reverse("author-list"), {"page": 2})
        assert response.status_code == HTTPStatus.OK
        data = response.data["data"]
        assert len(data["results"]) == _SECOND_PAGE_ITEMS
        assert data["next"] is None

    def test_list_authors_empty_returns_paginated_envelope(self) -> None:
        client = APIClient()
        response = client.get(reverse("author-list"))
        assert response.status_code == HTTPStatus.OK
        data = response.data["data"]
        assert data["count"] == 0
        assert data["results"] == []

    def test_search_authors_by_name(self) -> None:
        AuthorFactory.create(name="San Agustín")
        AuthorFactory.create(name="Santa Teresa")
        client = APIClient()
        response = client.get(reverse("author-list"), {"search": "Agustín"})
        assert response.status_code == HTTPStatus.OK
        results = response.data["data"]["results"]
        assert any(a["name"] == "San Agustín" for a in results)
        assert not any(a["name"] == "Santa Teresa" for a in results)

    def test_search_authors_by_bio(self) -> None:
        AuthorFactory.create(
            name="Luis de León",
            bio="Poeta y fraile agustino del siglo XVI",
        )
        AuthorFactory.create(name="Francisco", bio="Compositor moderno")
        client = APIClient()
        response = client.get(reverse("author-list"), {"search": "agustino"})
        assert response.status_code == HTTPStatus.OK
        results = response.data["data"]["results"]
        assert any(a["name"] == "Luis de León" for a in results)

    def test_search_authors_no_results(self) -> None:
        AuthorFactory.create_batch(2)
        client = APIClient()
        response = client.get(reverse("author-list"), {"search": "xyznonexistent"})
        assert response.status_code == HTTPStatus.OK
        data = response.data["data"]
        assert data["count"] == 0
        assert data["results"] == []

    def test_list_tags_returns_paginated_envelope(self) -> None:
        TagFactory.create_batch(25)
        client = APIClient()
        response = client.get(reverse("tag-list"))
        assert response.status_code == HTTPStatus.OK
        data = response.data["data"]
        assert data["count"] == _TOTAL_ITEMS
        assert len(data["results"]) == _PAGE_SIZE

    def test_list_tags_empty_returns_paginated_envelope(self) -> None:
        client = APIClient()
        response = client.get(reverse("tag-list"))
        assert response.status_code == HTTPStatus.OK
        data = response.data["data"]
        assert data["count"] == 0
        assert data["results"] == []

    def test_search_tags_by_name(self) -> None:
        TagFactory.create(name="Semana Santa")
        TagFactory.create(name="Navidad")
        client = APIClient()
        response = client.get(reverse("tag-list"), {"search": "Santa"})
        assert response.status_code == HTTPStatus.OK
        results = response.data["data"]["results"]
        assert any(t["name"] == "Semana Santa" for t in results)
        assert not any(t["name"] == "Navidad" for t in results)

    def test_search_tags_no_results(self) -> None:
        TagFactory.create_batch(3)
        client = APIClient()
        response = client.get(reverse("tag-list"), {"search": "xyznonexistent"})
        assert response.status_code == HTTPStatus.OK
        assert response.data["data"]["count"] == 0

    def test_author_songs_returns_paginated_envelope(self) -> None:
        author = AuthorFactory.create()
        for song in SongFactory.create_batch(25):
            song.authors.add(author)
        client = APIClient()
        response = client.get(reverse("author-songs", kwargs={"pk": author.pk}))
        assert response.status_code == HTTPStatus.OK
        data = response.data["data"]
        assert data["count"] == _TOTAL_ITEMS
        assert len(data["results"]) == _PAGE_SIZE

    def test_author_songs_empty_returns_paginated_envelope(self) -> None:
        author = AuthorFactory.create()
        client = APIClient()
        response = client.get(reverse("author-songs", kwargs={"pk": author.pk}))
        assert response.status_code == HTTPStatus.OK
        data = response.data["data"]
        assert data["count"] == 0
        assert data["results"] == []

    def test_tag_songs_returns_paginated_envelope(self) -> None:
        tag = TagFactory.create()
        for song in SongFactory.create_batch(25):
            song.tags.add(tag)
        client = APIClient()
        response = client.get(reverse("tag-songs", kwargs={"pk": tag.pk}))
        assert response.status_code == HTTPStatus.OK
        data = response.data["data"]
        assert data["count"] == _TOTAL_ITEMS
        assert len(data["results"]) == _PAGE_SIZE

    def test_tag_songs_empty_returns_paginated_envelope(self) -> None:
        tag = TagFactory.create()
        client = APIClient()
        response = client.get(reverse("tag-songs", kwargs={"pk": tag.pk}))
        assert response.status_code == HTTPStatus.OK
        data = response.data["data"]
        assert data["count"] == 0
        assert data["results"] == []

    def test_list_songs_no_n1(self) -> None:
        for _ in range(10):
            song = SongFactory.create()
            for author in AuthorFactory.create_batch(3):
                song.authors.add(author)
            for tag in TagFactory.create_batch(3):
                song.tags.add(tag)
        client = APIClient()
        with CaptureQueriesContext(connection) as ctx:
            response = client.get(reverse("song-list"))
        assert response.status_code == HTTPStatus.OK
        assert len(ctx) <= _LIST_QUERY_BUDGET

    def test_author_songs_no_n1(self) -> None:
        author = AuthorFactory.create()
        for _ in range(10):
            song = SongFactory.create()
            song.authors.add(author)
            for extra_author in AuthorFactory.create_batch(2):
                song.authors.add(extra_author)
            for tag in TagFactory.create_batch(3):
                song.tags.add(tag)
        client = APIClient()
        with CaptureQueriesContext(connection) as ctx:
            response = client.get(reverse("author-songs", kwargs={"pk": author.pk}))
        assert response.status_code == HTTPStatus.OK
        assert len(ctx) <= _DETAIL_QUERY_BUDGET

    def test_tag_songs_no_n1(self) -> None:
        tag = TagFactory.create()
        for _ in range(10):
            song = SongFactory.create()
            song.tags.add(tag)
            for extra_tag in TagFactory.create_batch(2):
                song.tags.add(extra_tag)
            for author in AuthorFactory.create_batch(2):
                song.authors.add(author)
        client = APIClient()
        with CaptureQueriesContext(connection) as ctx:
            response = client.get(reverse("tag-songs", kwargs={"pk": tag.pk}))
        assert response.status_code == HTTPStatus.OK
        assert len(ctx) <= _DETAIL_QUERY_BUDGET

    def test_list_songs_without_search_returns_all(self) -> None:
        songs = SongFactory.create_batch(5)
        client = APIClient()
        response = client.get(reverse("song-list"))
        assert response.status_code == HTTPStatus.OK
        data = response.data["data"]
        assert data["count"] == _DEFAULT_ITEMS
        result_ids = {s["id"] for s in data["results"]}
        assert result_ids == {song.pk for song in songs}
