from rest_framework import serializers
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from apps.accounts.models import User, UserRole
from apps.accounts.validators import validate_password_strength
from django.core.exceptions import ValidationError as DjangoValidationError

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        allow_null=False,
        allow_blank=False
    )
    username = serializers.CharField(required=True, allow_null=False, allow_blank=False)
    email = serializers.EmailField(required=True, allow_null=False, allow_blank=False)
    full_name = serializers.CharField(required=True, allow_null=False, allow_blank=False)
    role = serializers.ChoiceField(choices=UserRole.choices, required=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'full_name', 'role']

    def validate_password(self, value):
        try:
            validate_password_strength(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            username=validated_data['username'],
            full_name=validated_data['full_name'],
            role=validated_data['role'],
            password=validated_data['password']
        )
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True, allow_null=False, allow_blank=False)
    password = serializers.CharField(required=True, allow_null=False, allow_blank=False, write_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, allow_null=False, allow_blank=False, write_only=True)
    new_password = serializers.CharField(required=True, allow_null=False, allow_blank=False, write_only=True)

    def validate_new_password(self, value):
        try:
            validate_password_strength(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value
