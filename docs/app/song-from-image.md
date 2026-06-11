# Song from chord-sheet image

Extract lyrics and chords from a chord-sheet image URL and create a draft `Song` for human review in the Django admin.

## Overview

The admin **Extract from image** flow:

1. Paste a public image URL (for example an S3 chord sheet).
2. Claude vision reads the image and returns JSON with `name` and `plain_lyrics`.
3. `LyricsParser` validates the extracted text.
4. A draft song (`is_public=False`) is created with parsed `Verse` rows.
5. The source image URL is stored on the song as `source_image_url`.

## Admin usage

1. Open **Songs** in Django admin.
2. Click **Extract from image** in the object tools bar.
3. Enter the image URL and optionally override the song name.
4. Submit. On success you are redirected to the new draft song change page.

Example input URL:

```text
https://cancionero-catolico.s3.amazonaws.com/songs_chords/01JPJBFA3K50GN55J0CM4RSWPJ.jpg
```

## Configuration

Set these environment variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | Yes | *(empty)* | Anthropic API key for vision extraction |
| `ANTHROPIC_VISION_MODEL` | No | `claude-sonnet-4-5` | Model used for chord-sheet transcription |

## Extraction contract

Claude must return **only JSON**:

```json
{
  "name": "Song title",
  "plain_lyrics": "..."
}
```

The `plain_lyrics` value must follow the lyrics editor format documented in [lyrics-editor-implementation.md](./lyrics-editor-implementation.md):

- Frontmatter with required `tone` (valid note name).
- Section markers: `[verse]`, `[chorus]`, `[bridge]`.
- Inline chords as `{G}`, `{Em}`, etc., aligned above lyric lines.
- Multiple chords at one position: `{Em,A,C,D}`.

The prompt lives in `cc/songs/extraction.py` (`_EXTRACTION_PROMPT`).

## Implementation files

| File | Responsibility |
|------|----------------|
| `cc/songs/extraction.py` | `ChordSheetExtractor` — Claude vision call + JSON parsing |
| `cc/songs/services.py` | `CreateSongFromImageService` — extract, validate, create draft song |
| `cc/songs/admin.py` | Admin form, custom view, changelist button |
| `cc/songs/models.py` | `Song.source_image_url` provenance field |
| `cc/templates/admin/songs/song/` | Admin templates for changelist button and extract form |

## Tests

```bash
uv run pytest cc/songs/tests/test_extraction.py
```

Tests mock the Anthropic client; no live API calls are made in CI.

## Notes

- Extraction runs synchronously in the admin request (acceptable for low-volume admin use).
- Songs are always created as drafts; publish separately when reviewed.
- Supported image types for Claude vision: JPEG, PNG, GIF, WebP.
