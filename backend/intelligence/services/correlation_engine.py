"""
Correlation engine — merges signals from all OSINT sources into 3 business findings.

This is the "secret sauce": normalize + correlate + score across sources,
then hand pre-structured data to OpenAI for narrative generation.
"""

# High-risk ports that warrant immediate remediation
HIGH_RISK_PORTS = {
    21: "FTP",
    22: "SSH",
    23: "Telnet",
    25: "SMTP",
    445: "SMB",
    1433: "MSSQL",
    3306: "MySQL",
    3389: "RDP",
    5432: "PostgreSQL",
    5900: "VNC",
    6379: "Redis",
    27017: "MongoDB",
}


def correlate_findings(signals: list[dict], osint_results: dict) -> dict:
    """
    Cross-reference signals from all sources into 3 business findings:
    1. Credential Exposure — what's confirmed compromised
    2. Attack Surface — what's exposed and unprotected
    3. Remediation Priorities — what to fix, ordered by severity

    Args:
        signals: All extracted signals from extract_all_signals()
        osint_results: Raw OSINT response dicts keyed by source name

    Returns:
        Dict with credential_exposure, attack_surface, remediation_priorities
    """
    cred = _build_credential_exposure(signals, osint_results)
    surface = _build_attack_surface(signals, osint_results)
    remediation = _build_remediation_priorities(cred, surface, signals)

    return {
        "credential_exposure": cred,
        "attack_surface": surface,
        "remediation_priorities": remediation,
    }


# ---------------------------------------------------------------------------
# Finding 1: Credential Exposure
# ---------------------------------------------------------------------------

def _build_credential_exposure(signals: list[dict], osint_results: dict) -> dict:
    """Merge DeHashed + LeakCheck + HIBP into confirmed credential exposure."""

    # Extract from signals
    password_signal = _find_signal(signals, "password_exposure")
    email_signal = _find_signal(signals, "employee_emails_exposed")
    stealer_signal = _find_signal(signals, "stealer_log_exposure")
    breach_signal = _find_signal(signals, "known_breaches")
    recency_signal = _find_signal(signals, "breach_recency")
    repeated_signal = _find_signal(signals, "repeated_identity_exposure")
    credential_market = _find_signal(signals, "credential_market_presence")

    # Counts
    confirmed_passwords = password_signal.get("value", {}).get("count", 0) if password_signal else 0
    total_emails = email_signal.get("value", {}).get("count", 0) if email_signal else 0
    stealer_hits = stealer_signal.get("value", {}).get("credential_hits", 0) if stealer_signal else 0
    stealer_total = stealer_signal.get("value", {}).get("total_results", 0) if stealer_signal else 0
    breach_count = breach_signal.get("value", {}).get("count", 0) if breach_signal else 0
    breach_names = breach_signal.get("value", {}).get("breach_names", []) if breach_signal else []
    repeated_count = repeated_signal.get("value", {}).get("count", 0) if repeated_signal else 0
    market_count = credential_market.get("value", {}).get("count", 0) if credential_market else 0
    days_since_breach = recency_signal.get("value", {}).get("days_ago") if recency_signal else None

    # Total exposed credentials = passwords + stealer log credentials
    total_exposed = confirmed_passwords + stealer_hits

    # Severity
    if total_exposed >= 10 or market_count >= 5:
        severity = "critical"
    elif total_exposed >= 1 or stealer_hits >= 1:
        severity = "high"
    elif total_emails >= 20 or breach_count >= 5:
        severity = "medium"
    elif total_emails >= 1:
        severity = "low"
    else:
        severity = "low"

    # Evidence lines (for UI and for AI context)
    evidence = []
    sources = set()
    if total_emails > 0:
        evidence.append(f"DeHashed: {total_emails} employee emails in breach data")
        sources.add("dehashed")
    if confirmed_passwords > 0:
        evidence.append(f"DeHashed: {confirmed_passwords} exposed passwords/hashes")
        sources.add("dehashed")
    if stealer_hits > 0:
        evidence.append(f"LeakCheck: {stealer_hits} credentials from infostealer malware")
        sources.add("leakcheck")
    if breach_count > 0:
        top_breaches = ", ".join(breach_names[:5])
        evidence.append(f"HIBP: {breach_count} known breaches ({top_breaches})")
        sources.add("hibp")
    if repeated_count > 0:
        evidence.append(f"{repeated_count} identities exposed across multiple breaches")
    if days_since_breach is not None:
        evidence.append(f"Most recent breach: {days_since_breach} days ago")

    return {
        "severity": severity,
        "total_emails_exposed": total_emails,
        "confirmed_passwords": confirmed_passwords,
        "stealer_log_hits": stealer_hits,
        "stealer_log_total": stealer_total,
        "market_credentials": market_count,
        "breach_count": breach_count,
        "breach_names": breach_names[:10],
        "repeated_exposures": repeated_count,
        "days_since_breach": days_since_breach,
        "total_exposed_credentials": total_exposed,
        "evidence": evidence,
        "sources": sorted(sources),
    }


# ---------------------------------------------------------------------------
# Finding 2: Attack Surface
# ---------------------------------------------------------------------------

def _build_attack_surface(signals: list[dict], osint_results: dict) -> dict:
    """Merge Shodan + Censys + SecurityTrails + BuiltWith into attack surface view."""

    # Exposed services (Shodan + Censys)
    shodan_svc = _find_signal(signals, "exposed_services", source="shodan")
    censys_svc = _find_signal(signals, "exposed_services", source="censys")

    # Merge ports from both sources
    all_ports = set()
    high_risk_found = {}

    if shodan_svc:
        ports = shodan_svc.get("value", {}).get("ports", [])
        all_ports.update(ports)
        for p in ports:
            if p in HIGH_RISK_PORTS:
                high_risk_found[p] = HIGH_RISK_PORTS[p]

    if censys_svc:
        services = censys_svc.get("value", {}).get("services", [])
        # Censys may report service names instead of ports
        censys_hosts = censys_svc.get("value", {}).get("total_hosts", 0)

    # Vulnerabilities
    vuln_signal = _find_signal(signals, "known_vulnerabilities")
    cves = vuln_signal.get("value", {}).get("cves", []) if vuln_signal else []

    # Subdomains
    subdomain_signal = _find_signal(signals, "subdomain_count")
    subdomain_count = subdomain_signal.get("value", {}).get("count", 0) if subdomain_signal else 0
    subdomain_sample = subdomain_signal.get("value", {}).get("sample", []) if subdomain_signal else []

    # DNS issues
    dns_signal = _find_signal(signals, "dns_misconfigurations")
    dns_issues = dns_signal.get("value", {}).get("issues", []) if dns_signal else []

    # Tech footprint & missing defenses
    tech_signal = _find_signal(signals, "technology_footprint")
    security_signal = _find_signal(signals, "security_tools_detected")

    tech_count = tech_signal.get("value", {}).get("total", 0) if tech_signal else 0
    security_tools = security_signal.get("value", {}).get("tools", []) if security_signal else []
    has_security_tools = security_signal.get("value", {}).get("count", 0) > 0 if security_signal else False

    # Determine missing defenses
    missing_defenses = []
    if security_signal and not has_security_tools:
        missing_defenses.append("No WAF or CDN security detected")
    if "Missing SPF record" in dns_issues:
        missing_defenses.append("No SPF record (email spoofing risk)")
    if "Missing DMARC record" in dns_issues:
        missing_defenses.append("No DMARC record (email spoofing risk)")

    # Severity
    if high_risk_found or cves:
        severity = "critical"
    elif len(all_ports) > 10 or missing_defenses:
        severity = "high"
    elif len(all_ports) > 3 or subdomain_count > 50:
        severity = "medium"
    elif len(all_ports) > 0 or subdomain_count > 0:
        severity = "low"
    else:
        severity = "low"

    # Evidence lines
    evidence = []
    sources = set()
    if all_ports:
        evidence.append(f"Shodan: {len(all_ports)} open ports detected")
        sources.add("shodan")
    if high_risk_found:
        svc_list = ", ".join(f"{v} ({k})" for k, v in sorted(high_risk_found.items()))
        evidence.append(f"High-risk services: {svc_list}")
    if cves:
        evidence.append(f"{len(cves)} known CVEs: {', '.join(cves[:3])}")
        sources.add("shodan")
    if subdomain_count > 0:
        evidence.append(f"SecurityTrails: {subdomain_count} subdomains")
        sources.add("securitytrails")
    if dns_issues:
        evidence.append(f"DNS issues: {', '.join(dns_issues)}")
        sources.add("securitytrails")
    if tech_count > 0:
        evidence.append(f"BuiltWith: {tech_count} technologies in stack")
        sources.add("builtwith")
    if missing_defenses:
        evidence.append(f"Missing defenses: {', '.join(missing_defenses)}")
    if censys_svc:
        sources.add("censys")

    return {
        "severity": severity,
        "exposed_ports": sorted(all_ports),
        "high_risk_services": high_risk_found,
        "cves": cves,
        "subdomain_count": subdomain_count,
        "subdomain_sample": subdomain_sample[:10],
        "dns_issues": dns_issues,
        "tech_count": tech_count,
        "security_tools": security_tools,
        "missing_defenses": missing_defenses,
        "evidence": evidence,
        "sources": sorted(sources),
    }


# ---------------------------------------------------------------------------
# Finding 3: Remediation Priorities
# ---------------------------------------------------------------------------

def _build_remediation_priorities(cred: dict, surface: dict, signals: list[dict]) -> list[dict]:
    """Generate prioritized remediation items from correlated findings."""
    items = []
    priority = 0

    # Credential remediation
    if cred["confirmed_passwords"] > 0:
        priority += 1
        items.append({
            "priority": priority,
            "title": f"Rotate exposed credentials ({cred['confirmed_passwords']} accounts with passwords exposed)",
            "category": "credential",
            "severity": "critical",
            "evidence": [e for e in cred["evidence"] if "password" in e.lower() or "credential" in e.lower()],
            "sources": cred["sources"],
        })

    if cred["stealer_log_hits"] > 0:
        priority += 1
        items.append({
            "priority": priority,
            "title": f"Investigate infostealer compromise ({cred['stealer_log_hits']} credentials harvested by malware)",
            "category": "credential",
            "severity": "critical",
            "evidence": [e for e in cred["evidence"] if "stealer" in e.lower() or "malware" in e.lower()],
            "sources": ["leakcheck"],
        })

    if cred["total_emails_exposed"] > 0 and cred["confirmed_passwords"] == 0:
        priority += 1
        items.append({
            "priority": priority,
            "title": f"Review {cred['total_emails_exposed']} exposed employee emails for credential reuse",
            "category": "credential",
            "severity": "high" if cred["total_emails_exposed"] >= 20 else "medium",
            "evidence": [e for e in cred["evidence"] if "email" in e.lower()],
            "sources": ["dehashed"],
        })

    # High-risk service remediation
    for port, service in sorted(surface.get("high_risk_services", {}).items()):
        priority += 1
        items.append({
            "priority": priority,
            "title": f"Restrict or close {service} on port {port}",
            "category": "infrastructure",
            "severity": "critical" if port in (3389, 445, 23) else "high",
            "evidence": [f"Port {port} ({service}) is publicly accessible"],
            "sources": ["shodan"],
        })

    # CVE remediation
    if surface["cves"]:
        priority += 1
        items.append({
            "priority": priority,
            "title": f"Patch {len(surface['cves'])} known vulnerabilities ({', '.join(surface['cves'][:3])})",
            "category": "infrastructure",
            "severity": "critical",
            "evidence": [f"{len(surface['cves'])} CVEs detected on exposed services"],
            "sources": ["shodan"],
        })

    # DNS/email security remediation
    for issue in surface.get("dns_issues", []):
        priority += 1
        items.append({
            "priority": priority,
            "title": f"Implement {issue.replace('Missing ', '')}",
            "category": "email_security",
            "severity": "high",
            "evidence": [issue],
            "sources": ["securitytrails"],
        })

    # Missing defenses remediation
    if surface.get("missing_defenses"):
        for defense in surface["missing_defenses"]:
            if "SPF" in defense or "DMARC" in defense:
                continue  # Already covered by dns_issues
            priority += 1
            items.append({
                "priority": priority,
                "title": f"Deploy {defense.replace('No ', '').replace(' detected', '')}",
                "category": "perimeter",
                "severity": "medium",
                "evidence": [defense],
                "sources": ["builtwith"],
            })

    # If nothing found, add a clean item
    if not items:
        items.append({
            "priority": 1,
            "title": "No critical remediation items identified",
            "category": "none",
            "severity": "low",
            "evidence": ["No significant exposures detected across all sources"],
            "sources": [],
        })

    return items


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_signal(signals: list[dict], signal_type: str, source: str | None = None) -> dict | None:
    """Find a signal by type, optionally filtered by source."""
    for sig in signals:
        if sig.get("signal_type") == signal_type:
            if source is None or sig.get("source") == source:
                return sig
    return None
