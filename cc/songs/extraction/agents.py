from __future__ import annotations

import base64
import urllib.request
from abc import ABC, abstractmethod
from pathlib import PurePosixPath
from typing import Any
from urllib.error import URLError

from anthropic import Anthropic
from anthropic.types import TextBlock
from django.conf import settings
from google import genai
from google.genai import types
from openai import OpenAI

_MIME_FROM_CONTENT_TYPE: dict[str, str] = {
    "image/jpeg": "image/jpeg",
    "image/jpg": "image/jpeg",
    "image/png": "image/png",
    "image/gif": "image/gif",
    "image/webp": "image/webp",
}

_MIME_FROM_EXTENSION: dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


def _download_image(url: str, timeout: int = 10) -> tuple[bytes, str]:
    try:
        req = urllib.request.Request(  # noqa: S310
            url,
            headers={"User-Agent": "CantorCatolico/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            data: bytes = resp.read()
            raw_ct: str = resp.headers.get("Content-Type", "")
            content_type = raw_ct.split(";", maxsplit=1)[0].strip()
    except URLError as exc:
        msg = f"Failed to download image from {url!r}: {exc}"
        raise ValueError(msg) from exc

    mime = _MIME_FROM_CONTENT_TYPE.get(content_type)
    if not mime:
        ext = PurePosixPath(url.split("?", maxsplit=1)[0]).suffix.lower()
        mime = _MIME_FROM_EXTENSION.get(ext)
    if not mime:
        msg = (
            f"Unsupported image type {content_type!r} for {url!r}. "
            "Use JPEG, PNG, GIF, or WebP."
        )
        raise ValueError(msg)
    return data, mime


_ImageData = tuple[bytes, str]  # (raw bytes, mime type)


class ExtractionAgent(ABC):
    name: str

    @abstractmethod
    def generate(
        self,
        prompt: str,
        image_url: str | None,
        image_data: _ImageData | None = None,
    ) -> str: ...


class AnthropicAgent(ExtractionAgent):
    name = "anthropic"

    def generate(
        self,
        prompt: str,
        image_url: str | None,
        image_data: _ImageData | None = None,
    ) -> str:
        if not settings.ANTHROPIC_API_KEY:
            msg = "ANTHROPIC_API_KEY is not configured."
            raise ValueError(msg)

        if image_data:
            raw, mime = image_data
            image_source: Any = {
                "type": "base64",
                "media_type": mime,
                "data": base64.standard_b64encode(raw).decode(),
            }
        else:
            image_source = {"type": "url", "url": image_url or ""}

        client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=settings.ANTHROPIC_VISION_MODEL,
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image", "source": image_source},
                    ],
                },
            ],
        )
        parts = [
            block.text for block in response.content if isinstance(block, TextBlock)
        ]
        if not parts:
            msg = "Anthropic response did not contain text content."
            raise ValueError(msg)
        return "\n".join(parts)


class GeminiAgent(ExtractionAgent):
    name = "gemini"

    def generate(
        self,
        prompt: str,
        image_url: str | None,
        image_data: _ImageData | None = None,
    ) -> str:
        if not settings.GEMINI_API_KEY:
            msg = "GEMINI_API_KEY is not configured."
            raise ValueError(msg)

        data, mime = image_data if image_data else _download_image(image_url or "")
        client: Any = genai.Client(api_key=settings.GEMINI_API_KEY)
        response = client.models.generate_content(
            model=settings.GEMINI_VISION_MODEL,
            contents=[
                prompt,
                types.Part.from_bytes(data=data, mime_type=mime),
            ],
        )
        text: str = response.text
        return text


class OpenAIAgent(ExtractionAgent):
    name = "openai"

    def generate(
        self,
        prompt: str,
        image_url: str | None,
        image_data: _ImageData | None = None,
    ) -> str:
        if not settings.OPENAI_API_KEY:
            msg = "OPENAI_API_KEY is not configured."
            raise ValueError(msg)

        if image_data:
            raw, mime = image_data
            b64 = base64.standard_b64encode(raw).decode()
            input_image = f"data:{mime};base64,{b64}"
        else:
            input_image = image_url or ""

        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.responses.create(
            model=settings.OPENAI_VISION_MODEL,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {"type": "input_image", "image_url": input_image},
                    ],
                },
            ],
        )
        text: str = response.output_text
        if not text:
            msg = "OpenAI response did not contain text content."
            raise ValueError(msg)
        return text
