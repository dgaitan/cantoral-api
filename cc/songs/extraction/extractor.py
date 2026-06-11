from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from cc.songs.lyrics.parser import VALID_TONES

if TYPE_CHECKING:
    from cc.songs.extraction.agents import ExtractionAgent

_EXTRACTION_PROMPT = f"""You are a chord-sheet transcription assistant \
for a Catholic songbook.

Analyze the chord sheet image and return ONLY valid JSON with this exact shape:
{{"name": "<song title>", "plain_lyrics": "<lyrics document>"}}

Rules for plain_lyrics:
1. Start with frontmatter:
---
tone: <key>
---
Use tone from this list only: {", ".join(sorted(VALID_TONES))}
Infer the key from the chords shown in the image.

2. Divide the song into sections using lowercase markers on their own line:
[verse]
[chorus]
[bridge]

3. Chords must use curly braces and preserve horizontal alignment above lyrics:
     {{G}}                   {{D}}
Porque eres la razón de mi vida
 {{C}}      {{D}}        {{G}}
Mi fuerza consuelo y alegría

4. Multiple chords at one position: {{Em,A,C,D}}
5. Preserve Spanish text and accents exactly.
6. Do not wrap the JSON in markdown code fences.
7. Do not include commentary outside the JSON.

If the title is visible in the image, use it for name. \
Otherwise infer a reasonable title from the lyrics.
"""

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```")


def parse_extraction_response(text: str) -> dict[str, str]:
    stripped = text.strip()
    fence_match = _JSON_BLOCK_RE.search(stripped)
    if fence_match:
        stripped = fence_match.group(1).strip()
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError as exc:
        msg = "Could not parse extraction response as JSON."
        raise ValueError(msg) from exc
    if not isinstance(payload, dict):
        msg = "Extraction response must be a JSON object."
        raise ValueError(msg)  # noqa: TRY004
    name = payload.get("name")
    plain_lyrics = payload.get("plain_lyrics")
    if not isinstance(name, str) or not name.strip():
        msg = "Extraction response is missing a valid song name."
        raise ValueError(msg)
    if not isinstance(plain_lyrics, str) or not plain_lyrics.strip():
        msg = "Extraction response is missing valid plain_lyrics."
        raise ValueError(msg)
    return {"name": name.strip(), "plain_lyrics": plain_lyrics.strip()}


class ChordSheetExtractor:
    def __init__(self, image_url: str, agent: ExtractionAgent) -> None:
        self.image_url = image_url
        self.agent = agent

    def extract(self) -> dict[str, str]:
        text = self.agent.generate(_EXTRACTION_PROMPT, self.image_url)
        return parse_extraction_response(text)
