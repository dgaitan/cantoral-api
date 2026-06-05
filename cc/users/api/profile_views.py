from __future__ import annotations

from typing import TYPE_CHECKING

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from cc.users.api.serializers import ProfileSerializer
from cc.utils.responses import ApiResponse

if TYPE_CHECKING:
    from rest_framework.request import Request


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> ApiResponse:
        serializer = ProfileSerializer(request.user)
        return ApiResponse(data=serializer.data, status=status.HTTP_200_OK)

    def put(self, request: Request) -> ApiResponse:
        serializer = ProfileSerializer(request.user, data=request.data, partial=True)
        if not serializer.is_valid():
            return ApiResponse(
                errors=serializer.errors,
                success=False,
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer.save()
        return ApiResponse(data=serializer.data, status=status.HTTP_200_OK)
