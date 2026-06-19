from __future__ import annotations

import pytest

from cc.songs.queries import SongQuerySet
from cc.songs.tests.factories import AuthorFactory, SongFactory, TagFactory

pytestmark = pytest.mark.django_db


class TestSongQuerySetBase:
    def test_base_queryset_ordered_by_created_at_desc(self) -> None:
        song_a = SongFactory.create()
        song_b = SongFactory.create()
        qs = list(SongQuerySet().get_queryset())
        assert qs.index(song_b) < qs.index(song_a)

    def test_base_queryset_prefetches_tags_authors_verses(self) -> None:
        qs = SongQuerySet().get_queryset()
        assert {"tags", "authors", "verses"} <= set(qs._prefetch_related_lookups)  # type: ignore[attr-defined]


class TestSongQuerySetFilters:
    def test_filter_by_author_id_integer_returns_correct_songs(self) -> None:
        author = AuthorFactory.create()
        song = SongFactory.create()
        song.authors.add(author)
        other = SongFactory.create()

        result = set(SongQuerySet().with_filters(author_id=author.id).get_queryset())

        assert song in result
        assert other not in result

    def test_filter_by_tag_id_integer_returns_correct_songs(self) -> None:
        tag = TagFactory.create()
        song = SongFactory.create()
        song.tags.add(tag)
        other = SongFactory.create()

        result = set(SongQuerySet().with_filters(tag_id=tag.id).get_queryset())

        assert song in result
        assert other not in result

    def test_filter_by_search_returns_matching_songs(self) -> None:
        match = SongFactory.create(name="Ave María Cantata")
        miss = SongFactory.create(name="Padre Nuestro")

        result = set(SongQuerySet().with_filters(search="María").get_queryset())

        assert match in result
        assert miss not in result

    def test_filter_by_search_applies_distinct(self) -> None:
        author_a = AuthorFactory.create(name="Juan Pablo Segundo")
        author_b = AuthorFactory.create(name="Juan XXIII")
        song = SongFactory.create(name="Hosanna")
        song.authors.add(author_a, author_b)

        result = list(SongQuerySet().with_filters(search="Juan").get_queryset())

        assert result.count(song) == 1

    def test_combined_author_and_tag_filter_narrows_results(self) -> None:
        author = AuthorFactory.create()
        tag = TagFactory.create()
        match = SongFactory.create()
        match.authors.add(author)
        match.tags.add(tag)
        wrong_tag = SongFactory.create()
        wrong_tag.authors.add(author)
        wrong_author = SongFactory.create()
        wrong_author.tags.add(tag)

        result = set(
            SongQuerySet()
            .with_filters(author_id=author.id, tag_id=tag.id)
            .get_queryset(),
        )

        assert match in result
        assert wrong_tag not in result
        assert wrong_author not in result

    def test_unknown_filter_key_is_ignored(self) -> None:
        songs = SongFactory.create_batch(3)

        result = set(SongQuerySet().with_filters(nonexistent="x").get_queryset())

        assert {s.pk for s in songs} == {s.pk for s in result}

    def test_empty_string_filter_is_ignored(self) -> None:
        author = AuthorFactory.create()
        songs = SongFactory.create_batch(2)
        for s in songs:
            s.authors.add(author)

        result = set(SongQuerySet().with_filters(author_id="").get_queryset())

        assert {s.pk for s in songs} <= {s.pk for s in result}

    def test_none_value_filter_is_ignored(self) -> None:
        songs = SongFactory.create_batch(2)

        result = set(SongQuerySet().with_filters(author_id=None).get_queryset())

        assert {s.pk for s in songs} <= {s.pk for s in result}


class TestSongQuerySetIsolation:
    def test_two_instances_do_not_share_filters(self) -> None:
        a = SongQuerySet()
        a.with_filters(author_id=999)

        b = SongQuerySet()

        assert b.filters == {}
