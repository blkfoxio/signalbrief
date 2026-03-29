"""Custom User model for SignalBrief."""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Extended user with OAuth provider fields."""

    microsoft_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    google_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    avatar_url = models.URLField(blank=True, default="")

    class Meta:
        db_table = "users"

    def __str__(self):
        return self.email or self.username
