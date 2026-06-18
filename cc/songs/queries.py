from __future__ import annotations

from typing import TYPE_CHECKING, List, Self
from django.db.models import Q

from cc.songs.models import Song
from cc.utils.queries import BaseQuerySet

if TYPE_CHECKING:
    from django.db.models import QuerySet


class SongQuerySet(BaseQuerySet):
    available_filters: List[str] = [
        "search",
        "author_id",
        "tag_id",
    ]

    def base_queryset(self) -> QuerySet[Song]:
        return Song.objects.prefetch_related("tags", "authors", "verses").order_by("-created_at")

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

        if self.filters.get("author_id"):
            try:
                author_id = int(self.filters["author_id"])
            except (ValueError, TypeError):
                raise ValueError(f"author_id must be an integer, got {self.filters['author_id']!r}")
            self.queryset = self.queryset.filter(authors__id=author_id)

        if self.filters.get("tag_id"):
            try:
                tag_id = int(self.filters["tag_id"])
            except (ValueError, TypeError):
                raise ValueError(f"tag_id must be an integer, got {self.filters['tag_id']!r}")
            self.queryset = self.queryset.filter(tags__id=tag_id)

        if needs_distinct:
            self.queryset = self.queryset.distinct()

        return self