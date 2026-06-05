from rest_framework import serializers

from cc.users.models import User


class UserSerializer(serializers.ModelSerializer[User]):
    class Meta:
        model = User
        fields = ["id", "email", "name"]
        read_only_fields = ["id", "email"]


class ProfileSerializer(serializers.ModelSerializer[User]):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "name",
            "can_create_songs",
            "can_publish_songs",
            "can_create_playlists",
        ]
        read_only_fields = [
            "id",
            "email",
            "can_create_songs",
            "can_publish_songs",
            "can_create_playlists",
        ]


class RegisterUserSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8, max_length=32)
    name = serializers.CharField(min_length=3, max_length=255)

    def validate_email(self, value: str) -> str:
        value = value.lower()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "An account with this email already exists. Please log in instead."
            )
        return value


class LoginUserSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8, max_length=32)

    def validate_email(self, value: str) -> str:
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Invalid email or password.")
        return value


class VerifyEmailTokenSerializer(serializers.Serializer):
    email = serializers.EmailField()
    token = serializers.CharField(min_length=6, max_length=6)

    def validate_email(self, value: str) -> str:
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Invalid email. User does not exist.")
        return value


class LogoutSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()
