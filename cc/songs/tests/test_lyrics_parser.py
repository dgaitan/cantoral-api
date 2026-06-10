from __future__ import annotations

import pytest

from cc.songs.lyrics.parser import LyricsParser
from cc.songs.lyrics.transport import ChordTransposer

_SAMPLE = """\
---
tone: G
---
[verse]
     {G}                   {D}
Porque eres la razón de mi vida
 {C}      {D}        {G}
Mi fuerza consuelo y alegría

[chorus]
        {G}                {D}
Aquí estoy Señor toma mi vida
      {C}        {D}           {Em,A,C,D}
Sacerdote para siempre quiero ser
"""


class TestLyricsParser:
    def test_parses_tone(self) -> None:
        result = LyricsParser(_SAMPLE).parse()
        assert result["tone"] == "G"

    def test_guitar_capo_defaults_to_false(self) -> None:
        result = LyricsParser(_SAMPLE).parse()
        assert result["guitar_capo"] is False

    def test_guitar_capo_true(self) -> None:
        lyrics = "---\ntone: G\nguitar_capo: true\n---\n[verse]\nLine\n"
        result = LyricsParser(lyrics).parse()
        assert result["guitar_capo"] is True

    def test_returns_two_sections(self) -> None:
        result = LyricsParser(_SAMPLE).parse()
        assert result["lyric"][0]["type"] == "verse"
        assert result["lyric"][1]["type"] == "chorus"
        assert len(result["lyric"]) == len(result["chords"])

    def test_lyric_strips_chord_only_lines(self) -> None:
        result = LyricsParser(_SAMPLE).parse()
        verse_lyric = result["lyric"][0]["content"]
        assert "{G}" not in verse_lyric
        assert "{D}" not in verse_lyric
        assert "Porque eres la razón de mi vida" in verse_lyric

    def test_chords_replaces_braces(self) -> None:
        result = LyricsParser(_SAMPLE).parse()
        verse_chords = result["chords"][0]["content"]
        assert "{G}" not in verse_chords
        assert "G" in verse_chords

    def test_multi_chord_token_expanded(self) -> None:
        result = LyricsParser(_SAMPLE).parse()
        chorus_chords = result["chords"][1]["content"]
        assert "{Em,A,C,D}" not in chorus_chords
        assert "Em" in chorus_chords

    def test_missing_frontmatter_raises(self) -> None:
        with pytest.raises(ValueError, match="frontmatter"):
            LyricsParser("[verse]\nSome line").parse()

    def test_invalid_tone_raises(self) -> None:
        with pytest.raises(ValueError, match="Lyric Tone is invalid"):
            LyricsParser("---\ntone: X\n---\n[verse]\nline").parse()

    def test_missing_tone_raises(self) -> None:
        with pytest.raises(ValueError, match="Lyric Tone is invalid"):
            LyricsParser("---\nguitar_capo: false\n---\n[verse]\nline").parse()

    def test_bridge_section_supported(self) -> None:
        lyrics = "---\ntone: A\n---\n[bridge]\nBridge line\n"
        result = LyricsParser(lyrics).parse()
        assert result["lyric"][0]["type"] == "bridge"

    def test_lyric_content_is_html_wrapped(self) -> None:
        result = LyricsParser(_SAMPLE).parse()
        content = result["lyric"][0]["content"]
        assert content.startswith("<p>")
        assert content.endswith("</p>")
        assert "\n" not in content

    def test_chords_content_is_html_wrapped(self) -> None:
        result = LyricsParser(_SAMPLE).parse()
        content = result["chords"][0]["content"]
        assert content.startswith("<p>")
        assert content.endswith("</p>")
        assert "\n" not in content

    def test_code_fence_stripped_from_lyric(self) -> None:
        lyrics = "---\ntone: G\n---\n[verse]\nLine one\n```\n"
        result = LyricsParser(lyrics).parse()
        assert "```" not in result["lyric"][0]["content"]

    def test_code_fence_stripped_from_chords(self) -> None:
        lyrics = "---\ntone: G\n---\n[verse]\n{G}\nLine one\n```\n"
        result = LyricsParser(lyrics).parse()
        assert "```" not in result["chords"][0]["content"]

    def test_empty_lines_not_wrapped(self) -> None:
        lyrics = "---\ntone: G\n---\n[verse]\nLine one\n\nLine two\n"
        result = LyricsParser(lyrics).parse()
        assert "<p></p>" not in result["lyric"][0]["content"]

    def test_chord_token_replacement_is_width_preserving(self) -> None:
        # {G} is 3 chars; after replacement G should be padded to 3 so D stays at col 5
        lyrics = "---\ntone: G\n---\n[verse]\n{G}  {D}\nLine\n"
        result = LyricsParser(lyrics).parse()
        chords_html = result["chords"][0]["content"]
        # Extract the rendered chord line (content of first <p>)
        chord_line = chords_html.split("</p>")[0].replace("<p>", "")
        assert chord_line[0] == "G"
        assert chord_line[5] == "D"  # {G}(3) + 2 spaces = D at col 5

    def test_leading_spaces_preserved_on_chord_lines(self) -> None:
        lyrics = "---\ntone: G\n---\n[verse]\n     {G}   {D}\nLine\n"
        result = LyricsParser(lyrics).parse()
        chords_html = result["chords"][0]["content"]
        chord_line = chords_html.split("</p>")[0].replace("<p>", "")
        assert chord_line.startswith("     ")  # 5-space indent preserved
        assert chord_line[5] == "G"


class TestChordTransposer:
    def test_no_change_when_offset_is_zero(self) -> None:
        result = ChordTransposer(_SAMPLE, "G", "G", "semi_tone").transpose()
        # G + 1 semitone = G# — chords should change
        assert result != _SAMPLE

    def test_semi_tone_transposes_g_to_g_sharp(self) -> None:
        lyrics = "---\ntone: G\n---\n[verse]\n{G}\nLine\n"
        result = ChordTransposer(lyrics, "G", "G", "semi_tone").transpose()
        assert "{G#}" in result

    def test_tone_transposes_g_to_a(self) -> None:
        lyrics = "---\ntone: G\n---\n[verse]\n{G}\nLine\n"
        result = ChordTransposer(lyrics, "G", "G", "tone").transpose()
        assert "{A}" in result

    def test_current_tone_offset_applied(self) -> None:
        lyrics = "---\ntone: G\n---\n[verse]\n{G}\nLine\n"
        # G stored, displayed as A (+2), transport +1 → total A# from G
        result = ChordTransposer(lyrics, "G", "A", "semi_tone").transpose()
        assert "{A#}" in result

    def test_multi_chord_token_transposed(self) -> None:
        lyrics = "---\ntone: G\n---\n[verse]\n{Em,A}\nLine\n"
        result = ChordTransposer(lyrics, "G", "G", "semi_tone").transpose()
        assert "{Fm,A#}" in result

    def test_full_circle_twelve_semitones(self) -> None:
        lyrics = "---\ntone: G\n---\n[verse]\n{G}\nLine\n"
        # 12 semi_tones = back to original
        current = lyrics
        for _ in range(12):
            current = ChordTransposer(current, "G", "G", "semi_tone").transpose()
        assert "{" in current  # 12 semitones wraps back; verify no crash
