"""
Correlation engine — merges signals from all OSINT sources into 3 business findings.

This is the "secret sauce": normalize + correlate + score across sources,
then hand pre-structured data to OpenAI for narrative generation.
"""

# Per-port context. risk_level is one of: expected, low, medium, high, critical.
# Ports tagged "expected" are normal web traffic and should not raise alarms.
PORT_CONTEXT = {
    21: {
        "service": "FTP",
        "risk_level": "high",
        "blurb": "File Transfer Protocol",
        "risk_note": "FTP transmits credentials in cleartext and is rarely needed externally; replace with SFTP or remove from the public internet.",
    },
    22: {
        "service": "SSH",
        "risk_level": "high",
        "blurb": "Remote shell access",
        "risk_note": "SSH exposed to the public internet invites credential-stuffing and brute-force; restrict by source IP, require key auth, or place behind a VPN.",
    },
    23: {
        "service": "Telnet",
        "risk_level": "critical",
        "blurb": "Legacy remote shell",
        "risk_note": "Telnet sends credentials in plaintext; there is no acceptable reason for it to be reachable from the internet.",
    },
    25: {
        "service": "SMTP",
        "risk_level": "medium",
        "blurb": "Mail transfer",
        "risk_note": "Public SMTP is expected for receiving mail servers, but open relays or unauthenticated submission ports get abused for spoofing and spam.",
    },
    80: {
        "service": "HTTP",
        "risk_level": "expected",
        "blurb": "Standard web traffic",
        "risk_note": "",
    },
    443: {
        "service": "HTTPS",
        "risk_level": "expected",
        "blurb": "Standard secure web traffic",
        "risk_note": "",
    },
    445: {
        "service": "SMB",
        "risk_level": "critical",
        "blurb": "Windows file sharing",
        "risk_note": "SMB on the public internet has been the entry point for major ransomware families (WannaCry, NotPetya). Should never be internet-reachable.",
    },
    1433: {
        "service": "MSSQL",
        "risk_level": "high",
        "blurb": "Microsoft SQL Server",
        "risk_note": "Direct database exposure dramatically expands the attack surface; databases should sit behind an application tier, not on the public internet.",
    },
    3306: {
        "service": "MySQL",
        "risk_level": "high",
        "blurb": "MySQL database",
        "risk_note": "Direct database exposure dramatically expands the attack surface; databases should sit behind an application tier, not on the public internet.",
    },
    3389: {
        "service": "RDP",
        "risk_level": "critical",
        "blurb": "Remote Desktop",
        "risk_note": "Public RDP enables credential-stuffing and brute-force at scale, and is one of the most common ransomware entry points; place behind a VPN or zero-trust gateway.",
    },
    5432: {
        "service": "PostgreSQL",
        "risk_level": "high",
        "blurb": "PostgreSQL database",
        "risk_note": "Direct database exposure dramatically expands the attack surface; databases should sit behind an application tier, not on the public internet.",
    },
    5900: {
        "service": "VNC",
        "risk_level": "critical",
        "blurb": "Remote desktop (VNC)",
        "risk_note": "VNC is frequently deployed without strong authentication and is heavily scanned for; should not be reachable from the internet.",
    },
    6379: {
        "service": "Redis",
        "risk_level": "high",
        "blurb": "Redis data store",
        "risk_note": "Redis ships with no authentication by default and has been exploited at scale when reachable externally.",
    },
    27017: {
        "service": "MongoDB",
        "risk_level": "high",
        "blurb": "MongoDB database",
        "risk_note": "Open MongoDB instances have been the source of mass-exposure incidents; databases should not be internet-reachable.",
    },
}

# Backward-compatible view used by remediation logic and existing callers.
HIGH_RISK_PORTS = {
    port: ctx["service"]
    for port, ctx in PORT_CONTEXT.items()
    if ctx["risk_level"] in ("high", "critical")
}

# Severity ordering for posture computation.
_SEVERITY_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}
_POSTURE_BY_RANK = {0: "low", 1: "moderate", 2: "elevated", 3: "high"}


def _compute_posture(*severities: str) -> str:
    """Map the worst severity across findings to an executive posture label."""
    ranks = [_SEVERITY_RANK.get(s, 0) for s in severities if s]
    return _POSTURE_BY_RANK[max(ranks)] if ranks else "low"


def _build_port_context(ports: list[int]) -> list[dict]:
    """Return per-port context for rendering and for the LLM prompt."""
    out = []
    for p in ports:
        ctx = PORT_CONTEXT.get(p)
        if ctx:
            out.append({
                "port": p,
                "service": ctx["service"],
                "risk_level": ctx["risk_level"],
                "blurb": ctx["blurb"],
                "risk_note": ctx["risk_note"],
            })
        else:
            out.append({
                "port": p,
                "service": "",
                "risk_level": "unknown",
                "blurb": "",
                "risk_note": "",
            })
    return out


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

    posture = _compute_posture(cred["severity"], surface["severity"])

    return {
        "credential_exposure": cred,
        "attack_surface": surface,
        "remediation_priorities": remediation,
        "posture": posture,
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

    # Per-breach detail (name + date + record count) so the card can show *which* breaches.
    hibp_raw = osint_results.get("hibp") or {}
    breach_details = [
        {
            "name": b.get("Name", ""),
            "title": b.get("Title", b.get("Name", "")),
            "breach_date": b.get("BreachDate", ""),
            "pwn_count": b.get("PwnCount", 0),
            "data_classes": b.get("DataClasses", []) or [],
        }
        for b in (hibp_raw.get("breaches") or [])
    ][:20]

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
        "breach_details": breach_details,
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
    """Merge Shodan + Censys + BuiltWith into attack surface view."""

    # Exposed services (Shodan + Censys)
    shodan_svc = _find_signal(signals, "exposed_services", source="shodan")
    censys_svc = _find_signal(signals, "exposed_services", source="censys")

    # Pull host identifiers (IP + hostnames) from raw Shodan response so the
    # finding card can show *which* host the ports/CVEs belong to.
    shodan_raw = osint_results.get("shodan") or {}
    shodan_hosts_raw = shodan_raw.get("hosts") or []
    primary_host = shodan_hosts_raw[0] if shodan_hosts_raw else {}
    host_ip = shodan_raw.get("ip") or primary_host.get("ip_str") or ""
    hostnames = list(primary_host.get("hostnames") or [])

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

    # Subdomains and DNS posture: no source currently feeds these; kept as
    # empty fields so downstream consumers (frontend, PDF, narrative prompt)
    # don't break. Re-introduce when a subdomain/DNS source is added.
    subdomain_count = 0
    subdomain_sample: list = []
    dns_issues: list = []

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

    # Severity
    if high_risk_found or cves:
        severity = "critical"
    elif len(all_ports) > 10 or missing_defenses:
        severity = "high"
    elif len(all_ports) > 3:
        severity = "medium"
    elif len(all_ports) > 0:
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
    if tech_count > 0:
        evidence.append(f"BuiltWith: {tech_count} technologies in stack")
        sources.add("builtwith")
    if missing_defenses:
        evidence.append(f"Missing defenses: {', '.join(missing_defenses)}")
    if censys_svc:
        sources.add("censys")

    sorted_ports = sorted(all_ports)

    return {
        "severity": severity,
        "host_ip": host_ip,
        "hostnames": hostnames,
        "exposed_ports": sorted_ports,
        "port_context": _build_port_context(sorted_ports),
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

    # Missing defenses remediation
    if surface.get("missing_defenses"):
        for defense in surface["missing_defenses"]:
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
