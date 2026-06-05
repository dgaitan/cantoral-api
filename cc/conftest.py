from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from cc.users.tests.factories import UserFactory

if TYPE_CHECKING:
    from cc.users.models import User


@pytest.fixture
def user(db) -> User:
    return UserFactory.create()
