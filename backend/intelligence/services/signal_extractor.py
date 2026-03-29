"""Deterministic signal extraction from raw DeHashed results."""

from collections import Counter


def extract_signals(entries: list[dict]) -> list[dict]:
    """
    Extract structured security signals from DeHashed entries.
    All logic is deterministic — no AI, no randomness.
    Returns a list of signal dicts ready for SecuritySignal creation.
    """
    if not entries:
        return [_no_data_signal()]

    signals = []

    # Collect metrics
    all_emails = set()
    all_sources = set()
    password_exposed_count = 0
    email_source_map: dict[str, set] = {}

    for entry in entries:
        emails = entry.get("email", [])
        if isinstance(emails, str):
            emails = [emails]

        source = entry.get("database_name", "Unknown")
        passwords = entry.get("password", [])
        hashed_passwords = entry.get("hashed_password", [])

        for email in emails:
            if email:
                all_emails.add(email.lower())
                email_source_map.setdefault(email.lower(), set()).add(source)

        if source:
            all_sources.add(source)

        # Check for password exposure
        has_password = bool(passwords) and any(p for p in (passwords if isinstance(passwords, list) else [passwords]))
        has_hash = bool(hashed_passwords) and any(h for h in (hashed_passwords if isinstance(hashed_passwords, list) else [hashed_passwords]))
        if has_password or has_hash:
            password_exposed_count += 1

    unique_email_count = len(all_emails)
    breach_count = len(all_sources)

    # Emails with exposure in multiple breaches
    repeated_emails = {e for e, sources in email_source_map.items() if len(sources) > 1}
    repeated_exposure = len(repeated_emails) > 0

    # --- Generate signals ---

    # Signal 1: Employee emails exposed
    signals.append({
        "signal_type": "employee_emails_exposed",
        "value": {"count": unique_email_count},
        "severity": _email_severity(unique_email_count),
        "title": f"{unique_email_count} employee email{'s' if unique_email_count != 1 else ''} found in breach data",
        "description": f"{unique_email_count} unique employee email addresses were identified across breach datasets linked to this domain.",
    })

    # Signal 2: Breach events
    signals.append({
        "signal_type": "breach_events",
        "value": {"count": breach_count, "sources": sorted(all_sources)},
        "severity": _breach_severity(breach_count),
        "title": f"Exposed in {breach_count} known data breach{'es' if breach_count != 1 else ''}",
        "description": f"Company-associated data appears in {breach_count} distinct breach source{'s' if breach_count != 1 else ''}.",
    })

    # Signal 3: Password exposure
    signals.append({
        "signal_type": "password_exposure",
        "value": {"exposed": password_exposed_count > 0, "count": password_exposed_count},
        "severity": "high" if password_exposed_count > 0 else "low",
        "title": "Password exposure detected" if password_exposed_count > 0 else "No password exposure detected",
        "description": (
            f"{password_exposed_count} record{'s' if password_exposed_count != 1 else ''} include exposed passwords or password hashes, indicating potential credential reuse risk."
            if password_exposed_count > 0
            else "No plaintext passwords or hashes were found in the breach data for this domain."
        ),
    })

    # Signal 4: Repeated identity exposure
    if repeated_exposure:
        signals.append({
            "signal_type": "repeated_identity_exposure",
            "value": {"count": len(repeated_emails), "affected_emails": len(repeated_emails)},
            "severity": "high" if len(repeated_emails) >= 5 else "medium",
            "title": f"{len(repeated_emails)} identit{'ies' if len(repeated_emails) != 1 else 'y'} exposed across multiple breaches",
            "description": f"{len(repeated_emails)} email address{'es' if len(repeated_emails) != 1 else ''} appear{'s' if len(repeated_emails) == 1 else ''} in more than one breach source, indicating a pattern of repeated exposure.",
        })

    return signals


def _email_severity(count: int) -> str:
    if count >= 50:
        return "critical"
    if count >= 20:
        return "high"
    if count >= 5:
        return "medium"
    return "low"


def _breach_severity(count: int) -> str:
    if count >= 10:
        return "critical"
    if count >= 5:
        return "high"
    if count >= 2:
        return "medium"
    return "low"


def _no_data_signal() -> dict:
    return {
        "signal_type": "no_data",
        "value": {},
        "severity": "low",
        "title": "No breach data found",
        "description": "No records were found in breach databases for this domain. This may indicate limited exposure or that the domain has not appeared in known breach datasets.",
    }
