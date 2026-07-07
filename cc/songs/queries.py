from __future__ import annotations

from typing import TYPE_CHECKING, Self

from django.db.models import Q

from cc.songs.models import Song
from cc.utils.queries import BaseQuerySet

if TYPE_CHECKING:
    from django.db.models import QuerySet


class SongQuerySet(BaseQuerySet):
    available_filters: list[str] = [
        "search",
        "author_id",
        "tag_id",
        "order_by",
        "order",
    ]

    ORDER_BY_FIELDS: frozenset[str] = frozenset({"views", "created_at"})
    RANDOM_ORDER_VALUE: str = "rand"
    ORDER_DIRECTION_PREFIXES: dict[str, str] = {"asc": "", "desc": "-"}

    _needs_distinct: bool = False

    def base_queryset(self) -> QuerySet[Song]:
        return Song.objects.prefetch_related("tags", "authors", "verses").order_by(
            "-created_at",
        )

    def perform_filters(self) -> Self:
        self._needs_distinct = False
        if self.filters.get("search"):
            search = self.filters["search"]
            self.queryset = self.queryset.filter(
                Q(name__search=search)
                | Q(plain_lyrics__search=search)
                | Q(authors__name__icontains=search)
                | Q(tags__name__icontains=search),
            )
            self._needs_distinct = True

        if self.filters.get("author_id"):
            try:
                author_id = int(self.filters["author_id"])
            except (ValueError, TypeError) as exc:
                msg = f"author_id must be an integer, got {self.filters['author_id']!r}"
                raise ValueError(msg) from exc
            self.queryset = self.queryset.filter(authors__id=author_id)

        if self.filters.get("tag_id"):
            try:
                tag_id = int(self.filters["tag_id"])
            except (ValueError, TypeError) as exc:
                msg = f"tag_id must be an integer, got {self.filters['tag_id']!r}"
                raise ValueError(msg) from exc
            self.queryset = self.queryset.filter(tags__id=tag_id)

        if self._needs_distinct:
            self.queryset = self.queryset.distinct()

        self.queryset = self._apply_ordering()

        return self

    def _apply_ordering(self) -> QuerySet[Song]:
        order_by = self.filters.get("order_by")
        order = self.filters.get("order")
        if order_by is None and order is None:
            return self.queryset

        field = order_by or "created_at"

        if field == self.RANDOM_ORDER_VALUE:
            return self._random_order_queryset()

        if field not in self.ORDER_BY_FIELDS:
            valid_values = sorted({*self.ORDER_BY_FIELDS, self.RANDOM_ORDER_VALUE})
            msg = f"order_by must be one of {valid_values}, got {order_by!r}"
            raise ValueError(msg)

        direction = order or "asc"
        try:
            prefix = self.ORDER_DIRECTION_PREFIXES[direction]
        except KeyError as exc:
            msg = (
                f"order must be one of {sorted(self.ORDER_DIRECTION_PREFIXES)}, "
                f"got {order!r}"
            )
            raise ValueError(msg) from exc

        return self.queryset.order_by(f"{prefix}{field}")

    def _random_order_queryset(self) -> QuerySet[Song]:
        # Postgres requires ORDER BY RANDOM() to appear in the SELECT DISTINCT
        # column list, which defeats the search filter's distinct() above — a
        # song matched via two joined rows (e.g. two authors) would come back
        # twice. Re-scope to the already-deduplicated pk set on a fresh,
        # non-distinct queryset instead, where ordering by "?" is unrestricted.
        if not self._needs_distinct:
            return self.queryset.order_by("?")
        deduplicated_pks = self.queryset.values("pk")
        return self.base_queryset().filter(pk__in=deduplicated_pks).order_by("?")
