from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class RegisterSerializer(serializers.Serializer):
    """Self-service sign-up. A new user becomes the owner of their own teams."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    name = serializers.CharField(required=False, allow_blank=True)

    def validate_email(self, value):
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return email

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data["email"],
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data.get("name", "") or "",
        )


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Authenticate with email + password and issue an access/refresh pair.

    We look the user up by email (falling back to username) and verify the
    password directly, then mint the token via ``get_token``. This avoids
    SimpleJWT's parent ``validate`` calling ``authenticate(email=...)``, which
    Django's ModelBackend does not understand (it keys on ``username``).
    """

    username_field = "email"

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        if not email or not password:
            raise serializers.ValidationError(
                {"detail": "Email and password are required"}
            )

        user = (
            User.objects.filter(email__iexact=email).first()
            or User.objects.filter(username=email).first()
        )
        if user is None or not user.is_active or not user.check_password(password):
            raise serializers.ValidationError({"detail": "Invalid credentials"})

        refresh = self.get_token(user)
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }
