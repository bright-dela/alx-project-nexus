from rest_framework import serializers
from .models import User


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for passwordless user registration.
    Only requires email, firstname and lastname - no password needed.
    """

    class Meta:
        model = User
        fields = ("email", "firstname", "lastname")

    def validate_email(self, value):
        """Ensure email is lowercase and properly formatted"""
        return value.lower().strip()


class PasswordlessLoginSerializer(serializers.Serializer):
    """
    Serializer for initiating passwordless login.
    User provides email to receive OTP or magic link.
    """

    email = serializers.EmailField()
    method = serializers.ChoiceField(choices=["otp", "magic_link"], default="otp")

    def validate_email(self, value):
        """Ensure email exists in system"""

        email = value.lower().strip()
        if not User.objects.filter(email=email).exists():
            raise serializers.ValidationError("No account found with this email address")
        
        return email


class OTPVerificationSerializer(serializers.Serializer):
    """
    Serializer for verifying the OTP code sent to user's email.
    """

    email = serializers.EmailField()
    otp_code = serializers.CharField(max_length=6, min_length=6)

    def validate_email(self, value):
        return value.lower().strip()

    def validate_otp_code(self, value):
        """Ensure OTP is numeric and correct length"""
        if not value.isdigit():
            raise serializers.ValidationError("OTP must contain only numbers")
        
        if len(value) != 6:
            raise serializers.ValidationError("OTP must be exactly 6 digits long")
        
        return value


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user data responses"""

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "firstname",
            "lastname",
            "is_email_verified",
            "date_joined",
        )
        read_only_fields = ("id", "is_email_verified", "date_joined")
