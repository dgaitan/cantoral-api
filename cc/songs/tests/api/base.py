from __future__ import annotations

from rest_framework.test import APIClient

from cc.users.tests.factories import UserFactory


class AuthenticatedApiTest:
    def _auth_client(self, *, can_create_songs: bool = True) -> APIClient:
        user = UserFactory.create(can_create_songs=can_create_songs)
        client = APIClient()
        client.force_authenticate(user=user)
        return client
