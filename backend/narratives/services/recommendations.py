"""
Service-bucket recommendations.

Maps correlated OSINT findings to Cyflare's four service buckets (XDR, EDR, VSS, ES).
The selection is deterministic — rules in this module decide which buckets apply
and at what priority. The LLM is responsible only for writing a one-sentence
rationale per selected recommendation, citing the evidence we surface here.

Why deterministic: the customer wants predictable, defensible recommendations
that map cleanly to evidence. LLM-only selection drifts and hallucinates services.
"""

SERVICE_CATALOG = {
    "ES": {
        "code": "ES",
        "name": "Email Security",
        "tagline": "Phishing defense, mailbox protection, and email-auth enforcement (SPF / DKIM / DMARC).",
    },
    "EDR": {
        "code": "EDR",
        "name": "Endpoint Detection & Response",
        "tagline": "Detects and contains malware, infostealers, and post-compromise activity on endpoints.",
    },
    "VSS": {
        "code": "VSS",
        "name": "Vulnerability Scanning Services",
        "tagline": "Continuous external scanning for exposed services, open ports, and known CVEs.",
    },
    "XDR": {
        "code": "XDR",
        "name": "Extended Detection & Response",
        "tagline": "Unified detection across email, endpoint, network, and identity for multi-vector exposure.",
    },
}

_PRIORITY_RANK = {"medium": 0, "high": 1, "critical": 2}


def select_recommendations(correlated: dict) -> list[dict]:
    """
    Pick which service buckets to recommend based on correlated findings.

    Returns a list of dicts:
        {
            "code": "ES" | "EDR" | "VSS" | "XDR",
            "name": str,
            "tagline": str,
            "priority": "medium" | "high" | "critical",
            "triggers": [short evidence strings],
        }

    Empty list if no findings warrant a recommendation. XDR is suppressed unless
    two or more of {ES, EDR, VSS} fire — it's the consolidation play, not a
    default add-on.
    """
    cred = correlated.get("credential_exposure", {}) or {}
    surface = correlated.get("attack_surface", {}) or {}

    selected: dict[str, dict] = {}

    # ---- ES ----------------------------------------------------------------
    es_triggers: list[str] = []
    es_priority = "medium"
    missing_defenses = surface.get("missing_defenses", []) or []
    has_dmarc_gap = any("DMARC" in d or "SPF" in d for d in missing_defenses)
    if has_dmarc_gap:
        es_triggers.append("Missing email-authentication records (SPF/DMARC) — domain spoofable.")
        es_priority = "high"
    if cred.get("stealer_log_hits", 0) > 0:
        es_triggers.append(
            f"{cred['stealer_log_hits']} credentials harvested by infostealer malware — phishing is the typical delivery vector."
        )
        es_priority = "high"
    if cred.get("confirmed_passwords", 0) > 0:
        es_triggers.append(
            f"{cred['confirmed_passwords']} confirmed exposed passwords from breach data."
        )
    if cred.get("total_emails_exposed", 0) >= 10:
        es_triggers.append(
            f"{cred['total_emails_exposed']} employee mailboxes appear in breach data — high phishing target value."
        )
    if es_triggers:
        selected["ES"] = {
            **SERVICE_CATALOG["ES"],
            "priority": es_priority,
            "triggers": es_triggers,
        }

    # ---- EDR ---------------------------------------------------------------
    edr_triggers: list[str] = []
    edr_priority = "medium"
    if cred.get("stealer_log_hits", 0) > 0:
        edr_triggers.append(
            f"{cred['stealer_log_hits']} credentials in infostealer logs — those records exist because malware ran on an endpoint."
        )
        edr_priority = "critical"
    if cred.get("repeated_exposures", 0) >= 3:
        edr_triggers.append(
            f"{cred['repeated_exposures']} identities exposed across multiple breaches — pattern consistent with recurring endpoint compromise."
        )
    if edr_triggers:
        selected["EDR"] = {
            **SERVICE_CATALOG["EDR"],
            "priority": edr_priority,
            "triggers": edr_triggers,
        }

    # ---- VSS ---------------------------------------------------------------
    vss_triggers: list[str] = []
    vss_priority = "medium"
    cves = surface.get("cves") or []
    high_risk_services = surface.get("high_risk_services") or {}
    if cves:
        vss_triggers.append(
            f"{len(cves)} known CVEs detected on internet-facing services."
        )
        vss_priority = "critical"
    if high_risk_services:
        svc_list = ", ".join(f"{name} ({port})" for port, name in sorted(high_risk_services.items()))
        vss_triggers.append(f"High-risk services exposed to the public internet: {svc_list}.")
        if vss_priority != "critical":
            vss_priority = "high"
    if surface.get("subdomain_count", 0) >= 25:
        vss_triggers.append(
            f"{surface['subdomain_count']} subdomains in scope — large external surface that needs continuous coverage."
        )
    if vss_triggers:
        selected["VSS"] = {
            **SERVICE_CATALOG["VSS"],
            "priority": vss_priority,
            "triggers": vss_triggers,
        }

    # ---- XDR (consolidation play; only if multi-vector) --------------------
    point_buckets = [c for c in ("ES", "EDR", "VSS") if c in selected]
    if len(point_buckets) >= 2:
        xdr_triggers = [
            f"Findings span {len(point_buckets)} domains ({', '.join(point_buckets)}) — unified detection collapses these into a single response surface."
        ]
        # Match severity if any fired bucket is critical
        any_critical = any(selected[b]["priority"] == "critical" for b in point_buckets)
        any_high = any(selected[b]["priority"] == "high" for b in point_buckets)
        if any_critical:
            xdr_priority = "critical"
        elif any_high:
            xdr_priority = "high"
        else:
            xdr_priority = "medium"
        selected["XDR"] = {
            **SERVICE_CATALOG["XDR"],
            "priority": xdr_priority,
            "triggers": xdr_triggers,
        }

    # Order by priority (critical first), then by stable bucket order.
    bucket_order = ["XDR", "EDR", "VSS", "ES"]
    ordered = sorted(
        selected.values(),
        key=lambda r: (-_PRIORITY_RANK.get(r["priority"], 0), bucket_order.index(r["code"])),
    )
    return ordered
