from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import Q
from rest_framework.filters import BaseFilterBackend

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from rest_framework.request import Request
    from rest_framework.views import APIView


class SongFTSFilter(BaseFilterBackend):
    def filter_queryset(
        self, request: Request, queryset: QuerySet, view: APIView,
    ) -> QuerySet:
        query = request.query_params.get("search", "").strip()
        if not query:
            return queryset
        return (
            queryset.filter(
                Q(name__search=query)
                | Q(plain_lyrics__search=query)
                | Q(authors__name__icontains=query)
                | Q(tags__name__icontains=query),
            )
            .distinct()
        )


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
