"""Authentication views: Google OAuth, Microsoft OAuth, and dev email/password."""

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
from .services import google_service, msal_service

User = get_user_model()


def _get_tokens_for_user(user):
    """Generate JWT token pair for a user."""
    refresh = RefreshToken.for_user(user)
    return {
        "access_token": str(refresh.access_token),
        "refresh_token": str(refresh),
    }


# --- Google OAuth ---


@api_view(["GET"])
@permission_classes([AllowAny])
def google_login_view(request):
    """Return Google OAuth authorization URL."""
    state = secrets.token_urlsafe(32)
    request.session["oauth_state"] = state
    auth_url = google_service.get_auth_url(state)
    return Response({"auth_url": auth_url})


@api_view(["POST"])
@permission_classes([AllowAny])
def google_callback_view(request):
    """Handle Google OAuth callback: exchange code, create/update user, return JWT."""
    serializer = OAuthCallbackSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    code = serializer.validated_data["code"]

    try:
        token_result = async_to_sync(google_service.exchange_code_for_tokens)(code)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    access_token = token_result.get("access_token")
    if not access_token:
        return Response({"error": "No access token received"}, status=status.HTTP_400_BAD_REQUEST)

    profile = async_to_sync(google_service.fetch_user_profile)(access_token)

    google_id = profile.get("id")
    email = profile.get("email", "")

    # Try to find existing user by google_id or email
    user = User.objects.filter(google_id=google_id).first()
    if not user and email:
        user = User.objects.filter(email=email).first()

    if user:
        # Update existing user with google_id
        if not user.google_id:
            user.google_id = google_id
        user.first_name = profile.get("given_name", "") or user.first_name
        user.last_name = profile.get("family_name", "") or user.last_name
        user.avatar_url = profile.get("picture", "") or user.avatar_url
        user.save()
    else:
        # Create new user
        user = User.objects.create(
            google_id=google_id,
            email=email,
            username=email.split("@")[0] if email else google_id,
            first_name=profile.get("given_name", ""),
            last_name=profile.get("family_name", ""),
            avatar_url=profile.get("picture", ""),
        )

    tokens = _get_tokens_for_user(user)
    return Response({
        **tokens,
        "user": UserSerializer(user).data,
    })


# --- Microsoft OAuth ---


@api_view(["GET"])
@permission_classes([AllowAny])
def microsoft_login_view(request):
    """Return Microsoft OAuth authorization URL."""
    state = secrets.token_urlsafe(32)
    request.session["oauth_state"] = state
    auth_url = msal_service.get_auth_url(state)
    return Response({"auth_url": auth_url})


@api_view(["POST"])
@permission_classes([AllowAny])
def microsoft_callback_view(request):
    """Handle Microsoft OAuth callback: exchange code, create/update user, return JWT."""
    serializer = OAuthCallbackSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    code = serializer.validated_data["code"]

    try:
        token_result = msal_service.exchange_code_for_tokens(code)
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    ms_access_token = token_result.get("access_token")
    if not ms_access_token:
        return Response({"error": "No access token received"}, status=status.HTTP_400_BAD_REQUEST)

    profile = async_to_sync(msal_service.fetch_user_profile)(ms_access_token)

    microsoft_id = profile.get("id")
    email = profile.get("mail") or profile.get("userPrincipalName", "")

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


# --- Common ---


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
