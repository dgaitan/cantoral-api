from __future__ import annotations

from django.contrib.auth import authenticate
from django.db import transaction

from cc.users.emails import EmailTokenMail
from cc.users.models import User
from cc.users.tokens import create_email_token
from cc.users.tokens import verify_email_token


class RegisterUserService:
    def __init__(self, email: str, password: str, name: str) -> None:
        self.email = email
        self.password = password
        self.name = name

    @transaction.atomic
    def dispatch(self) -> User:
        user = User.objects.create_user(
            email=self.email,
            password=self.password,
            name=self.name,
            is_active=False,
        )
        email_token = create_email_token(user)
        _token = email_token.token
        transaction.on_commit(
            lambda: EmailTokenMail(to=user.email, token=_token, name=user.name).send(),
        )
        return user


class LoginUserService:
    def __init__(self, email: str, password: str) -> None:
        self.email = email
        self.password = password

    @transaction.atomic
    def dispatch(self) -> None:
        user = authenticate(email=self.email, password=self.password)
        if user is None or not user.is_active:
            return
        email_token = create_email_token(user)
        _token = email_token.token
        transaction.on_commit(
            lambda: EmailTokenMail(to=user.email, token=_token, name=user.name).send(),
        )


class VerifyEmailTokenService:
    def __init__(self, email: str, token: str) -> None:
        self.email = email
        self.token = token

    @transaction.atomic
    def dispatch(self) -> User:
        user = User.objects.get(email=self.email)
        email_token = verify_email_token(user, self.token)
        if email_token is None:
            msg = "Invalid token. Token does not exist or is expired."
            raise ValueError(msg)
        email_token.is_used = True
        email_token.save(update_fields=["is_used"])
        if not user.is_active:
            user.is_active = True
            user.save(update_fields=["is_active"])
        return user
