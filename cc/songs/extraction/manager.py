from __future__ import annotations

from cc.songs.extraction.agents import AnthropicAgent, ExtractionAgent, GeminiAgent

_AGENTS: dict[str, type[ExtractionAgent]] = {
    "anthropic": AnthropicAgent,
    "gemini": GeminiAgent,
}

AGENT_CHOICES: list[tuple[str, str]] = [(k, k.title()) for k in _AGENTS]


def get_agent(name: str) -> ExtractionAgent:
    try:
        return _AGENTS[name]()
    except KeyError as exc:
        msg = f"Unknown extraction agent: {name!r}. Choose one of: {list(_AGENTS)}."
        raise ValueError(msg) from exc
