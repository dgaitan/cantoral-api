from __future__ import annotations

from typing import Any

from django.utils.text import slugify


class SlugAutoGenerateMixin:
    """Serializer mixin: auto-generates slug from name when slug is blank."""

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        data = super().validate(data)  # type: ignore[misc]
        instance = getattr(self, "instance", None)
        is_partial = getattr(self, "partial", False)
        if not is_partial:
            if not data.get("slug"):
                name = data.get("name") or (instance.name if instance else "")
                data["slug"] = slugify(name)
        elif "slug" in data and not data["slug"]:
            name = data.get("name") or (instance.name if instance else "")
            data["slug"] = slugify(name)
        return data
