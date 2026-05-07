"""OpenAI narrative generation — 3-finding correlated report output."""

import hashlib
import json
import logging

from django.conf import settings
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a cybersecurity presales strategist. You receive pre-correlated security findings from multiple OSINT sources and write concise, compelling narratives that help sales reps prepare for prospect calls.

You will receive:
- 3 correlated findings: CREDENTIAL EXPOSURE, ATTACK SURFACE, REMEDIATION PRIORITIES
- A list of pre-selected service recommendations (XDR / EDR / VSS / ES) chosen by deterministic rules — your job is to write a one-sentence rationale for each, citing evidence from the findings
- Per-port context for any open ports, including which ports are expected (80, 443) and which carry real risk

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

PORT FRAMING:
- Treat ports 80 and 443 as expected web traffic. Do NOT flag them as risks. Do not list them as exposures in narrative prose.
- When discussing ports, name the SERVICE (RDP, SMB, MySQL, SSH) and the BUSINESS CONSEQUENCE (e.g., "RDP exposed to the internet enables credential-stuffing"). Avoid generic "this port is open" phrasing.
- If only ports 80/443 are open, frame the network attack surface as well-contained.
- Use the port_context list provided in attack_surface to ground your prose; only call out ports with risk_level of medium, high, or critical.

RECOMMENDATION RATIONALES:
- For each recommendation in `recommendations`, write a 1–2 sentence `rationale` that ties the service to the specific evidence (the `triggers` array) for THIS prospect.
- Do not pitch services that aren't in the input list. Do not invent new services.
- Do not stack scare words; describe the gap and what the service does about it.

ACCEPTABLE FRAMING:
- "We found 25 employee credentials confirmed exposed, with 3 harvested by infostealer malware."
- "RDP is reachable from the public internet, which is one of the most common ransomware entry points."
- "The combination of credential exposure and unprotected infrastructure suggests immediate attention is warranted."

UNACCEPTABLE FRAMING:
- "You are violating HIPAA."
- "Attackers are inside your network."
- "Your employees are at immediate risk."
- "Port 443 is open — this is a serious risk." (443 is expected.)

OUTPUT FORMAT:
Return a JSON object with exactly these fields:
- headline: One sentence summarizing the most compelling finding (max 120 chars)
- executive_summary: Object with these keys:
  - key_risks: Array of 2–4 short bullets (≤90 chars each), each tied to evidence. If there are no significant risks, return a single positive bullet.
  - business_impact: 1–2 plain-English sentences on what these findings mean for the business. No scare tactics, no compliance accusations.
  - top_actions: Array of 2–3 short imperative bullets describing what to do next. Action language only, no product names.
- findings: Object with exactly 3 keys:
  - credential_exposure:
    - summary: 2-3 sentences on what credentials are confirmed compromised
    - talk_track: 1-2 sentences a rep can say verbatim about this finding
  - attack_surface:
    - summary: 2-3 sentences on exposed infrastructure and defense gaps. Apply the PORT FRAMING rules above.
    - talk_track: 1-2 sentences a rep can say verbatim about this finding
  - remediation:
    - summary: 2-3 sentences on what should be fixed first and why
    - talk_track: 1-2 sentences a rep can say verbatim about this finding
- recommendation_rationales: Object keyed by recommendation `code` (XDR / EDR / VSS / ES). Each value is a string of 1–2 sentences explaining why this service fits THIS prospect, citing the triggers. Only include codes that appear in the input recommendations list.
- executive_brief: 3-4 sentence overview a rep reads before picking up the phone (kept for backward compatibility with older renderers; should be consistent with executive_summary)
- transition: 1 sentence bridging from findings to how the rep's solution can help"""


def _build_user_prompt(company_context: dict, correlated: dict, recommendations: list[dict]) -> str:
    """Build prompt from company context, correlated findings, and rule-selected recommendations."""
    surface = correlated["attack_surface"]
    payload = {
        "company_context": company_context,
        "posture": correlated.get("posture", "low"),
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
                "severity": surface["severity"],
                "exposed_ports": surface["exposed_ports"],
                "port_context": surface.get("port_context", []),
                "high_risk_services": surface["high_risk_services"],
                "cves": surface["cves"],
                "subdomain_count": surface["subdomain_count"],
                "dns_issues": surface["dns_issues"],
                "missing_defenses": surface["missing_defenses"],
                "tech_count": surface["tech_count"],
                "evidence": surface["evidence"],
            },
            "remediation_priorities": correlated["remediation_priorities"],
        },
        "recommendations": [
            {"code": r["code"], "name": r["name"], "priority": r["priority"], "triggers": r["triggers"]}
            for r in recommendations
        ],
    }

    return f"Generate a presales security narrative based on these correlated findings:\n\n{json.dumps(payload, indent=2)}"


async def generate_narrative(company_context: dict, correlated: dict, recommendations: list[dict] | None = None) -> dict:
    """
    Generate AI narrative from company context, correlated findings, and rule-selected recommendations.
    Returns dict with headline, executive_summary, findings, recommendations (with rationales),
    executive_brief, transition.
    """
    recommendations = recommendations or []

    if not settings.OPENAI_API:
        logger.warning("OPENAI_API key not configured, returning placeholder narrative")
        return _placeholder_narrative(company_context, correlated, recommendations)

    user_prompt = _build_user_prompt(company_context, correlated, recommendations)
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
            max_tokens=2200,
        )

        content = response.choices[0].message.content
        result = json.loads(content)

        # Validate findings shape
        if "findings" not in result:
            result["findings"] = {}
        for key in ("credential_exposure", "attack_surface", "remediation"):
            if key not in result["findings"]:
                result["findings"][key] = {"summary": "", "talk_track": ""}
            for field in ("summary", "talk_track"):
                if field not in result["findings"][key]:
                    result["findings"][key][field] = ""

        # Validate executive_summary shape
        exec_summary = result.get("executive_summary") or {}
        result["executive_summary"] = {
            "key_risks": exec_summary.get("key_risks") or [],
            "business_impact": exec_summary.get("business_impact", ""),
            "top_actions": exec_summary.get("top_actions") or [],
        }

        # Merge LLM rationales into recommendations list (keeps shape stable)
        rationales = result.get("recommendation_rationales") or {}
        merged_recs = []
        for r in recommendations:
            merged_recs.append({
                **r,
                "rationale": rationales.get(r["code"], "") or rationales.get(r["code"].lower(), ""),
            })
        result["recommendations"] = merged_recs
        # Drop the intermediate dict so consumers see one canonical shape.
        result.pop("recommendation_rationales", None)

        for field in ("headline", "executive_brief", "transition"):
            if field not in result:
                result[field] = ""

        result["model_used"] = model
        result["prompt_hash"] = prompt_hash
        return result

    except Exception as e:
        logger.exception(f"OpenAI narrative generation failed: {e}")
        return _placeholder_narrative(company_context, correlated, recommendations)


def _placeholder_narrative(company_context: dict, correlated: dict, recommendations: list[dict]) -> dict:
    """Fallback narrative when OpenAI is unavailable."""
    company_name = company_context.get("company_name", "this company")
    cred = correlated.get("credential_exposure", {})
    surface = correlated.get("attack_surface", {})
    remediation = correlated.get("remediation_priorities", [])

    total_creds = cred.get("total_exposed_credentials", 0)
    risky_ports = [
        p for p in surface.get("port_context", [])
        if p.get("risk_level") in ("medium", "high", "critical")
    ]
    total_items = len([r for r in remediation if r.get("severity") in ("critical", "high")])

    key_risks = []
    if total_creds > 0:
        key_risks.append(f"{total_creds} confirmed credential exposures")
    if risky_ports:
        names = ", ".join(p["service"] or str(p["port"]) for p in risky_ports[:3])
        key_risks.append(f"Risky services exposed: {names}")
    if surface.get("missing_defenses"):
        key_risks.append(surface["missing_defenses"][0])
    if not key_risks:
        key_risks.append("No significant exposures detected")

    placeholder_recs = [
        {**r, "rationale": f"Recommended based on: {r['triggers'][0]}" if r.get("triggers") else ""}
        for r in recommendations
    ]

    return {
        "headline": f"Security exposure data identified for {company_name}",
        "executive_summary": {
            "key_risks": key_risks[:4],
            "business_impact": (
                f"Our analysis surfaced indicators worth reviewing with {company_name}'s team."
                if (total_creds or risky_ports or surface.get("missing_defenses"))
                else f"{company_name}'s external posture appears well-contained based on current OSINT."
            ),
            "top_actions": (
                ["Rotate exposed credentials", "Reduce internet-facing services", "Close email-auth gaps"][:3]
                if (total_creds or risky_ports or surface.get("missing_defenses"))
                else ["Maintain current controls", "Schedule a periodic re-scan"]
            ),
        },
        "findings": {
            "credential_exposure": {
                "summary": f"{cred.get('total_emails_exposed', 0)} employee emails found in breach data with {total_creds} confirmed credential exposures." if total_creds > 0 else "No confirmed credential exposures were found in breach databases.",
                "talk_track": f"We found evidence of credential exposure for {company_name} that may warrant a review of access controls." if total_creds > 0 else f"Good news — we didn't find confirmed credential exposures for {company_name} in our sources.",
            },
            "attack_surface": {
                "summary": f"{len(risky_ports)} services with elevated risk are publicly visible." if risky_ports else "No significant attack surface exposure was detected beyond standard web traffic.",
                "talk_track": f"We identified internet-facing services for {company_name} worth reviewing." if risky_ports else f"The external attack surface for {company_name} appears limited based on our scan.",
            },
            "remediation": {
                "summary": f"{total_items} high-priority remediation items identified." if total_items > 0 else "No critical remediation items identified.",
                "talk_track": f"Based on our findings, there are {total_items} items we'd recommend addressing." if total_items > 0 else "No urgent action items were identified, but there may be areas to strengthen.",
            },
        },
        "recommendations": placeholder_recs,
        "executive_brief": f"Our analysis of {company_name} identified {total_creds} credential exposures and {len(risky_ports)} elevated-risk services. Review the detailed findings below.",
        "transition": "This is typically where we help teams get visibility into their exposure and tighten their response posture.",
        "model_used": "placeholder",
        "prompt_hash": "",
    }
