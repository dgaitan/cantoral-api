from __future__ import annotations

from cc.songs.extraction.agents import (
    AnthropicAgent,
    ExtractionAgent,
    GeminiAgent,
    OpenAIAgent,
)

_AGENTS: dict[str, type[ExtractionAgent]] = {
    "anthropic": AnthropicAgent,
    "gemini": GeminiAgent,
    "openai": OpenAIAgent,
}

_DISPLAY_NAMES: dict[str, str] = {
    "anthropic": "Anthropic",
    "gemini": "Gemini",
    "openai": "OpenAI",
}

AGENT_CHOICES: list[tuple[str, str]] = [
    (k, _DISPLAY_NAMES.get(k, k.title())) for k in _AGENTS
]


def get_agent(name: str) -> ExtractionAgent:
    try:
        return _AGENTS[name]()
    except KeyError as exc:
        msg = f"Unknown extraction agent: {name!r}. Choose one of: {list(_AGENTS)}."
        raise ValueError(msg) from exc
