from __future__ import annotations

from typing import TYPE_CHECKING

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from cc.users.api.serializers import LoginUserSerializer
from cc.users.api.serializers import LogoutSerializer
from cc.users.api.serializers import RegisterUserSerializer
from cc.users.api.serializers import VerifyEmailTokenSerializer
from cc.users.services import LoginUserService
from cc.users.services import RegisterUserService
from cc.users.services import VerifyEmailTokenService
from cc.utils.responses import ApiResponse

if TYPE_CHECKING:
    from rest_framework.request import Request


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request: Request) -> ApiResponse:
        serializer = RegisterUserSerializer(data=request.data)
        if not serializer.is_valid():
            return ApiResponse(
                errors=serializer.errors,
                success=False,
                status=status.HTTP_400_BAD_REQUEST,
            )
        RegisterUserService(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
            name=serializer.validated_data["name"],
        ).dispatch()
        return ApiResponse(
            message="Check your email inbox and use the code to log in.",
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request: Request) -> ApiResponse:
        serializer = LoginUserSerializer(data=request.data)
        if not serializer.is_valid():
            return ApiResponse(
                errors=serializer.errors,
                success=False,
                status=status.HTTP_400_BAD_REQUEST,
            )
        LoginUserService(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        ).dispatch()
        return ApiResponse(
            message="If your credentials are correct, check your email inbox for a login code.",
            status=status.HTTP_200_OK,
        )


class VerifyEmailTokenView(APIView):
    permission_classes = [AllowAny]

    def post(self, request: Request) -> ApiResponse:
        serializer = VerifyEmailTokenSerializer(data=request.data)
        if not serializer.is_valid():
            return ApiResponse(
                errors=serializer.errors,
                success=False,
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            user = VerifyEmailTokenService(
                email=serializer.validated_data["email"],
                token=serializer.validated_data["token"],
            ).dispatch()
        except ValueError as exc:
            return ApiResponse(
                errors=[str(exc)],
                success=False,
                status=status.HTTP_400_BAD_REQUEST,
            )
        refresh = RefreshToken.for_user(user)
        return ApiResponse(
            data={
                "access_token": str(refresh.access_token),
                "refresh_token": str(refresh),
            },
            message="Email successfully verified.",
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> ApiResponse:
        serializer = LogoutSerializer(data=request.data)
        if not serializer.is_valid():
            return ApiResponse(
                errors=serializer.errors,
                success=False,
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            RefreshToken(serializer.validated_data["refresh_token"]).blacklist()
        except TokenError:
            return ApiResponse(
                errors=["Invalid or expired token."],
                success=False,
                status=status.HTTP_400_BAD_REQUEST,
            )
        return ApiResponse(
            message="Successfully logged out.",
            status=status.HTTP_200_OK,
        )
