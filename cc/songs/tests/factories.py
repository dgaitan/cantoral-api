from __future__ import annotations

from factory import Faker
from factory import LazyFunction
from factory import SubFactory
from factory.django import DjangoModelFactory

from cc.songs.models import Author
from cc.songs.models import Song
from cc.songs.models import Tag
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
    name = Faker("word")

    class Meta:
        model = Tag
        django_get_or_create = ["name"]


class AuthorFactory(DjangoModelFactory[Author]):
    name = Faker("name")
    image = ""
    bio = ""
    slug = ""

    class Meta:
        model = Author


class SongFactory(DjangoModelFactory[Song]):
    name = Faker("sentence", nb_words=4)
    plain_lyrics = LazyFunction(lambda: _PLAIN_LYRICS)
    tone = "G"
    is_public = False
    created_by = SubFactory(UserFactory)

    class Meta:
        model = Song
