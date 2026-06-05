# Lyrics Editor — Implementation Reference

This document describes how the lyrics editor format is parsed, stored, and rendered by the API.

---

## Overview

Songs are stored as raw plain text (`plain_lyrics` field) using a Markdown-inspired format.
The API parses this text at response time and returns structured JSON — the raw text is never
modified by the server after creation.

---

## Format Specification

### Frontmatter

Every lyrics document must begin with a YAML-like frontmatter block delimited by `---`:

```text
---
tone: G
guitar_capo: false
---
```

**Rules:**
- The frontmatter **must** appear at the very beginning of the document.
- `tone` is **required**. Valid values are the 17 standard note names:
  `C`, `C#`, `Db`, `D`, `D#`, `Eb`, `E`, `F`, `F#`, `Gb`, `G`, `G#`, `Ab`, `A`, `A#`, `Bb`, `B`
- `guitar_capo` is optional (defaults to `false`). Only `true` or `false` are accepted.

**Validation errors:**
- Missing frontmatter → `"Lyric frontmatter is missing. Add '---\ntone: <note>\n---' at the top."`
- Missing or invalid tone → `"Lyric Tone is invalid. Please use a valid tone."`

These errors are raised as `ValidationError` by `CreateSongSerializer.validate_lyrics()`.

---

### Section Markers

The body of the document is divided into sections using bracket markers in lowercase:

```text
[verse]
[chorus]
[bridge]
```

Content following a marker belongs to that section until the next marker or end of file.
Text before the first marker is ignored. All three markers are optional.

---

### Chord Annotations

Chords are written inline using curly braces: `{G}`, `{Em}`, `{C#m7}`.  
Multiple chords on one position are comma-separated: `{Em,A,C,D}`.

**Chord-only lines** — lines where every non-whitespace token is a chord annotation — are
treated as positioning guides. The parser uses them for the `chords` output but strips them
entirely from the `lyric` (no-chord) output.

**Example input:**
```text
[verse]
     {G}                   {D}
Porque eres la razón de mi vida
 {C}      {D}        {G}
Mi fuerza consuelo y alegría
```

---

## API Response Structure

The `lyrics` field in the Song payload is computed from `plain_lyrics` at serialisation time:

```json
{
  "lyrics": {
    "lyric": [
      {
        "type": "verse",
        "content": "Porque eres la razón de mi vida\nMi fuerza consuelo y alegría"
      }
    ],
    "chords": [
      {
        "type": "verse",
        "content": "     G                    D\nPorque eres la razón de mi vida\n C       D          G\nMi fuerza consuelo y alegría"
      }
    ]
  }
}
```

- `lyric` — lyrics only, all chord annotations removed.
- `chords` — chord annotations converted from `{G}` to `G`, positions preserved.
  Multi-chord tokens like `{Em,A,C,D}` become `Em  A  C  D` (double-space separated).

The `plain_lyrics` field is also returned verbatim so clients can re-render or edit it.

---

## Chord Transposition

### Algorithm

The transposer works on the raw `plain_lyrics` string, modifying only the `{chord}` tokens
while leaving all whitespace and text intact. This ensures the chord positioning is preserved
after transposition.

**Chromatic scale (sharps):**
```
C  C#  D  D#  E  F  F#  G  G#  A  A#  B
0   1  2   3  4  5   6  7   8  9  10  11
```

Flat spellings (`Db`, `Eb`, `Gb`, `Ab`, `Bb`) are mapped to their sharp equivalent for index
lookup, then converted back to flats in the output if the original root used a flat.

**Transposition steps:**

1. Determine delta: `semi_tone` = 1 semitone, `tone` = 2 semitones.
2. Calculate total offset from stored chords:
   `offset = (interval(original_tone → current_tone) + delta) mod 12`
3. For each `{...}` token in `plain_lyrics`:
   - Split on `,` to handle multi-chord tokens.
   - For each chord, extract the root (1–2 chars: letter + optional `#` or `b`).
   - Shift the root by `offset` semitones on the chromatic scale.
   - Re-attach the quality suffix (e.g. `m`, `maj7`, `7`, `m7`).
4. Return the modified plain_lyrics string.

**Example:**
```
original_tone = "G", current_tone = "G", transport = "semi_tone"
offset = (0 + 1) = 1

{G}  → index 7 + 1 = 8 → G#
{D}  → index 5 + 1 = 6 → D# (but Eb display if source was flat — here D# is returned)
{Em} → root E (index 4) + 1 = 5 → Fm
```

### Transport endpoint

```
POST /api/v1/songs/{id}/transport
```

Payload:
```json
{
  "transport": "semi_tone",
  "current_tone": "G",
  "original_tone": "G"
}
```

- `transport`: `"semi_tone"` (+1 semitone) or `"tone"` (+2 semitones).
- `current_tone`: the tone the song is currently displayed in (client-side state).
- `original_tone`: the song's stored original tone (from `song.tone`).

The endpoint does **not** modify the stored `plain_lyrics`. It returns the full Song payload
with `lyrics.chords` transposed in place. The `plain_lyrics` field in the response still
shows the original stored text.

---

## Implementation Files

| File | Responsibility |
|------|---------------|
| `cc/songs/lyrics/parser.py` | `LyricsParser` — parses raw text into structured `{lyric, chords}` |
| `cc/songs/lyrics/transport.py` | `ChordTransposer` — transposes chord tokens in raw text |
| `cc/songs/api/serializers.py` | `SongSerializer.get_lyrics()` calls `LyricsParser` at serialisation time |
| `cc/songs/api/views.py` | `SongViewSet.transport()` calls `ChordTransposer` then re-serialises |
| `cc/songs/services.py` | `CreateSongService` calls `LyricsParser` to extract tone on creation |

---

## Testing

Unit tests for the parser and transposer live in `cc/songs/tests/test_lyrics_parser.py`.
They cover:
- Valid parse → correct section types and content
- Frontmatter missing / invalid tone → `ValueError`
- Chord-only line stripping
- Multi-chord token expansion
- Semitone and full-tone transposition
- Transposition with a non-zero `current_tone` offset
- 12-semitone wrap (chromatic identity)
