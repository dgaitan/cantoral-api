from __future__ import annotations

from rest_framework import serializers

from cc.songs.lyrics.parser import VALID_TONES
from cc.songs.lyrics.parser import LyricsParser
from cc.songs.models import Author
from cc.songs.models import Song
from cc.songs.models import Tag
from cc.utils.mixins import SlugAutoGenerateMixin


class TagSerializer(serializers.ModelSerializer[Tag]):
    class Meta:
        model = Tag
        fields = ["id", "name", "slug", "parent_id"]


class TagWriteSerializer(SlugAutoGenerateMixin, serializers.ModelSerializer[Tag]):
    slug = serializers.SlugField(required=False, allow_blank=True, default="", max_length=255)
    parent_id = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        source="parent",
        allow_null=True,
        required=False,
    )

    class Meta:
        model = Tag
        fields = ["name", "slug", "parent_id"]

    def validate(self, data: dict) -> dict:
        data = super().validate(data)
        slug = data.get("slug")
        if slug:
            qs = Tag.objects.filter(slug=slug)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({"slug": "Tag with this slug already exists."})
        return data


class AuthorSerializer(serializers.ModelSerializer[Author]):
    class Meta:
        model = Author
        fields = ["id", "name", "image", "bio", "slug"]


class AuthorWriteSerializer(SlugAutoGenerateMixin, serializers.ModelSerializer[Author]):
    slug = serializers.SlugField(required=False, allow_blank=True, default="", max_length=255)

    class Meta:
        model = Author
        fields = ["name", "image", "bio", "slug"]


class SongSerializer(serializers.ModelSerializer[Song]):
    tags = TagSerializer(many=True, read_only=True)
    authors = AuthorSerializer(many=True, read_only=True)
    lyrics = serializers.SerializerMethodField()

    class Meta:
        model = Song
        fields = [
            "id",
            "slug",
            "name",
            "views",
            "tags",
            "authors",
            "plain_lyrics",
            "tone",
            "is_public",
            "lyrics",
        ]

    def get_lyrics(self, obj: Song) -> dict:
        plain = self.context.get("override_plain_lyrics", obj.plain_lyrics)
        try:
            parsed = LyricsParser(plain).parse()
        except ValueError:
            return {"lyric": [], "chords": []}
        return {"lyric": parsed["lyric"], "chords": parsed["chords"]}


class SongWriteSerializer(SlugAutoGenerateMixin, serializers.Serializer):
    name = serializers.CharField(min_length=1, max_length=255)
    slug = serializers.SlugField(required=False, allow_blank=True, default="", max_length=255)
    authors = serializers.ListField(child=serializers.IntegerField(), min_length=1)
    tags = serializers.ListField(
        child=serializers.IntegerField(), required=False, default=list,
    )
    lyrics = serializers.CharField()

    def validate_lyrics(self, value: str) -> str:
        try:
            LyricsParser(value).parse()
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc
        return value

    def validate_authors(self, value: list[int]) -> list[int]:
        existing = set(Author.objects.filter(pk__in=value).values_list("pk", flat=True))
        missing = [pk for pk in value if pk not in existing]
        if missing:
            msg = f"Authors with ids {missing} do not exist."
            raise serializers.ValidationError(msg)
        return value

    def validate_tags(self, value: list[int]) -> list[int]:
        if not value:
            return value
        existing = set(Tag.objects.filter(pk__in=value).values_list("pk", flat=True))
        missing = [pk for pk in value if pk not in existing]
        if missing:
            msg = f"Tags with ids {missing} do not exist."
            raise serializers.ValidationError(msg)
        return value


CreateSongSerializer = SongWriteSerializer


class TransportSerializer(serializers.Serializer):
    transport = serializers.ChoiceField(choices=["semi_tone", "tone"])
    current_tone = serializers.CharField()
    original_tone = serializers.CharField()

    def validate_current_tone(self, value: str) -> str:
        if value not in VALID_TONES:
            msg = "Lyric Tone is invalid. Please use a valid tone."
            raise serializers.ValidationError(msg)
        return value

    def validate_original_tone(self, value: str) -> str:
        if value not in VALID_TONES:
            msg = "Lyric Tone is invalid. Please use a valid tone."
            raise serializers.ValidationError(msg)
        return value
