from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self, List
from django.db.models import QuerySet

if TYPE_CHECKING:
    from typing import TypeVar
    T = TypeVar("T")

class BaseQuerySet:
    queryset: QuerySet[T]
    available_filters: List[str] = []
    filters: dict[str, Any] = {}

    def __init__(self):
        self.filters: dict[str, Any] = {}
        self.queryset = self.base_queryset()

    def base_queryset(self) -> QuerySet[T]:
        raise NotImplementedError("base_queryset method must be implemented")

    def get_queryset(self) -> QuerySet[T]:
        return self.queryset

    def with_filters(self, **kwargs: Any) -> Self:
        self.apply_filters(**kwargs)
        self.perform_filters()
        return self

    def perform_filters(self) -> Self:
        return self

    def apply_filters(self, **kwargs: Any) -> Self:
        for filter_name, filter_value in kwargs.items():
            if filter_name not in self.available_filters:
                continue
            # QueryDict unpacks values as lists; take the last element
            if isinstance(filter_value, list):
                filter_value = filter_value[-1] if filter_value else None
            if filter_value is None:
                continue
            if isinstance(filter_value, str) and filter_value.strip() == "":
                continue
            self.filters[filter_name] = filter_value.strip() if isinstance(filter_value, str) else filter_value
        return self
