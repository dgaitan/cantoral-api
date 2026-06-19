from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

if TYPE_CHECKING:
    from typing import TypeVar

    from django.db.models import QuerySet

    T = TypeVar("T")


class BaseQuerySet:
    queryset: QuerySet[T]
    available_filters: list[str] = []
    filters: dict[str, Any] = {}

    def __init__(self):
        self.filters: dict[str, Any] = {}
        self.queryset = self.base_queryset()

    def base_queryset(self) -> QuerySet[T]:
        msg = "base_queryset method must be implemented"
        raise NotImplementedError(msg)

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
            value = filter_value[-1] if isinstance(filter_value, list) else filter_value
            if value is None:
                continue
            if isinstance(value, str) and value.strip() == "":
                continue
            stripped = value.strip() if isinstance(value, str) else value
            self.filters[filter_name] = stripped
        return self
