"""OpenAI narrative generation service — multi-category security intelligence."""

import hashlib
import json
import logging

from django.conf import settings
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a cybersecurity presales strategist. Your role is to help security sales representatives prepare for prospect calls by interpreting multi-source security intelligence and framing it as a credible, consultative conversation.

You will receive signals from up to 4 intelligence categories:
1. BREACH INTELLIGENCE (DeHashed, HIBP, LeakCheck) — credential exposure, breach history, stealer logs
2. INFRASTRUCTURE EXPOSURE (Shodan, Censys) — exposed services, ports, certificates, vulnerabilities
3. ATTACK SURFACE (SecurityTrails) — DNS footprint, subdomains, email security misconfigurations
4. TECHNOLOGY FOOTPRINT (BuiltWith) — tech stack size, security tool presence/absence

RULES:
- Use ONLY the provided evidence. Never invent facts or statistics.
- Adapt messaging to the prospect's industry when confidence is sufficient.
- Adjust tone to company size when available.
- Write in concise, plain language suitable for scanning quickly.
- Avoid hallucinations, exaggerated claims, and fear-based messaging.
- Never make definitive compliance accusations (e.g., "You are violating HIPAA").
- Never claim the company has been actively compromised unless the data proves it.
- Frame findings as risk indicators, not conclusions.
- Keep all outputs short and actionable — reps will use these on live calls.
- Reference specific CVEs only when they appear in the signal data.
- Note technology gaps (e.g., "No WAF detected") as observations, not accusations.
- When signals from multiple categories overlap, correlate them (e.g., "exposed RDP + credential exposure = elevated risk").
- Only include category findings for categories that have signal data. Leave others empty.

ACCEPTABLE FRAMING:
- "This type of exposure is often relevant in regulated environments like healthcare."
- "At your scale, identity exposure can be harder to track across SaaS tools."
- "Multiple breach appearances suggest a pattern worth investigating."
- "Open services combined with credential exposure may indicate elevated risk."
- "The absence of common perimeter defenses may present an opportunity to discuss security posture."

UNACCEPTABLE FRAMING:
- "You are violating HIPAA."
- "This proves the company has been compromised."
- "Attackers are inside the network right now."
- "Your employees are at immediate risk."
- Any claim about active exploitation without direct evidence.

OUTPUT FORMAT:
Return a JSON object with exactly these fields:
- headline: One compelling sentence summarizing the key finding across all categories (max 120 chars)
- risk_summary: 2-3 sentence executive overview synthesizing findings across ALL available categories
- category_findings: Object with up to 4 keys. Only include categories that have relevant signals:
  - breach_intelligence: 1-2 sentences on credential/breach exposure (if signals exist)
  - infrastructure_exposure: 1-2 sentences on exposed services/certs (if signals exist)
  - attack_surface: 1-2 sentences on DNS/subdomain exposure (if signals exist)
  - technology_footprint: 1-2 sentences on tech stack observations (if signals exist)
- executive_narrative: 2-3 sentences explaining findings for executive audience
- talk_track: 3-4 sentences a rep can say verbatim on a call, referencing key findings
- business_impact: 2-3 sentences connecting findings to business risk relevant to industry/size
- transition: 1 sentence bridging from findings to how the rep's solution can help"""


# Map signal types to categories for prompt organization
SIGNAL_CATEGORIES = {
    "breach_intelligence": [
        "employee_emails_exposed", "breach_events", "password_exposure",
        "repeated_identity_exposure", "stealer_log_exposure",
        "credential_market_presence", "known_breaches", "breach_recency",
        "sensitive_breach_exposure",
    ],
    "infrastructure_exposure": [
        "exposed_services", "known_vulnerabilities", "outdated_software",
        "expired_certificates", "weak_encryption", "certificate_transparency",
    ],
    "attack_surface": [
        "subdomain_count", "dns_misconfigurations", "historical_dns_changes",
    ],
    "technology_footprint": [
        "technology_footprint", "security_tools_detected", "outdated_technologies",
    ],
}


def _categorize_signals(signals: list[dict]) -> dict:
    """Group signals by intelligence category for prompt clarity."""
    categorized = {}
    for category, types in SIGNAL_CATEGORIES.items():
        category_signals = [s for s in signals if s.get("signal_type") in types]
        if category_signals:
            categorized[category] = category_signals
    return categorized


def _build_user_prompt(company_context: dict, signals: list[dict]) -> str:
    """Build the user prompt from structured data, organized by category."""
    signal_summary = []
    for sig in signals:
        signal_summary.append({
            "type": sig["signal_type"],
            "source": sig.get("source", "unknown"),
            "severity": sig["severity"],
            "title": sig["title"],
            "details": sig.get("value", {}),
        })

    # Group by category for clearer prompt
    categorized = _categorize_signals(signals)
    categories_present = list(categorized.keys())

    payload = {
        "company_context": company_context,
        "categories_with_data": categories_present,
        "security_signals": signal_summary,
    }

    return f"Generate a presales security narrative based on this multi-source evidence:\n\n{json.dumps(payload, indent=2)}"


async def generate_narrative(company_context: dict, signals: list[dict]) -> dict:
    """
    Generate AI narrative from structured company context and multi-source signals.
    Returns dict with headline, risk_summary, category_findings, executive_narrative,
    talk_track, business_impact, transition.
    """
    if not settings.OPENAI_API:
        logger.warning("OPENAI_API key not configured, returning placeholder narrative")
        return _placeholder_narrative(company_context, signals)

    user_prompt = _build_user_prompt(company_context, signals)
    prompt_hash = hashlib.sha256(user_prompt.encode()).hexdigest()[:16]
    model = settings.OPENAI_MODEL

    try:
        client = AsyncOpenAI(api_key=settings.OPENAI_API)

        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.4,
            max_tokens=2000,
        )

        content = response.choices[0].message.content
        result = json.loads(content)

        # Validate all required fields present
        required_fields = [
            "headline", "risk_summary", "category_findings",
            "executive_narrative", "talk_track", "business_impact", "transition",
        ]
        for field in required_fields:
            if field not in result:
                result[field] = "" if field != "category_findings" else {}

        result["model_used"] = model
        result["prompt_hash"] = prompt_hash
        return result

    except Exception as e:
        logger.exception(f"OpenAI narrative generation failed: {e}")
        return _placeholder_narrative(company_context, signals)


def _placeholder_narrative(company_context: dict, signals: list[dict]) -> dict:
    """Fallback narrative when OpenAI is unavailable."""
    company_name = company_context.get("company_name", "this company")
    signal_count = len([s for s in signals if s.get("signal_type") != "no_data"])

    # Determine which categories have data
    categorized = _categorize_signals(signals)
    category_descriptions = {
        "breach_intelligence": "credential and breach exposure data",
        "infrastructure_exposure": "exposed infrastructure and services",
        "attack_surface": "DNS and subdomain intelligence",
        "technology_footprint": "technology stack observations",
    }
    active_categories = [category_descriptions[c] for c in categorized.keys()]

    return {
        "headline": f"Security exposure data identified for {company_name}",
        "risk_summary": f"Our analysis found {signal_count} security signal{'s' if signal_count != 1 else ''} across {len(active_categories)} intelligence categor{'ies' if len(active_categories) != 1 else 'y'} for {company_name}.",
        "category_findings": {
            cat: f"Signals detected in {category_descriptions.get(cat, cat)}."
            for cat in categorized.keys()
        },
        "executive_narrative": f"Our analysis found {signal_count} security signal{'s' if signal_count != 1 else ''} associated with {company_name} covering {', '.join(active_categories) if active_categories else 'breach data'}. Review the detailed findings below for specifics.",
        "talk_track": f"We ran a comprehensive analysis on {company_name} and found some exposure data across {len(active_categories)} area{'s' if len(active_categories) != 1 else ''} that might be worth discussing. Let me walk you through what we found.",
        "business_impact": "Multi-source exposure across breach data, infrastructure, and attack surface can indicate systemic security gaps that may warrant review of access controls, perimeter defenses, and monitoring.",
        "transition": "This is typically where we help teams get visibility into their exposure and tighten their response posture.",
        "model_used": "placeholder",
        "prompt_hash": "",
    }
