from __future__ import annotations

from factory import Faker, SubFactory
from factory.django import DjangoModelFactory

from cc.playlists.models import Playlist, PlaylistSong
from cc.songs.tests.factories import SongFactory
from cc.users.tests.factories import UserFactory


class PlaylistFactory(DjangoModelFactory[Playlist]):
    name = Faker("sentence", nb_words=3)
    description = ""
    is_public = False
    is_collaborative = False
    owner = SubFactory(UserFactory)

    class Meta:
        model = Playlist


class PlaylistSongFactory(DjangoModelFactory[PlaylistSong]):
    playlist = SubFactory(PlaylistFactory)
    song = SubFactory(SongFactory)
    order = 1

    class Meta:
        model = PlaylistSong
