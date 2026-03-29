"""Authentication URL routes."""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

urlpatterns = [
    path("login/", views.login_view, name="auth-login"),
    path("callback/", views.callback_view, name="auth-callback"),
    path("refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
    path("me/", views.me_view, name="auth-me"),
    # Dev auth (disabled in production via settings)
    path("dev/register/", views.dev_register_view, name="auth-dev-register"),
    path("dev/login/", views.dev_login_view, name="auth-dev-login"),
]
