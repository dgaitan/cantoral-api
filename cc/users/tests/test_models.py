from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from cc.users.models import User as UserModel

if TYPE_CHECKING:
    from cc.users.models import User

pytestmark = pytest.mark.django_db


def test_user_email_is_username_field(user: User) -> None:
    assert UserModel.USERNAME_FIELD == "email"


def test_user_has_no_username_field(user: User) -> None:
    assert not hasattr(user, "username") or user.username is None


def test_user_str_representation(user: User) -> None:
    assert str(user) == user.email
