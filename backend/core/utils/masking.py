"""Utilities for masking sensitive data in API responses."""

import re

MASK_CHAR = "\u2022"  # bullet character
MASKED_PASSWORD = MASK_CHAR * 8


def mask_password(value: str | None) -> str:
    """Replace any password value with masked bullets."""
    if not value:
        return ""
    return MASKED_PASSWORD


def mask_hash(value: str | None, visible_chars: int = 8) -> str:
    """Show first N chars of a hash, mask the rest."""
    if not value:
        return ""
    if len(value) <= visible_chars:
        return MASKED_PASSWORD
    return value[:visible_chars] + MASK_CHAR * 8


def mask_ip_address(value: str | None) -> str:
    """Mask the last octet of an IP address."""
    if not value:
        return ""
    parts = value.split(".")
    if len(parts) == 4:
        parts[-1] = "***"
        return ".".join(parts)
    return value


def mask_email_local(email: str | None) -> str:
    """Show first 2 chars of local part, mask the rest. Keep domain."""
    if not email or "@" not in email:
        return email or ""
    local, domain = email.rsplit("@", 1)
    if len(local) <= 2:
        masked_local = local[0] + MASK_CHAR * 3
    else:
        masked_local = local[:2] + MASK_CHAR * (len(local) - 2)
    return f"{masked_local}@{domain}"


def mask_dehashed_entry(entry: dict) -> dict:
    """Mask sensitive fields in a single DeHashed result entry."""
    masked = dict(entry)

    if "password" in masked:
        passwords = masked["password"]
        if isinstance(passwords, list):
            masked["password"] = [MASKED_PASSWORD for _ in passwords]
        else:
            masked["password"] = MASKED_PASSWORD
        masked["password_exposed"] = bool(entry.get("password"))

    if "hashed_password" in masked:
        hashes = masked["hashed_password"]
        if isinstance(hashes, list):
            masked["hashed_password"] = [mask_hash(h) for h in hashes]
        else:
            masked["hashed_password"] = mask_hash(hashes)

    if "ip_address" in masked:
        ips = masked["ip_address"]
        if isinstance(ips, list):
            masked["ip_address"] = [mask_ip_address(ip) for ip in ips]
        else:
            masked["ip_address"] = mask_ip_address(ips)

    return masked
