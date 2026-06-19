from __future__ import annotations

import string
from datetime import timedelta

from django.utils import timezone
from factory import Faker, LazyFunction, SubFactory, post_generation
from factory.django import DjangoModelFactory

from cc.users.models import EmailToken, User

_TOKEN_LETTERS = string.ascii_uppercase + string.digits


class UserFactory(DjangoModelFactory[User]):
    email = Faker("email")
    name = Faker("name")

    @post_generation
    def password(self: User, create: bool, extracted: str | None, **kwargs):  # noqa: FBT001
        password = (
            extracted
            if extracted
            else Faker(
                "password",
                length=42,
                special_chars=True,
                digits=True,
                upper_case=True,
                lower_case=True,
            ).evaluate(None, None, extra={"locale": None})
        )
        self.set_password(password)
        if create:
            self.save()

    class Meta:
        model = User
        django_get_or_create = ["email"]
        skip_postgeneration_save = True


class EmailTokenFactory(DjangoModelFactory[EmailToken]):
    user = SubFactory(UserFactory)
    token = Faker("lexify", text="??????", letters=_TOKEN_LETTERS)
    expires_at = LazyFunction(lambda: timezone.now() + timedelta(minutes=20))
    is_used = False

    class Meta:
        model = EmailToken
