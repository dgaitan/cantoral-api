from __future__ import annotations

from typing import TYPE_CHECKING, Self

from django.db.models import Q

from cc.songs.models import Song
from cc.utils.queries import BaseQuerySet

if TYPE_CHECKING:
    from django.db.models import QuerySet


def _invalid_integer_filter_error(filter_name: str, value: object) -> ValueError:
    return ValueError(f"{filter_name} must be an integer, got {value!r}")


AUTHOR_ID_FILTER = "author_id"
TAG_ID_FILTER = "tag_id"


class SongQuerySet(BaseQuerySet):
    available_filters: list[str] = [
        "search",
        AUTHOR_ID_FILTER,
        TAG_ID_FILTER,
    ]

    def base_queryset(self) -> QuerySet[Song]:
        return Song.objects.prefetch_related(
            "tags",
            "authors",
            "verses",
        ).order_by("-created_at")

    def perform_filters(self) -> Self:
        needs_distinct: bool = False
        if self.filters.get("search"):
            search = self.filters["search"]
            self.queryset = self.queryset.filter(
                Q(name__search=search)
                | Q(plain_lyrics__search=search)
                | Q(authors__name__icontains=search)
                | Q(tags__name__icontains=search),
            )
            needs_distinct = True

        if self.filters.get(AUTHOR_ID_FILTER):
            try:
                author_id = int(self.filters[AUTHOR_ID_FILTER])
            except (ValueError, TypeError) as err:
                raise _invalid_integer_filter_error(
                    AUTHOR_ID_FILTER,
                    self.filters[AUTHOR_ID_FILTER],
                ) from err
            self.queryset = self.queryset.filter(authors__id=author_id)

        if self.filters.get(TAG_ID_FILTER):
            try:
                tag_id = int(self.filters[TAG_ID_FILTER])
            except (ValueError, TypeError) as err:
                raise _invalid_integer_filter_error(
                    TAG_ID_FILTER,
                    self.filters[TAG_ID_FILTER],
                ) from err
            self.queryset = self.queryset.filter(tags__id=tag_id)

        if needs_distinct:
            self.queryset = self.queryset.distinct()

        return self
