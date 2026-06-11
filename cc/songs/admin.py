from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, cast

from django import forms
from django.conf import settings as django_settings
from django.contrib import admin, messages
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils.safestring import mark_safe
from django.utils.text import slugify

from cc.songs.extraction import AGENT_CHOICES
from cc.songs.lyrics.parser import LyricsParser
from cc.songs.models import Author, Song, Tag, Verse
from cc.songs.services import CreateSongFromImageService, sync_song_verses

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse

    from cc.users.models import User


class LyricsEditorWidget(forms.Textarea):
    """CodeMirror editor for the plain_lyrics format."""

    class Media:
        css = {
            "all": [
                "https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/codemirror.min.css",
                "https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/theme/dracula.min.css",
            ],
        }
        js = [
            "https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/codemirror.min.js",
        ]

    def render(
        self,
        name: str,
        value: Any,
        attrs: dict[str, Any] | None = None,
        renderer: Any = None,
    ) -> str:
        base_html = super().render(name, value, attrs, renderer)
        safe_name = json.dumps(name)
        extra = f"""<style>
.CodeMirror {{ height: auto; min-height: 450px; }}
.CodeMirror {{ font-family: monospace; font-size: 13px; }}
</style>
<script>
document.addEventListener('DOMContentLoaded', function() {{
  var ta = document.querySelector('textarea[name=' + {safe_name} + ']');
  if (!ta) return;
  var editor = CodeMirror.fromTextArea(ta, {{
    lineNumbers: true,
    theme: 'dracula',
    mode: 'text/plain',
    lineWrapping: false,
    indentUnit: 2,
    tabSize: 2,
    viewportMargin: Infinity
  }});
  editor.on('change', function() {{ editor.save(); }});
}});
</script>"""
        return mark_safe(str(base_html) + extra)  # noqa: S308


class VerseInline(admin.TabularInline):  # type: ignore[type-arg]
    model = Verse
    extra = 0
    readonly_fields = ["type", "order", "lyrics_html", "chords_preview"]
    can_delete = False

    def has_add_permission(self, request: HttpRequest, obj: Song | None = None) -> bool:  # type: ignore[override]
        return False

    def chords_preview(self, obj: Verse) -> str:
        text = obj.chords_html.replace("</p>", "\n").replace("<p>", "")
        style = "font-family:monospace;font-size:12px;margin:0;white-space:pre"
        return mark_safe(f'<pre style="{style}">{text.strip(chr(10))}</pre>')  # noqa: S308

    chords_preview.short_description = "Chords"  # type: ignore[attr-defined]


class SongAdminForm(forms.ModelForm):  # type: ignore[type-arg]
    class Meta:
        model = Song
        fields = ["name", "slug", "is_public", "authors", "tags", "plain_lyrics"]
        widgets = {
            "plain_lyrics": LyricsEditorWidget(attrs={"rows": 30}),
        }

    def clean_plain_lyrics(self) -> str:
        value: str = self.cleaned_data.get("plain_lyrics", "")
        try:
            LyricsParser(value).parse()
        except ValueError as exc:
            raise forms.ValidationError(str(exc)) from exc
        return value


class ExtractSongFromImageForm(forms.Form):
    image_url = forms.URLField(
        label="Image URL",
        help_text="Public URL to a chord sheet image (JPEG, PNG, GIF, or WebP).",
    )
    name = forms.CharField(
        label="Song name (optional)",
        required=False,
        max_length=255,
        help_text="Override the title extracted from the image.",
    )
    agent = forms.ChoiceField(
        label="Extraction agent",
        choices=AGENT_CHOICES,
        help_text="Vision model to use for chord-sheet extraction.",
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["agent"].initial = django_settings.CHORD_EXTRACTION_DEFAULT_AGENT


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ["id", "name", "slug", "parent"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ["id", "name", "slug"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Song)
class SongAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    form = SongAdminForm
    change_list_template = "admin/songs/song/change_list.html"
    inlines = [VerseInline]
    list_display = ["id", "name", "tone", "is_public", "created_by", "created_at"]
    list_filter = ["is_public", "tone"]
    search_fields = ["name"]
    autocomplete_fields = ["tags", "authors"]
    readonly_fields = [
        "tone",
        "views",
        "source_image_url",
        "created_by",
        "created_at",
        "updated_at",
    ]
    prepopulated_fields = {"slug": ("name",)}
    fieldsets = [
        (
            None,
            {"fields": ["name", "slug", "is_public"]},
        ),
        (
            "Authors & Tags",
            {"fields": ["authors", "tags"]},
        ),
        (
            "Lyrics",
            {"fields": ["plain_lyrics"]},
        ),
        (
            "Metadata",
            {
                "fields": [
                    "tone",
                    "source_image_url",
                    "views",
                    "created_by",
                    "created_at",
                    "updated_at",
                ],
                "classes": ["collapse"],
            },
        ),
    ]

    def get_urls(self) -> list:
        urls = super().get_urls()
        custom_urls = [
            path(
                "extract-from-image/",
                self.admin_site.admin_view(self.extract_from_image_view),
                name="songs_song_extract_from_image",
            ),
        ]
        return custom_urls + urls

    def extract_from_image_view(self, request: HttpRequest) -> HttpResponse:
        form = ExtractSongFromImageForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            try:
                song = CreateSongFromImageService(
                    user=cast("User", request.user),
                    image_url=form.cleaned_data["image_url"],
                    name=form.cleaned_data.get("name", ""),
                    agent=form.cleaned_data["agent"],
                ).dispatch()
            except ValueError as exc:
                messages.error(request, str(exc))
            else:
                messages.success(
                    request,
                    f'Draft song "{song.name}" was created from the image.',
                )
                return redirect(
                    reverse("admin:songs_song_change", args=[song.pk]),
                )
        context = {
            **self.admin_site.each_context(request),
            "form": form,
            "opts": self.opts,
            "title": "Extract song from image",
        }
        return render(
            request,
            "admin/songs/song/extract_from_image.html",
            context,
        )

    def save_model(
        self,
        request: HttpRequest,
        obj: Song,
        form: forms.ModelForm,  # type: ignore[type-arg]
        change: bool,  # noqa: FBT001
    ) -> None:
        if not change:
            obj.created_by = request.user  # type: ignore[assignment]
        plain = form.cleaned_data.get("plain_lyrics", obj.plain_lyrics)
        parsed = LyricsParser(plain).parse()
        obj.tone = parsed["tone"]
        if not obj.slug:
            obj.slug = slugify(obj.name)
        super().save_model(request, obj, form, change)
        sync_song_verses(obj, parsed)
