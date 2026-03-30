"""OpenAI narrative generation — 3-finding correlated report output."""

import hashlib
import json
import logging

from django.conf import settings
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a cybersecurity presales strategist. You receive pre-correlated security findings from multiple OSINT sources and write concise, compelling narratives that help sales reps prepare for prospect calls.

You will receive 3 correlated findings:
1. CREDENTIAL EXPOSURE — confirmed passwords, stealer logs, breach history
2. ATTACK SURFACE — exposed services, subdomains, missing defenses, tech stack gaps
3. REMEDIATION PRIORITIES — prioritized action items with evidence

RULES:
- Use ONLY the provided evidence. Never invent facts or statistics.
- Adapt messaging to the prospect's industry when provided.
- Adjust tone to company size when available.
- Write in concise, plain language suitable for scanning quickly.
- Avoid hallucinations, exaggerated claims, and fear-based messaging.
- Never make definitive compliance accusations.
- Never claim active compromise unless the data proves it.
- Frame findings as risk indicators, not conclusions.
- When a finding has no significant data, acknowledge it briefly as a positive ("No exposed credentials were found").
- Correlate across findings when relevant (e.g., "exposed credentials combined with unprotected services elevate the risk").
- Keep all outputs short and actionable — reps will use these on live calls.

ACCEPTABLE FRAMING:
- "We found 25 employee credentials confirmed exposed, with 3 harvested by infostealer malware."
- "13 services are publicly visible, including RDP, with no WAF detected."
- "The combination of credential exposure and unprotected infrastructure suggests immediate attention is warranted."

UNACCEPTABLE FRAMING:
- "You are violating HIPAA."
- "Attackers are inside your network."
- "Your employees are at immediate risk."

OUTPUT FORMAT:
Return a JSON object with exactly these fields:
- headline: One sentence summarizing the most compelling finding (max 120 chars)
- findings: Object with exactly 3 keys:
  - credential_exposure:
    - summary: 2-3 sentences on what credentials are confirmed compromised
    - talk_track: 1-2 sentences a rep can say verbatim about this finding
  - attack_surface:
    - summary: 2-3 sentences on exposed infrastructure and defense gaps
    - talk_track: 1-2 sentences a rep can say verbatim about this finding
  - remediation:
    - summary: 2-3 sentences on what should be fixed first and why
    - talk_track: 1-2 sentences a rep can say verbatim about this finding
- executive_brief: 3-4 sentence overview a rep reads before picking up the phone
- transition: 1 sentence bridging from findings to how the rep's solution can help"""


def _build_user_prompt(company_context: dict, correlated: dict) -> str:
    """Build prompt from company context and pre-correlated findings."""
    payload = {
        "company_context": company_context,
        "correlated_findings": {
            "credential_exposure": {
                "severity": correlated["credential_exposure"]["severity"],
                "total_emails_exposed": correlated["credential_exposure"]["total_emails_exposed"],
                "confirmed_passwords": correlated["credential_exposure"]["confirmed_passwords"],
                "stealer_log_hits": correlated["credential_exposure"]["stealer_log_hits"],
                "breach_count": correlated["credential_exposure"]["breach_count"],
                "breach_names": correlated["credential_exposure"]["breach_names"],
                "repeated_exposures": correlated["credential_exposure"]["repeated_exposures"],
                "days_since_breach": correlated["credential_exposure"]["days_since_breach"],
                "evidence": correlated["credential_exposure"]["evidence"],
            },
            "attack_surface": {
                "severity": correlated["attack_surface"]["severity"],
                "exposed_ports": correlated["attack_surface"]["exposed_ports"],
                "high_risk_services": correlated["attack_surface"]["high_risk_services"],
                "cves": correlated["attack_surface"]["cves"],
                "subdomain_count": correlated["attack_surface"]["subdomain_count"],
                "dns_issues": correlated["attack_surface"]["dns_issues"],
                "missing_defenses": correlated["attack_surface"]["missing_defenses"],
                "tech_count": correlated["attack_surface"]["tech_count"],
                "evidence": correlated["attack_surface"]["evidence"],
            },
            "remediation_priorities": correlated["remediation_priorities"],
        },
    }

    return f"Generate a presales security narrative based on these correlated findings:\n\n{json.dumps(payload, indent=2)}"


async def generate_narrative(company_context: dict, correlated: dict) -> dict:
    """
    Generate AI narrative from company context and correlated findings.
    Returns dict with headline, findings, executive_brief, transition.
    """
    if not settings.OPENAI_API:
        logger.warning("OPENAI_API key not configured, returning placeholder narrative")
        return _placeholder_narrative(company_context, correlated)

    user_prompt = _build_user_prompt(company_context, correlated)
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

        # Validate structure
        if "findings" not in result:
            result["findings"] = {}
        for key in ("credential_exposure", "attack_surface", "remediation"):
            if key not in result["findings"]:
                result["findings"][key] = {"summary": "", "talk_track": ""}
            for field in ("summary", "talk_track"):
                if field not in result["findings"][key]:
                    result["findings"][key][field] = ""

        for field in ("headline", "executive_brief", "transition"):
            if field not in result:
                result[field] = ""

        result["model_used"] = model
        result["prompt_hash"] = prompt_hash
        return result

    except Exception as e:
        logger.exception(f"OpenAI narrative generation failed: {e}")
        return _placeholder_narrative(company_context, correlated)


def _placeholder_narrative(company_context: dict, correlated: dict) -> dict:
    """Fallback narrative when OpenAI is unavailable."""
    company_name = company_context.get("company_name", "this company")
    cred = correlated.get("credential_exposure", {})
    surface = correlated.get("attack_surface", {})
    remediation = correlated.get("remediation_priorities", [])

    total_creds = cred.get("total_exposed_credentials", 0)
    total_ports = len(surface.get("exposed_ports", []))
    total_items = len([r for r in remediation if r.get("severity") in ("critical", "high")])

    return {
        "headline": f"Security exposure data identified for {company_name}",
        "findings": {
            "credential_exposure": {
                "summary": f"{cred.get('total_emails_exposed', 0)} employee emails found in breach data with {total_creds} confirmed credential exposures." if total_creds > 0 else "No confirmed credential exposures were found in breach databases.",
                "talk_track": f"We found evidence of credential exposure for {company_name} that may warrant a review of access controls." if total_creds > 0 else f"Good news — we didn't find confirmed credential exposures for {company_name} in our sources.",
            },
            "attack_surface": {
                "summary": f"{total_ports} services are publicly visible." if total_ports > 0 else "No significant attack surface exposure was detected.",
                "talk_track": f"We identified some publicly visible infrastructure for {company_name} worth reviewing." if total_ports > 0 else f"The external attack surface for {company_name} appears limited based on our scan.",
            },
            "remediation": {
                "summary": f"{total_items} high-priority remediation items identified." if total_items > 0 else "No critical remediation items identified.",
                "talk_track": f"Based on our findings, there are {total_items} items we'd recommend addressing." if total_items > 0 else "No urgent action items were identified, but there may be areas to strengthen.",
            },
        },
        "executive_brief": f"Our analysis of {company_name} identified {total_creds} credential exposures and {total_ports} exposed services. Review the detailed findings below.",
        "transition": "This is typically where we help teams get visibility into their exposure and tighten their response posture.",
        "model_used": "placeholder",
        "prompt_hash": "",
    }
