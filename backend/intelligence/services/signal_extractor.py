"""Deterministic signal extraction from all OSINT data sources."""

from datetime import datetime, timezone


def extract_all_signals(dehashed_entries: list[dict], osint_results: dict) -> list[dict]:
    """
    Extract structured security signals from all data sources.
    All logic is deterministic — no AI, no randomness.
    Returns a list of signal dicts ready for SecuritySignal creation.
    """
    signals = extract_dehashed_signals(dehashed_entries)
    signals += extract_hibp_signals(osint_results.get("hibp", {}))
    signals += extract_leakcheck_signals(osint_results.get("leakcheck", {}))
    signals += extract_shodan_signals(osint_results.get("shodan", {}))
    signals += extract_censys_signals(osint_results.get("censys", {}))
    signals += extract_securitytrails_signals(osint_results.get("securitytrails", {}))
    signals += extract_builtwith_signals(osint_results.get("builtwith", {}))
    return signals


# ---------------------------------------------------------------------------
# DeHashed signals (existing logic, preserved)
# ---------------------------------------------------------------------------

def extract_dehashed_signals(entries: list[dict]) -> list[dict]:
    """Extract signals from DeHashed breach entries."""
    if not entries:
        return [_no_data_signal("dehashed")]

    signals = []
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

        has_password = bool(passwords) and any(p for p in (passwords if isinstance(passwords, list) else [passwords]))
        has_hash = bool(hashed_passwords) and any(h for h in (hashed_passwords if isinstance(hashed_passwords, list) else [hashed_passwords]))
        if has_password or has_hash:
            password_exposed_count += 1

    unique_email_count = len(all_emails)
    breach_count = len(all_sources)
    repeated_emails = {e for e, sources in email_source_map.items() if len(sources) > 1}

    signals.append({
        "source": "dehashed",
        "signal_type": "employee_emails_exposed",
        "value": {"count": unique_email_count},
        "severity": _email_severity(unique_email_count),
        "title": f"{unique_email_count} employee email{'s' if unique_email_count != 1 else ''} found in breach data",
        "description": f"{unique_email_count} unique employee email addresses were identified across breach datasets linked to this domain.",
    })

    signals.append({
        "source": "dehashed",
        "signal_type": "breach_events",
        "value": {"count": breach_count, "sources": sorted(all_sources)},
        "severity": _breach_severity(breach_count),
        "title": f"Exposed in {breach_count} known data breach{'es' if breach_count != 1 else ''}",
        "description": f"Company-associated data appears in {breach_count} distinct breach source{'s' if breach_count != 1 else ''}.",
    })

    signals.append({
        "source": "dehashed",
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

    if repeated_emails:
        signals.append({
            "source": "dehashed",
            "signal_type": "repeated_identity_exposure",
            "value": {"count": len(repeated_emails), "affected_emails": len(repeated_emails)},
            "severity": "high" if len(repeated_emails) >= 5 else "medium",
            "title": f"{len(repeated_emails)} identit{'ies' if len(repeated_emails) != 1 else 'y'} exposed across multiple breaches",
            "description": f"{len(repeated_emails)} email address{'es' if len(repeated_emails) != 1 else ''} appear{'s' if len(repeated_emails) == 1 else ''} in more than one breach source, indicating a pattern of repeated exposure.",
        })

    return signals


# ---------------------------------------------------------------------------
# HIBP signals
# ---------------------------------------------------------------------------

def extract_hibp_signals(data: dict) -> list[dict]:
    """Extract signals from Have I Been Pwned breach data."""
    if not data or data.get("error") or not data.get("breaches"):
        return []

    signals = []
    breaches = data["breaches"]
    total = len(breaches)

    # Collect breach metadata
    breach_names = [b.get("Name", "Unknown") for b in breaches]
    data_classes = set()
    sensitive_breaches = []
    most_recent_date = None

    for breach in breaches:
        for dc in breach.get("DataClasses", []):
            data_classes.add(dc)
        if breach.get("IsSensitive"):
            sensitive_breaches.append(breach.get("Name", "Unknown"))
        breach_date_str = breach.get("BreachDate", "")
        if breach_date_str:
            try:
                breach_date = datetime.strptime(breach_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                if most_recent_date is None or breach_date > most_recent_date:
                    most_recent_date = breach_date
            except ValueError:
                pass

    # Signal: Known breaches
    signals.append({
        "source": "hibp",
        "signal_type": "known_breaches",
        "value": {"count": total, "breach_names": breach_names[:20], "data_classes": sorted(data_classes)},
        "severity": _breach_severity(total),
        "title": f"Domain appears in {total} known breach{'es' if total != 1 else ''}",
        "description": f"HIBP confirms this domain was involved in {total} publicly disclosed breach{'es' if total != 1 else ''}, exposing data types including: {', '.join(sorted(data_classes)[:5])}.",
    })

    # Signal: Breach recency
    if most_recent_date:
        days_ago = (datetime.now(timezone.utc) - most_recent_date).days
        recency_severity = "critical" if days_ago < 180 else "high" if days_ago < 365 else "medium" if days_ago < 730 else "low"
        signals.append({
            "source": "hibp",
            "signal_type": "breach_recency",
            "value": {"most_recent_date": most_recent_date.isoformat(), "days_ago": days_ago},
            "severity": recency_severity,
            "title": f"Most recent breach was {days_ago} days ago",
            "description": f"The most recent known breach involving this domain occurred {days_ago} days ago ({most_recent_date.strftime('%B %Y')}).",
        })

    # Signal: Sensitive breach exposure
    if sensitive_breaches:
        signals.append({
            "source": "hibp",
            "signal_type": "sensitive_breach_exposure",
            "value": {"count": len(sensitive_breaches), "breaches": sensitive_breaches},
            "severity": "critical" if len(sensitive_breaches) >= 2 else "high",
            "title": f"Appears in {len(sensitive_breaches)} sensitive breach{'es' if len(sensitive_breaches) != 1 else ''}",
            "description": f"This domain appears in {len(sensitive_breaches)} breach{'es' if len(sensitive_breaches) != 1 else ''} classified as sensitive, which may contain data that could cause reputational or legal risk.",
        })

    return signals


# ---------------------------------------------------------------------------
# LeakCheck signals
# ---------------------------------------------------------------------------

def extract_leakcheck_signals(data: dict) -> list[dict]:
    """Extract signals from LeakCheck stealer log data."""
    if not data or data.get("error") or not data.get("results"):
        return []

    signals = []
    results = data["results"]
    total = len(results)

    # Count entries with password or stealer log indicators
    stealer_hits = 0
    sources = set()
    for entry in results:
        source = entry.get("source", {})
        if isinstance(source, dict):
            source_name = source.get("name", "")
        else:
            source_name = str(source)
        sources.add(source_name)
        if entry.get("password") or entry.get("hash"):
            stealer_hits += 1

    signals.append({
        "source": "leakcheck",
        "signal_type": "stealer_log_exposure",
        "value": {"total_results": total, "credential_hits": stealer_hits, "sources": sorted(sources)},
        "severity": "critical" if stealer_hits >= 10 else "high" if stealer_hits >= 1 else "medium",
        "title": f"{total} record{'s' if total != 1 else ''} found in stealer logs",
        "description": f"LeakCheck identified {total} record{'s' if total != 1 else ''} associated with this domain in infostealer malware logs. {stealer_hits} include exposed credentials.",
    })

    if stealer_hits > 0:
        signals.append({
            "source": "leakcheck",
            "signal_type": "credential_market_presence",
            "value": {"count": stealer_hits},
            "severity": "critical" if stealer_hits >= 5 else "high",
            "title": f"{stealer_hits} credential{'s' if stealer_hits != 1 else ''} from infostealer malware",
            "description": f"{stealer_hits} credential{'s' if stealer_hits != 1 else ''} associated with this domain were harvested by infostealer malware, indicating active endpoint compromise risk.",
        })

    return signals


# ---------------------------------------------------------------------------
# Shodan signals
# ---------------------------------------------------------------------------

def extract_shodan_signals(data: dict) -> list[dict]:
    """Extract signals from Shodan host/service data."""
    if not data or data.get("error") or not data.get("hosts"):
        return []

    signals = []
    host = data["hosts"][0]  # Primary host
    ports = host.get("ports", [])
    vulns = host.get("vulns", [])
    services = host.get("data", [])

    # Signal: Exposed services
    if ports:
        high_risk_ports = {21, 22, 23, 25, 445, 1433, 3306, 3389, 5432, 5900, 6379, 27017}
        exposed_high_risk = [p for p in ports if p in high_risk_ports]
        severity = "critical" if exposed_high_risk else "high" if len(ports) > 10 else "medium" if len(ports) > 3 else "low"

        signals.append({
            "source": "shodan",
            "signal_type": "exposed_services",
            "value": {"ports": ports, "high_risk_ports": exposed_high_risk, "total": len(ports)},
            "severity": severity,
            "title": f"{len(ports)} exposed service{'s' if len(ports) != 1 else ''} detected",
            "description": f"Shodan detected {len(ports)} open port{'s' if len(ports) != 1 else ''} on the primary IP."
            + (f" Includes high-risk services on port{'s' if len(exposed_high_risk) != 1 else ''}: {', '.join(str(p) for p in exposed_high_risk)}." if exposed_high_risk else ""),
        })

    # Signal: Known vulnerabilities
    if vulns:
        signals.append({
            "source": "shodan",
            "signal_type": "known_vulnerabilities",
            "value": {"cves": vulns[:20], "total": len(vulns)},
            "severity": "critical" if len(vulns) >= 5 else "high" if len(vulns) >= 1 else "low",
            "title": f"{len(vulns)} known CVE{'s' if len(vulns) != 1 else ''} detected",
            "description": f"Shodan identified {len(vulns)} known vulnerabilit{'ies' if len(vulns) != 1 else 'y'} on exposed services: {', '.join(vulns[:5])}{'...' if len(vulns) > 5 else ''}.",
        })

    # Signal: Outdated software
    outdated = []
    for svc in services:
        product = svc.get("product", "")
        version = svc.get("version", "")
        if product and version:
            outdated.append(f"{product} {version}")

    if outdated:
        signals.append({
            "source": "shodan",
            "signal_type": "outdated_software",
            "value": {"software": outdated[:10]},
            "severity": "medium",
            "title": f"{len(outdated)} software version{'s' if len(outdated) != 1 else ''} identified",
            "description": f"Detected software versions on exposed services: {', '.join(outdated[:5])}. Review for end-of-life or unpatched versions.",
        })

    return signals


# ---------------------------------------------------------------------------
# Censys signals
# ---------------------------------------------------------------------------

def extract_censys_signals(data: dict) -> list[dict]:
    """Extract signals from Censys certificate and host data."""
    if not data or data.get("error"):
        return []

    signals = []
    hosts = data.get("hosts", [])
    certs = data.get("certificates", [])

    # Signal: Expired or expiring certificates
    expired_count = 0
    weak_tls_count = 0
    for cert in certs:
        parsed = cert.get("parsed", {})
        validity = parsed.get("validity", {})
        not_after = validity.get("end")
        if not_after:
            try:
                expiry = datetime.fromisoformat(not_after.replace("Z", "+00:00"))
                if expiry < datetime.now(timezone.utc):
                    expired_count += 1
            except (ValueError, TypeError):
                pass

    if expired_count > 0:
        signals.append({
            "source": "censys",
            "signal_type": "expired_certificates",
            "value": {"count": expired_count, "total_certs": len(certs)},
            "severity": "high" if expired_count >= 3 else "medium",
            "title": f"{expired_count} expired SSL certificate{'s' if expired_count != 1 else ''}",
            "description": f"{expired_count} of {len(certs)} certificates associated with this domain {'are' if expired_count != 1 else 'is'} expired, which may indicate abandoned infrastructure or management gaps.",
        })

    # Signal: Host exposure
    total_hosts = data.get("total_hosts", len(hosts))
    if total_hosts > 0:
        services_seen = set()
        for host in hosts:
            for svc in host.get("services", []):
                svc_name = svc.get("service_name", svc.get("transport_protocol", ""))
                if svc_name:
                    services_seen.add(svc_name)

        if services_seen:
            signals.append({
                "source": "censys",
                "signal_type": "exposed_services",
                "value": {"total_hosts": total_hosts, "services": sorted(services_seen)},
                "severity": "medium" if total_hosts <= 5 else "high",
                "title": f"{total_hosts} host{'s' if total_hosts != 1 else ''} with exposed services",
                "description": f"Censys found {total_hosts} host{'s' if total_hosts != 1 else ''} associated with this domain exposing services: {', '.join(sorted(services_seen)[:5])}.",
            })

    return signals


# ---------------------------------------------------------------------------
# SecurityTrails signals
# ---------------------------------------------------------------------------

def extract_securitytrails_signals(data: dict) -> list[dict]:
    """Extract signals from SecurityTrails DNS/subdomain data."""
    if not data or data.get("error"):
        return []

    signals = []
    subdomains = data.get("subdomains", [])
    dns = data.get("dns", {})
    total_subs = len(subdomains)

    # Signal: Subdomain count (attack surface width)
    if total_subs > 0:
        severity = "high" if total_subs >= 100 else "medium" if total_subs >= 20 else "low"
        signals.append({
            "source": "securitytrails",
            "signal_type": "subdomain_count",
            "value": {"count": total_subs, "sample": subdomains[:20]},
            "severity": severity,
            "title": f"{total_subs} subdomain{'s' if total_subs != 1 else ''} discovered",
            "description": f"SecurityTrails found {total_subs} subdomain{'s' if total_subs != 1 else ''} for this domain. A larger subdomain footprint increases attack surface area.",
        })

    # Signal: DNS misconfigurations
    issues = []
    txt_records = dns.get("txt", {}).get("values", [])
    mx_records = dns.get("mx", {}).get("values", [])

    # Check for SPF
    has_spf = any("v=spf1" in str(r.get("value", "")).lower() for r in txt_records) if txt_records else False
    # Check for DMARC (would be on _dmarc subdomain, but flag if missing from TXT)
    has_dmarc = any("v=dmarc1" in str(r.get("value", "")).lower() for r in txt_records) if txt_records else False

    if mx_records and not has_spf:
        issues.append("Missing SPF record")
    if mx_records and not has_dmarc:
        issues.append("Missing DMARC record")

    if issues:
        signals.append({
            "source": "securitytrails",
            "signal_type": "dns_misconfigurations",
            "value": {"issues": issues},
            "severity": "high" if len(issues) >= 2 else "medium",
            "title": f"{len(issues)} DNS configuration issue{'s' if len(issues) != 1 else ''}",
            "description": f"DNS analysis found: {', '.join(issues)}. These gaps can enable email spoofing and phishing attacks.",
        })

    return signals


# ---------------------------------------------------------------------------
# BuiltWith signals
# ---------------------------------------------------------------------------

def extract_builtwith_signals(data: dict) -> list[dict]:
    """Extract signals from BuiltWith technology footprint data."""
    if not data or data.get("error") or not data.get("technologies"):
        return []

    signals = []
    technologies = data["technologies"]
    security_tools = data.get("security_tools", [])
    total = len(technologies)

    # Signal: Technology footprint size
    severity = "medium" if total >= 50 else "low"
    signals.append({
        "source": "builtwith",
        "signal_type": "technology_footprint",
        "value": {"total": total, "categories": list({t.get("category", "") for t in technologies if t.get("category")})},
        "severity": severity,
        "title": f"{total} technologies detected in stack",
        "description": f"BuiltWith identified {total} technologies in use. A larger tech stack increases the attack surface and dependency management complexity.",
    })

    # Signal: Security tools presence (or absence)
    security_names = [t.get("name", "") for t in security_tools]
    if security_names:
        signals.append({
            "source": "builtwith",
            "signal_type": "security_tools_detected",
            "value": {"tools": security_names, "count": len(security_names)},
            "severity": "low",
            "title": f"{len(security_names)} security-related tool{'s' if len(security_names) != 1 else ''} detected",
            "description": f"Detected security-related technologies: {', '.join(security_names[:5])}{'...' if len(security_names) > 5 else ''}.",
        })
    else:
        signals.append({
            "source": "builtwith",
            "signal_type": "security_tools_detected",
            "value": {"tools": [], "count": 0},
            "severity": "medium",
            "title": "No security tools detected",
            "description": "No WAF, CDN security, or monitoring tools were detected in the technology stack. This may indicate gaps in perimeter defense.",
        })

    return signals


# ---------------------------------------------------------------------------
# Backward-compatible wrapper (existing code calls extract_signals)
# ---------------------------------------------------------------------------

def extract_signals(entries: list[dict]) -> list[dict]:
    """Legacy wrapper — extracts DeHashed signals only. Use extract_all_signals for full pipeline."""
    return extract_dehashed_signals(entries)


# ---------------------------------------------------------------------------
# Severity helpers
# ---------------------------------------------------------------------------

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


def _no_data_signal(source: str = "dehashed") -> dict:
    return {
        "source": source,
        "signal_type": "no_data",
        "value": {},
        "severity": "low",
        "title": "No breach data found",
        "description": "No records were found in breach databases for this domain. This may indicate limited exposure or that the domain has not appeared in known breach datasets.",
    }
