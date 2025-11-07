from rest_framework import serializers
from djoser.serializers import UserCreateSerializer as BaseUserCreateSerializer
from djoser.serializers import TokenCreateSerializer as BaseTokenCreateSerializer
from .models import User
from rest_framework_simplejwt.tokens import RefreshToken


class UserCreateSerializer(BaseUserCreateSerializer):
    confirm_password = serializers.CharField(write_only=True)
    role = serializers.CharField(read_only=True)

    class Meta(BaseUserCreateSerializer.Meta):
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "password", "confirm_password", "role"]

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        if User.objects.filter(email=attrs['email']).exists():
            raise serializers.ValidationError({"email": "Email already exists."})
        if User.objects.filter(username=attrs['username']).exists():
            raise serializers.ValidationError({"username": "Username is taken."})
        return attrs

    def create(self, validated_data):
        validated_data.pop("confirm_password")
        user = super().create(validated_data)

        # Generate JWT token for this user
        refresh = RefreshToken.for_user(user)
        self.token = str(refresh.access_token)

        return user

    def to_representation(self, instance):
        return {
            "token": getattr(self, "token", None),
            "user": {
                "id": str(instance.id),
                "email": instance.email,
                "name": f"{instance.first_name} {instance.last_name}",
                "role": instance.role,
                "created_at": instance.date_joined.isoformat(),
            }
        }


