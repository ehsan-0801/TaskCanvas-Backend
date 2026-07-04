from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


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
