from __future__ import annotations

from django.utils.text import slugify
from factory import Faker
from factory import LazyAttribute
from factory import LazyFunction
from factory import Sequence
from factory import SubFactory
from factory import post_generation
from factory.django import DjangoModelFactory

from cc.songs.lyrics.parser import LyricsParser
from cc.songs.models import Author
from cc.songs.models import Song
from cc.songs.models import Tag
from cc.songs.services import sync_song_verses
from cc.users.tests.factories import UserFactory

_PLAIN_LYRICS = """\
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
      {D}        {D}              {G}
Sacerdote para siempre quiero ser
"""


class TagFactory(DjangoModelFactory[Tag]):
    name = Sequence(lambda n: f"tag-{n}")
    slug = LazyAttribute(lambda obj: slugify(obj.name))
    parent = None

    class Meta:
        model = Tag


class AuthorFactory(DjangoModelFactory[Author]):
    name = Faker("name")
    image = ""
    bio = ""
    slug = ""

    class Meta:
        model = Author


class SongFactory(DjangoModelFactory[Song]):
    name = Faker("sentence", nb_words=4)
    slug = Sequence(lambda n: f"song-{n}")
    plain_lyrics = LazyFunction(lambda: _PLAIN_LYRICS)
    tone = "G"
    is_public = False
    created_by = SubFactory(UserFactory)

    class Meta:
        model = Song
        skip_postgeneration_save = True

    @post_generation
    def _verses(self, create: bool, extracted: object, **kwargs: object) -> None:  # noqa: FBT001
        if not create:
            return
        try:
            parsed = LyricsParser(self.plain_lyrics).parse()
            sync_song_verses(self, parsed)
        except ValueError:
            pass
