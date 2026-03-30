"""Authentication URL routes."""

from django.urls import path

from . import views

urlpatterns = [
    # Google OAuth
    path("google/login/", views.google_login_view, name="auth-google-login"),
    path("google/callback/", views.google_callback_view, name="auth-google-callback"),
    # Microsoft OAuth
    path("microsoft/login/", views.microsoft_login_view, name="auth-microsoft-login"),
    path("microsoft/callback/", views.microsoft_callback_view, name="auth-microsoft-callback"),
    # Common
    path("refresh/", views.refresh_token_view, name="auth-refresh"),
    path("logout/", views.logout_view, name="auth-logout"),
    path("me/", views.me_view, name="auth-me"),
    # Dev auth (disabled in production via settings)
    path("dev/register/", views.dev_register_view, name="auth-dev-register"),
    path("dev/login/", views.dev_login_view, name="auth-dev-login"),
]
