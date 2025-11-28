from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User, LoginHistory, SecurityClaim


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["email", "password", "password_confirm", "first_name", "last_name"]

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError({"password": "Passwords do not match"})
        return attrs

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user


class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        if not email or not password:
            raise serializers.ValidationError("Email and password are required")

        user = authenticate(username=email, password=password)

        if not user:
            raise serializers.ValidationError("Invalid credentials")

        if not user.is_active:
            raise serializers.ValidationError("Account is deactivated")

        attrs["user"] = user
        return attrs


class EmailVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)


class ResendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)
    new_password = serializers.CharField(
        write_only=True, validators=[validate_password]
    )
    new_password_confirm = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs["new_password"] != attrs.pop("new_password_confirm"):
            raise serializers.ValidationError(
                {"new_password": "Passwords do not match"}
            )
        return attrs


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "is_verified",
            "date_joined",
            "last_login_at",
        ]
        read_only_fields = [
            "id",
            "email",
            "is_verified",
            "date_joined",
            "last_login_at",
        ]


class LoginHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = LoginHistory
        fields = [
            "id",
            "ip_address",
            "user_agent",
            "country",
            "country_code",
            "city",
            "region",
            "latitude",
            "longitude",
            "login_successful",
            "failure_reason",
            "created_at",
        ]
        read_only_fields = fields


class SecurityClaimSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecurityClaim
        fields = [
            "id",
            "claim_type",
            "description",
            "ip_address",
            "resolved",
            "resolved_at",
            "created_at",
        ]
        read_only_fields = fields


class GoogleAuthSerializer(serializers.Serializer):
    """
    Serializer for Google OAuth authentication.
    Only accepts Google ID tokens.
    """

    id_token = serializers.CharField(
        required=True, help_text="Google ID token obtained from Google OAuth flow"
    )

    def validate_id_token(self, value):
        """Validate that the ID token is not empty"""
        if not value or not value.strip():
            raise serializers.ValidationError("ID token cannot be empty")
        return value.strip()
