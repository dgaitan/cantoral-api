from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from anthropic.types import TextBlock
from django.test import override_settings

from cc.songs.extraction import (
    AnthropicAgent,
    ChordSheetExtractor,
    GeminiAgent,
    get_agent,
    parse_extraction_response,
)
from cc.songs.models import Song
from cc.songs.services import CreateSongFromImageService
from cc.songs.tests.factories import AuthorFactory, SongFactory, TagFactory, UserFactory

_VALID_PLAIN_LYRICS = """\
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
"""

_EXPECTED_SECTION_COUNT = 2

_VALID_RESPONSE_JSON = (
    '{"name": "Mi Canción", "plain_lyrics": '
    '"---\\ntone: G\\n---\\n[verse]\\n     {G}\\nLine one\\n"}'
)


# ---------------------------------------------------------------------------
# parse_extraction_response
# ---------------------------------------------------------------------------


class TestParseExtractionResponse:
    def test_parses_valid_json(self) -> None:
        payload = (
            '{"name": "Test Song", "plain_lyrics": '
            '"---\\ntone: G\\n---\\n[verse]\\nLine\\n"}'
        )
        result = parse_extraction_response(payload)
        assert result["name"] == "Test Song"
        assert "tone: G" in result["plain_lyrics"]

    def test_parses_fenced_json(self) -> None:
        payload = (
            '```json\n{"name": "Test", "plain_lyrics": "---\\ntone: G\\n---\\n"}\n```'
        )
        result = parse_extraction_response(payload)
        assert result["name"] == "Test"

    def test_invalid_json_raises(self) -> None:
        with pytest.raises(ValueError, match="Could not parse extraction response"):
            parse_extraction_response("not json")

    def test_missing_name_raises(self) -> None:
        with pytest.raises(ValueError, match="missing a valid song name"):
            parse_extraction_response('{"plain_lyrics": "x"}')

    def test_missing_plain_lyrics_raises(self) -> None:
        with pytest.raises(ValueError, match="missing valid plain_lyrics"):
            parse_extraction_response('{"name": "Test"}')


# ---------------------------------------------------------------------------
# AnthropicAgent
# ---------------------------------------------------------------------------


class TestAnthropicAgent:
    @override_settings(ANTHROPIC_API_KEY="")
    def test_missing_api_key_raises(self) -> None:
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY is not configured"):
            AnthropicAgent().generate("prompt", "https://example.com/img.jpg")

    @override_settings(ANTHROPIC_API_KEY="test-key")
    @patch("cc.songs.extraction.agents.Anthropic")
    def test_returns_text_from_response(self, mock_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        block = TextBlock(type="text", text=_VALID_RESPONSE_JSON)
        mock_client.messages.create.return_value = MagicMock(content=[block])

        result = AnthropicAgent().generate("prompt", "https://example.com/img.jpg")

        assert result == _VALID_RESPONSE_JSON
        call_kwargs = mock_client.messages.create.call_args.kwargs
        image_block = call_kwargs["messages"][0]["content"][1]
        assert image_block["source"]["type"] == "url"
        assert image_block["source"]["url"] == "https://example.com/img.jpg"

    @override_settings(ANTHROPIC_API_KEY="test-key")
    @patch("cc.songs.extraction.agents.Anthropic")
    def test_empty_content_raises(self, mock_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.return_value = MagicMock(content=[])

        with pytest.raises(ValueError, match="did not contain text content"):
            AnthropicAgent().generate("prompt", "https://example.com/img.jpg")


# ---------------------------------------------------------------------------
# GeminiAgent
# ---------------------------------------------------------------------------


class TestGeminiAgent:
    @override_settings(GEMINI_API_KEY="")
    def test_missing_api_key_raises(self) -> None:
        with pytest.raises(ValueError, match="GEMINI_API_KEY is not configured"):
            GeminiAgent().generate("prompt", "https://example.com/img.jpg")

    @override_settings(GEMINI_API_KEY="test-key")
    @patch(
        "cc.songs.extraction.agents._download_image",
        return_value=(b"data", "image/jpeg"),
    )
    @patch("cc.songs.extraction.agents.genai")
    @patch("cc.songs.extraction.agents.types")
    def test_returns_text_from_response(
        self,
        mock_types: MagicMock,
        mock_genai: MagicMock,
        mock_download: MagicMock,
    ) -> None:
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_part = MagicMock()
        mock_types.Part.from_bytes.return_value = mock_part
        mock_client.models.generate_content.return_value = MagicMock(
            text=_VALID_RESPONSE_JSON,
        )

        result = GeminiAgent().generate("prompt", "https://example.com/img.jpg")

        assert result == _VALID_RESPONSE_JSON
        mock_download.assert_called_once_with("https://example.com/img.jpg")
        mock_types.Part.from_bytes.assert_called_once_with(
            data=b"data",
            mime_type="image/jpeg",
        )
        call_kwargs = mock_client.models.generate_content.call_args.kwargs
        assert call_kwargs["contents"] == ["prompt", mock_part]


# ---------------------------------------------------------------------------
# Agent manager
# ---------------------------------------------------------------------------


class TestAgentManager:
    def test_get_anthropic_agent(self) -> None:
        agent = get_agent("anthropic")
        assert isinstance(agent, AnthropicAgent)

    def test_get_gemini_agent(self) -> None:
        agent = get_agent("gemini")
        assert isinstance(agent, GeminiAgent)

    def test_unknown_agent_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown extraction agent"):
            get_agent("openai")


# ---------------------------------------------------------------------------
# ChordSheetExtractor — agnostic
# ---------------------------------------------------------------------------


class TestChordSheetExtractor:
    def test_delegates_to_agent_and_parses(self) -> None:
        stub_agent = MagicMock()
        stub_agent.generate.return_value = (
            '{"name": "Test", '
            '"plain_lyrics": "---\\ntone: G\\n---\\n[verse]\\nLine\\n"}'
        )
        result = ChordSheetExtractor(
            "https://example.com/img.jpg",
            stub_agent,
        ).extract()

        assert result["name"] == "Test"
        assert "tone: G" in result["plain_lyrics"]
        stub_agent.generate.assert_called_once()
        prompt_arg, url_arg, *_ = stub_agent.generate.call_args.args
        assert url_arg == "https://example.com/img.jpg"
        assert "chord" in prompt_arg.lower()

    def test_propagates_agent_error(self) -> None:
        stub_agent = MagicMock()
        stub_agent.generate.side_effect = ValueError("API key missing")
        with pytest.raises(ValueError, match="API key missing"):
            ChordSheetExtractor("https://example.com/img.jpg", stub_agent).extract()


# ---------------------------------------------------------------------------
# CreateSongFromImageService
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCreateSongFromImageService:
    @patch("cc.songs.services.get_agent")
    @patch("cc.songs.services.ChordSheetExtractor")
    def test_creates_draft_song_with_verses(
        self,
        mock_extractor_cls: MagicMock,
        mock_get_agent: MagicMock,
    ) -> None:
        user = UserFactory()
        mock_agent = MagicMock()
        mock_get_agent.return_value = mock_agent
        mock_extractor_cls.return_value.extract.return_value = {
            "name": "Extracted Song",
            "plain_lyrics": _VALID_PLAIN_LYRICS,
        }
        image_url = "https://example.com/sheet.jpg"

        song = CreateSongFromImageService(
            user=user,
            image_url=image_url,
        ).dispatch()

        assert song.name == "Extracted Song"
        assert song.is_public is False
        assert song.tone == "G"
        assert song.source_image_url == image_url
        assert song.verses.count() == _EXPECTED_SECTION_COUNT
        mock_extractor_cls.assert_called_once_with(image_url, mock_agent, None)

    @patch("cc.songs.services.get_agent")
    @patch("cc.songs.services.ChordSheetExtractor")
    def test_uses_specified_agent(
        self,
        mock_extractor_cls: MagicMock,
        mock_get_agent: MagicMock,
    ) -> None:
        user = UserFactory()
        mock_get_agent.return_value = MagicMock()
        mock_extractor_cls.return_value.extract.return_value = {
            "name": "Song",
            "plain_lyrics": _VALID_PLAIN_LYRICS,
        }

        CreateSongFromImageService(
            user=user,
            image_url="https://example.com/sheet.jpg",
            agent="gemini",
        ).dispatch()

        mock_get_agent.assert_called_once_with("gemini")

    @override_settings(CHORD_EXTRACTION_DEFAULT_AGENT="anthropic")
    @patch("cc.songs.services.get_agent")
    @patch("cc.songs.services.ChordSheetExtractor")
    def test_falls_back_to_settings_default(
        self,
        mock_extractor_cls: MagicMock,
        mock_get_agent: MagicMock,
    ) -> None:
        user = UserFactory()
        mock_get_agent.return_value = MagicMock()
        mock_extractor_cls.return_value.extract.return_value = {
            "name": "Song",
            "plain_lyrics": _VALID_PLAIN_LYRICS,
        }

        CreateSongFromImageService(
            user=user,
            image_url="https://example.com/sheet.jpg",
        ).dispatch()

        mock_get_agent.assert_called_once_with("anthropic")

    @patch("cc.songs.services.get_agent")
    @patch("cc.songs.services.ChordSheetExtractor")
    def test_name_override(
        self,
        mock_extractor_cls: MagicMock,
        mock_get_agent: MagicMock,
    ) -> None:
        user = UserFactory()
        mock_get_agent.return_value = MagicMock()
        mock_extractor_cls.return_value.extract.return_value = {
            "name": "Extracted Song",
            "plain_lyrics": _VALID_PLAIN_LYRICS,
        }

        song = CreateSongFromImageService(
            user=user,
            image_url="https://example.com/sheet.jpg",
            name="Custom Name",
        ).dispatch()

        assert song.name == "Custom Name"

    @patch("cc.songs.services.get_agent")
    @patch("cc.songs.services.ChordSheetExtractor")
    def test_invalid_plain_lyrics_raises(
        self,
        mock_extractor_cls: MagicMock,
        mock_get_agent: MagicMock,
    ) -> None:
        user = UserFactory()
        mock_get_agent.return_value = MagicMock()
        mock_extractor_cls.return_value.extract.return_value = {
            "name": "Bad Song",
            "plain_lyrics": "not valid lyrics",
        }

        with pytest.raises(ValueError, match="frontmatter"):
            CreateSongFromImageService(
                user=user,
                image_url="https://example.com/sheet.jpg",
            ).dispatch()

        assert Song.objects.count() == 0

    @patch("cc.songs.services.get_agent")
    @patch("cc.songs.services.ChordSheetExtractor")
    def test_updates_existing_song_when_song_provided(
        self,
        mock_extractor_cls: MagicMock,
        mock_get_agent: MagicMock,
    ) -> None:
        user = UserFactory()
        existing_song = SongFactory(name="Original Name")
        mock_get_agent.return_value = MagicMock()
        mock_extractor_cls.return_value.extract.return_value = {
            "name": "Extracted Song",
            "plain_lyrics": _VALID_PLAIN_LYRICS,
        }

        song = CreateSongFromImageService(
            user=user,
            image_url="https://example.com/sheet.jpg",
            song=existing_song,
        ).dispatch()

        assert Song.objects.count() == 1
        assert song.pk == existing_song.pk
        assert song.name == "Original Name"
        assert song.tone == "G"
        assert song.verses.count() == _EXPECTED_SECTION_COUNT

    @patch("cc.songs.services.get_agent")
    @patch("cc.songs.services.ChordSheetExtractor")
    def test_ignores_name_and_extracted_name_when_song_provided(
        self,
        mock_extractor_cls: MagicMock,
        mock_get_agent: MagicMock,
    ) -> None:
        user = UserFactory()
        existing_song = SongFactory(name="Original Name")
        mock_get_agent.return_value = MagicMock()
        mock_extractor_cls.return_value.extract.return_value = {
            "name": "Extracted Song",
            "plain_lyrics": _VALID_PLAIN_LYRICS,
        }

        song = CreateSongFromImageService(
            user=user,
            image_url="https://example.com/sheet.jpg",
            name="Some Override",
            song=existing_song,
        ).dispatch()

        assert song.name == "Original Name"

    @patch("cc.songs.services.get_agent")
    @patch("cc.songs.services.ChordSheetExtractor")
    def test_does_not_clear_authors_or_tags_when_song_provided(
        self,
        mock_extractor_cls: MagicMock,
        mock_get_agent: MagicMock,
    ) -> None:
        user = UserFactory()
        existing_song = SongFactory()
        author = AuthorFactory()
        tag = TagFactory()
        existing_song.authors.add(author)
        existing_song.tags.add(tag)
        mock_get_agent.return_value = MagicMock()
        mock_extractor_cls.return_value.extract.return_value = {
            "name": "Extracted Song",
            "plain_lyrics": _VALID_PLAIN_LYRICS,
        }

        song = CreateSongFromImageService(
            user=user,
            image_url="https://example.com/sheet.jpg",
            song=existing_song,
        ).dispatch()

        assert list(song.authors.all()) == [author]
        assert list(song.tags.all()) == [tag]

    @patch("cc.songs.services.get_agent")
    @patch("cc.songs.services.ChordSheetExtractor")
    def test_updates_source_image_url_when_song_provided(
        self,
        mock_extractor_cls: MagicMock,
        mock_get_agent: MagicMock,
    ) -> None:
        user = UserFactory()
        existing_song = SongFactory(source_image_url="https://example.com/old.jpg")
        mock_get_agent.return_value = MagicMock()
        mock_extractor_cls.return_value.extract.return_value = {
            "name": "Extracted Song",
            "plain_lyrics": _VALID_PLAIN_LYRICS,
        }
        image_url = "https://example.com/new.jpg"

        song = CreateSongFromImageService(
            user=user,
            image_url=image_url,
            song=existing_song,
        ).dispatch()

        assert song.source_image_url == image_url

    @patch("cc.songs.services.get_agent")
    @patch("cc.songs.services.ChordSheetExtractor")
    def test_invalid_plain_lyrics_raises_with_song_provided(
        self,
        mock_extractor_cls: MagicMock,
        mock_get_agent: MagicMock,
    ) -> None:
        user = UserFactory()
        existing_song = SongFactory()
        original_lyrics = existing_song.plain_lyrics
        mock_get_agent.return_value = MagicMock()
        mock_extractor_cls.return_value.extract.return_value = {
            "name": "Bad Song",
            "plain_lyrics": "not valid lyrics",
        }

        with pytest.raises(ValueError, match="frontmatter"):
            CreateSongFromImageService(
                user=user,
                image_url="https://example.com/sheet.jpg",
                song=existing_song,
            ).dispatch()

        existing_song.refresh_from_db()
        assert existing_song.plain_lyrics == original_lyrics
