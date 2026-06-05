from __future__ import annotations

import re

VALID_TONES = {
    "C", "C#", "Db", "D", "D#", "Eb", "E", "F",
    "F#", "Gb", "G", "G#", "Ab", "A", "A#", "Bb", "B",
}

_FRONTMATTER_RE = re.compile(r"^\s*---\s*\n(.*?)\n\s*---\s*\n?", re.DOTALL)
_SECTION_RE = re.compile(r"\[(verse|chorus|bridge)\]", re.IGNORECASE)
_CHORD_LINE_RE = re.compile(r"^\s*(\{[^}]+\}\s*)+$")
_CHORD_TOKEN_RE = re.compile(r"\{([^}]+)\}")


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    match = _FRONTMATTER_RE.match(text)
    if not match:
        msg = "Lyric frontmatter is missing. Add '---\\ntone: <note>\\n---' at the top."
        raise ValueError(msg)
    raw = match.group(1)
    body = text[match.end():]
    fields: dict[str, str] = {}
    for line in raw.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            fields[key.strip()] = val.strip()
    return fields, body


def _chord_token_to_display(match: re.Match[str]) -> str:
    inner = match.group(1)
    parts = [p.strip() for p in inner.split(",")]
    return "  ".join(parts)


def _strip_chords_from_line(line: str) -> str:
    return _CHORD_TOKEN_RE.sub("", line).rstrip()


def _render_chords_in_line(line: str) -> str:
    return _CHORD_TOKEN_RE.sub(_chord_token_to_display, line)


def _is_chord_only_line(line: str) -> bool:
    return bool(_CHORD_LINE_RE.match(line)) and bool(line.strip())


def _split_into_sections(body: str) -> list[tuple[str, str]]:
    parts = _SECTION_RE.split(body)
    sections: list[tuple[str, str]] = []
    i = 1
    while i + 1 < len(parts):
        section_type = parts[i].lower()
        content = parts[i + 1]
        sections.append((section_type, content))
        i += 2
    return sections


def _build_lyric_content(raw: str) -> str:
    lines = []
    for line in raw.splitlines():
        if _is_chord_only_line(line):
            continue
        stripped = _strip_chords_from_line(line)
        lines.append(stripped)
    return "\n".join(lines).strip()


def _build_chords_content(raw: str) -> str:
    lines = [_render_chords_in_line(line) for line in raw.splitlines()]
    return "\n".join(lines).strip()


class LyricsParser:
    def __init__(self, plain_lyrics: str) -> None:
        self.plain_lyrics = plain_lyrics

    def parse(self) -> dict:
        fields, body = _parse_frontmatter(self.plain_lyrics)

        tone = fields.get("tone", "").strip()
        if not tone or tone not in VALID_TONES:
            msg = "Lyric Tone is invalid. Please use a valid tone."
            raise ValueError(msg)

        guitar_capo_raw = fields.get("guitar_capo", "false").lower()
        guitar_capo = guitar_capo_raw == "true"

        sections = _split_into_sections(body)

        lyric_sections = []
        chord_sections = []
        for section_type, raw_content in sections:
            lyric_sections.append(
                {"type": section_type, "content": _build_lyric_content(raw_content)},
            )
            chord_sections.append(
                {"type": section_type, "content": _build_chords_content(raw_content)},
            )

        return {
            "tone": tone,
            "guitar_capo": guitar_capo,
            "lyric": lyric_sections,
            "chords": chord_sections,
        }
