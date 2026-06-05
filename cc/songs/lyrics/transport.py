from __future__ import annotations

import re

CHROMATIC = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Map flat spellings to their sharp equivalent for index lookup
_FLAT_TO_SHARP: dict[str, str] = {
    "Db": "C#", "Eb": "D#", "Fb": "E", "Gb": "F#", "Ab": "G#", "Bb": "A#", "Cb": "B",
}

# Preferred display form depends on original root: flats stay flats, sharps stay sharps
_SHARP_TO_FLAT: dict[str, str] = {v: k for k, v in _FLAT_TO_SHARP.items()}

_CHORD_TOKEN_RE = re.compile(r"\{([^}]+)\}")
_ROOT_RE = re.compile(r"^([A-G][#b]?)(.*)")

TRANSPORT_SEMITONES: dict[str, int] = {
    "semi_tone": 1,
    "tone": 2,
}


def _note_to_index(note: str) -> int:
    canonical = _FLAT_TO_SHARP.get(note, note)
    return CHROMATIC.index(canonical)


def _index_to_note(index: int, *, prefer_flat: bool = False) -> str:
    note = CHROMATIC[index % 12]
    if prefer_flat and note in _SHARP_TO_FLAT:
        return _SHARP_TO_FLAT[note]
    return note


def _transpose_root(root: str, semitones: int) -> str:
    prefer_flat = root in _FLAT_TO_SHARP or root.endswith("b")
    idx = _note_to_index(root)
    new_idx = (idx + semitones) % 12
    return _index_to_note(new_idx, prefer_flat=prefer_flat)


def _transpose_chord(chord: str, semitones: int) -> str:
    match = _ROOT_RE.match(chord.strip())
    if not match:
        return chord
    root, suffix = match.group(1), match.group(2)
    return _transpose_root(root, semitones) + suffix


def _transpose_token(token_inner: str, semitones: int) -> str:
    parts = [p.strip() for p in token_inner.split(",")]
    transposed = [_transpose_chord(p, semitones) for p in parts]
    return ",".join(transposed)


def _interval(from_note: str, to_note: str) -> int:
    return (_note_to_index(to_note) - _note_to_index(from_note)) % 12


class ChordTransposer:
    def __init__(
        self,
        plain_lyrics: str,
        original_tone: str,
        current_tone: str,
        transport: str,
    ) -> None:
        self.plain_lyrics = plain_lyrics
        self.original_tone = original_tone
        self.current_tone = current_tone
        self.transport = transport

    def transpose(self) -> str:
        delta = TRANSPORT_SEMITONES[self.transport]
        # Total offset from the stored (original) chords to the new desired key
        offset = (_interval(self.original_tone, self.current_tone) + delta) % 12
        if offset == 0:
            return self.plain_lyrics

        def replace_token(match: re.Match[str]) -> str:
            return "{" + _transpose_token(match.group(1), offset) + "}"

        return _CHORD_TOKEN_RE.sub(replace_token, self.plain_lyrics)
