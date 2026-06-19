from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import Q
from rest_framework.exceptions import ValidationError
from rest_framework.filters import BaseFilterBackend

if TYPE_CHECKING:
    from typing import Any

    from django.db.models import QuerySet
    from rest_framework.request import Request
    from rest_framework.views import APIView


class SongFTSFilter(BaseFilterBackend):
    def filter_queryset(
        self, request: Request, queryset: QuerySet, view: APIView,
    ) -> QuerySet:
        params = request.query_params
        needs_distinct = False

        if query := params.get("search", "").strip():
            queryset = queryset.filter(
                Q(name__search=query)
                | Q(plain_lyrics__search=query)
                | Q(authors__name__icontains=query)
                | Q(tags__name__icontains=query),
            )
            needs_distinct = True

        queryset, needs_distinct = self._maybe_filter_by_id(
            params, "author_id", "authors__id", queryset, needs_distinct=needs_distinct,
        )
        queryset, needs_distinct = self._maybe_filter_by_id(
            params, "tag_id", "tags__id", queryset, needs_distinct=needs_distinct,
        )

        if needs_distinct:
            return queryset.distinct()
        return queryset

    def _maybe_filter_by_id(
        self,
        params: Any,
        param_name: str,
        lookup: str,
        queryset: QuerySet,
        *,
        needs_distinct: bool,
    ) -> tuple[QuerySet, bool]:
        value = params.get(param_name, "").strip()
        if not value:
            return queryset, needs_distinct
        try:
            pk = int(value)
        except ValueError:
            raise ValidationError({param_name: "Must be an integer."}) from None
        return queryset.filter(**{lookup: pk}), True


class AuthorFTSFilter(BaseFilterBackend):
    def filter_queryset(
        self, request: Request, queryset: QuerySet, view: APIView,
    ) -> QuerySet:
        query = request.query_params.get("search", "").strip()
        if not query:
            return queryset
        return queryset.filter(Q(name__search=query) | Q(bio__search=query))


class TagFTSFilter(BaseFilterBackend):
    def filter_queryset(
        self, request: Request, queryset: QuerySet, view: APIView,
    ) -> QuerySet:
        query = request.query_params.get("search", "").strip()
        if not query:
            return queryset
        return queryset.filter(name__search=query)
