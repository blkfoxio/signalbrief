"""Authentication views: Google OAuth, Microsoft OAuth, and dev email/password."""

import logging
import secrets
import uuid

logger = logging.getLogger(__name__)

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


def _unique_username(base: str) -> str:
    """Generate a unique username, appending a short suffix if needed."""
    if not User.objects.filter(username=base).exists():
        return base
    return f"{base}_{uuid.uuid4().hex[:6]}"


REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_MAX_AGE = 7 * 24 * 60 * 60  # 7 days, matches SIMPLE_JWT REFRESH_TOKEN_LIFETIME


def _get_tokens_for_user(user):
    """Generate JWT token pair for a user."""
    refresh = RefreshToken.for_user(user)
    return {
        "access_token": str(refresh.access_token),
        "refresh_token": str(refresh),
    }


def _set_refresh_cookie(response, refresh_token):
    """Set the refresh token as an HttpOnly secure cookie."""
    is_secure = not settings.DEBUG
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        refresh_token,
        max_age=REFRESH_COOKIE_MAX_AGE,
        httponly=True,
        secure=is_secure,
        samesite="Lax",
        path="/api/auth/",
    )
    return response


def _clear_refresh_cookie(response):
    """Remove the refresh token cookie."""
    response.delete_cookie(REFRESH_COOKIE_NAME, path="/api/auth/")
    return response


def _auth_response(user, http_status=status.HTTP_200_OK):
    """Build an auth response with access token in body and refresh token in HttpOnly cookie."""
    tokens = _get_tokens_for_user(user)
    response = Response(
        {
            "access_token": tokens["access_token"],
            "user": UserSerializer(user).data,
        },
        status=http_status,
    )
    _set_refresh_cookie(response, tokens["refresh_token"])
    return response


# --- Google OAuth ---


@api_view(["GET"])
@permission_classes([AllowAny])
def google_login_view(request):
    """Return Google OAuth authorization URL with PKCE."""
    state = secrets.token_urlsafe(32)
    request.session["oauth_state"] = state
    auth_url, code_verifier = google_service.get_auth_url(state)
    request.session["pkce_code_verifier"] = code_verifier
    return Response({"auth_url": auth_url})


@api_view(["POST"])
@permission_classes([AllowAny])
def google_callback_view(request):
    """Handle Google OAuth callback: exchange code, create/update user, return JWT."""
    serializer = OAuthCallbackSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    # Validate OAuth state to prevent CSRF
    expected_state = request.session.pop("oauth_state", None)
    if not expected_state or serializer.validated_data["state"] != expected_state:
        return Response({"error": "Invalid OAuth state"}, status=status.HTTP_400_BAD_REQUEST)

    code = serializer.validated_data["code"]
    code_verifier = request.session.pop("pkce_code_verifier", "")

    try:
        token_result = async_to_sync(google_service.exchange_code_for_tokens)(code, code_verifier)
    except Exception:
        logger.exception("Google OAuth token exchange failed")
        return Response({"error": "Authentication failed"}, status=status.HTTP_400_BAD_REQUEST)

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
            username=_unique_username(email.split("@")[0] if email else google_id),
            first_name=profile.get("given_name", ""),
            last_name=profile.get("family_name", ""),
            avatar_url=profile.get("picture", ""),
        )

    return _auth_response(user)


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

    # Validate OAuth state to prevent CSRF
    expected_state = request.session.pop("oauth_state", None)
    if not expected_state or serializer.validated_data["state"] != expected_state:
        return Response({"error": "Invalid OAuth state"}, status=status.HTTP_400_BAD_REQUEST)

    code = serializer.validated_data["code"]

    try:
        token_result = msal_service.exchange_code_for_tokens(code)
    except ValueError:
        logger.exception("Microsoft OAuth token exchange failed")
        return Response({"error": "Authentication failed"}, status=status.HTTP_400_BAD_REQUEST)

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
            "username": _unique_username(email.split("@")[0] if email else microsoft_id),
            "first_name": profile.get("givenName", ""),
            "last_name": profile.get("surname", ""),
        },
    )

    return _auth_response(user)


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
        username=_unique_username(serializer.validated_data["email"].split("@")[0]),
        email=serializer.validated_data["email"],
        password=serializer.validated_data["password"],
        first_name=serializer.validated_data.get("first_name", ""),
        last_name=serializer.validated_data.get("last_name", ""),
    )

    return _auth_response(user, http_status=status.HTTP_201_CREATED)


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

    return _auth_response(user)


# --- Token refresh (reads from HttpOnly cookie) ---


@api_view(["POST"])
@permission_classes([AllowAny])
def refresh_token_view(request):
    """Refresh JWT tokens using the HttpOnly cookie."""
    refresh_token = request.COOKIES.get(REFRESH_COOKIE_NAME)
    if not refresh_token:
        return Response({"error": "No refresh token"}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        refresh = RefreshToken(refresh_token)
        new_access = str(refresh.access_token)

        # Rotate refresh token
        new_refresh = str(refresh)
        if settings.SIMPLE_JWT.get("ROTATE_REFRESH_TOKENS", False):
            refresh.set_jti()
            refresh.set_exp()
            new_refresh = str(refresh)

        response = Response({"access": new_access})
        _set_refresh_cookie(response, new_refresh)
        return response
    except Exception:
        response = Response({"error": "Invalid or expired refresh token"}, status=status.HTTP_401_UNAUTHORIZED)
        _clear_refresh_cookie(response)
        return response


@api_view(["POST"])
@permission_classes([AllowAny])
def logout_view(request):
    """Clear the refresh token cookie."""
    response = Response({"detail": "Logged out"})
    _clear_refresh_cookie(response)
    return response
