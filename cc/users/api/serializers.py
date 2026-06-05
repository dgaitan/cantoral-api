from rest_framework import serializers

from cc.users.models import User


class UserSerializer(serializers.ModelSerializer[User]):
    class Meta:
        model = User
        fields = ["id", "email", "name"]
        read_only_fields = ["id", "email"]
