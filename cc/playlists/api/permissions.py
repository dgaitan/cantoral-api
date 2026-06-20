from __future__ import annotations

from rest_framework.permissions import BasePermission

from cc.playlists.models import Playlist


class BasePlaylistPermission(BasePermission):
    def is_owner(self, request, obj: Playlist) -> bool:
        return bool(request.user and request.user.is_authenticated and obj.owner_id == request.user.pk)


class PlaylistAccessPermission(BasePlaylistPermission):
    """Allow access if the playlist is public, or if the requesting user is the owner."""

    def has_object_permission(self, request, view, obj: Playlist) -> bool:
        if obj.is_public:
            return True
        return self.is_owner(request, obj)


class IsPlaylistOwner(BasePlaylistPermission):
    def has_object_permission(self, request, view, obj: Playlist) -> bool:
        return self.is_owner(request, obj)


class CanMutatePlaylistSongs(BasePermission):
    """Allow if the user is the owner, or if the playlist is collaborative."""

    def has_object_permission(self, request, view, obj: Playlist) -> bool:
        if not (request.user and request.user.is_authenticated):
            return False
        return obj.owner_id == request.user.pk or obj.is_collaborative
