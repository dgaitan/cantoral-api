from django.urls import path

from cc.playlists.api.views import PlaylistViewSet

playlist_list = PlaylistViewSet.as_view({"get": "list", "post": "create"})
playlist_detail = PlaylistViewSet.as_view({"get": "retrieve", "post": "update", "delete": "destroy"})
playlist_songs = PlaylistViewSet.as_view({"get": "songs"})
playlist_attach = PlaylistViewSet.as_view({"post": "attach"})
playlist_reorder = PlaylistViewSet.as_view({"post": "reorder"})

urlpatterns = [
    path("playlists/", playlist_list, name="playlist-list"),
    path("playlists/<uuid:uuid>/", playlist_detail, name="playlist-detail"),
    path("playlists/<uuid:uuid>/songs/", playlist_songs, name="playlist-songs"),
    path("playlists/<uuid:uuid>/songs/attach/", playlist_attach, name="playlist-songs-attach"),
    path("playlists/<uuid:uuid>/songs/order/", playlist_reorder, name="playlist-songs-reorder"),
]
