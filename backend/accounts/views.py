"""Authentication views: Microsoft OAuth + dev email/password."""

import secrets

from asgiref.sync import async_to_sync
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import (
    DevLoginSerializer,
    DevRegisterSerializer,
    OAuthCallbackSerializer,
    UserSerializer,
)
from .services.msal_service import exchange_code_for_tokens, fetch_user_profile, get_auth_url

User = get_user_model()


def _get_tokens_for_user(user):
    """Generate JWT token pair for a user."""
    refresh = RefreshToken.for_user(user)
    return {
        "access_token": str(refresh.access_token),
        "refresh_token": str(refresh),
    }


@api_view(["GET"])
@permission_classes([AllowAny])
def login_view(request):
    """Return Microsoft OAuth authorization URL."""
    state = secrets.token_urlsafe(32)
    request.session["oauth_state"] = state
    auth_url = get_auth_url(state)
    return Response({"auth_url": auth_url})


@api_view(["POST"])
@permission_classes([AllowAny])
def callback_view(request):
    """Handle OAuth callback: exchange code, create/update user, return JWT."""
    serializer = OAuthCallbackSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    code = serializer.validated_data["code"]

    try:
        token_result = exchange_code_for_tokens(code)
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    ms_access_token = token_result.get("access_token")
    if not ms_access_token:
        return Response({"error": "No access token received"}, status=status.HTTP_400_BAD_REQUEST)

    # Fetch user profile from Microsoft Graph
    profile = async_to_sync(fetch_user_profile)(ms_access_token)

    microsoft_id = profile.get("id")
    email = profile.get("mail") or profile.get("userPrincipalName", "")

    # Create or update user
    user, _ = User.objects.update_or_create(
        microsoft_id=microsoft_id,
        defaults={
            "email": email,
            "username": email.split("@")[0] if email else microsoft_id,
            "first_name": profile.get("givenName", ""),
            "last_name": profile.get("surname", ""),
        },
    )

    tokens = _get_tokens_for_user(user)
    return Response({
        **tokens,
        "user": UserSerializer(user).data,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me_view(request):
    """Return current authenticated user."""
    return Response(UserSerializer(request.user).data)


# --- Dev auth (development only) ---


@api_view(["POST"])
@permission_classes([AllowAny])
def dev_register_view(request):
    """Register with email/password (development only)."""
    if not getattr(settings, "DEV_AUTH_ENABLED", False):
        return Response({"error": "Dev auth is disabled"}, status=status.HTTP_403_FORBIDDEN)

    serializer = DevRegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    user = User.objects.create_user(
        username=serializer.validated_data["email"].split("@")[0],
        email=serializer.validated_data["email"],
        password=serializer.validated_data["password"],
        first_name=serializer.validated_data.get("first_name", ""),
        last_name=serializer.validated_data.get("last_name", ""),
    )

    tokens = _get_tokens_for_user(user)
    return Response({
        **tokens,
        "user": UserSerializer(user).data,
    }, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([AllowAny])
def dev_login_view(request):
    """Login with email/password (development only)."""
    if not getattr(settings, "DEV_AUTH_ENABLED", False):
        return Response({"error": "Dev auth is disabled"}, status=status.HTTP_403_FORBIDDEN)

    serializer = DevLoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        user = User.objects.get(email=serializer.validated_data["email"])
    except User.DoesNotExist:
        return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

    if not user.check_password(serializer.validated_data["password"]):
        return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

    tokens = _get_tokens_for_user(user)
    return Response({
        **tokens,
        "user": UserSerializer(user).data,
    })
