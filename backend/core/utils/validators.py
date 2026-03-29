"""Input validation utilities."""

import re
from urllib.parse import urlparse

from rest_framework import serializers


def normalize_domain(value: str) -> str:
    """
    Normalize a domain input: strip protocol, www, trailing slashes, lowercase.
    Handles inputs like 'https://www.example.com/', 'www.example.com', 'example.com'.
    """
    if not value:
        return ""

    value = value.strip().lower()

    # Strip protocol
    if "://" in value:
        parsed = urlparse(value)
        value = parsed.netloc or parsed.path

    # Strip www prefix
    if value.startswith("www."):
        value = value[4:]

    # Strip trailing slashes and paths
    value = value.split("/")[0]

    # Strip port
    value = value.split(":")[0]

    return value


def extract_domain_from_email(email: str) -> str:
    """Extract and normalize domain from an email address."""
    if not email or "@" not in email:
        return ""
    return normalize_domain(email.split("@")[1])


def validate_domain_format(domain: str) -> bool:
    """Check if a string looks like a valid domain."""
    if not domain:
        return False
    pattern = r"^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z]{2,})+$"
    return bool(re.match(pattern, domain))


def validate_linkedin_url(url: str) -> bool:
    """Check if a URL is a valid LinkedIn company URL."""
    if not url:
        return True  # Optional field
    parsed = urlparse(url)
    return parsed.netloc in ("linkedin.com", "www.linkedin.com") and "/company/" in parsed.path
