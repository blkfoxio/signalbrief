"""OpenAI narrative generation service."""

import hashlib
import json
import logging

from django.conf import settings
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a cybersecurity presales strategist. Your role is to help security sales representatives prepare for prospect calls by interpreting breach exposure data and framing it as a credible, consultative conversation.

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

ACCEPTABLE FRAMING:
- "This type of exposure is often relevant in regulated environments like healthcare."
- "At your scale, identity exposure can be harder to track across SaaS tools."
- "Multiple breach appearances suggest a pattern worth investigating."

UNACCEPTABLE FRAMING:
- "You are violating HIPAA."
- "This proves the company has been compromised."
- "Attackers are inside the network right now."
- "Your employees are at immediate risk."

OUTPUT FORMAT:
Return a JSON object with exactly these 5 fields:
- headline: One compelling sentence summarizing the key finding (max 120 chars)
- executive_narrative: 2-3 sentences explaining what was found and why it matters for this company
- talk_track: 2-3 sentences a rep can say verbatim on a call to introduce the finding
- business_impact: 1-2 sentences connecting the finding to business risk relevant to the company's industry/size
- transition: 1 sentence bridging from the finding to how the rep's solution can help"""


def _build_user_prompt(company_context: dict, signals: list[dict]) -> str:
    """Build the user prompt from structured data."""
    signal_summary = []
    for sig in signals:
        signal_summary.append({
            "type": sig["signal_type"],
            "severity": sig["severity"],
            "title": sig["title"],
            "details": sig.get("value", {}),
        })

    payload = {
        "company_context": company_context,
        "security_signals": signal_summary,
    }

    return f"Generate a presales security narrative based on this evidence:\n\n{json.dumps(payload, indent=2)}"


async def generate_narrative(company_context: dict, signals: list[dict]) -> dict:
    """
    Generate AI narrative from structured company context and signals.
    Returns dict with headline, executive_narrative, talk_track, business_impact, transition.
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
            max_tokens=1000,
        )

        content = response.choices[0].message.content
        result = json.loads(content)

        # Validate all required fields present
        required_fields = ["headline", "executive_narrative", "talk_track", "business_impact", "transition"]
        for field in required_fields:
            if field not in result:
                result[field] = ""

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

    return {
        "headline": f"Security exposure data identified for {company_name}",
        "executive_narrative": f"Our analysis found {signal_count} security signal{'s' if signal_count != 1 else ''} associated with {company_name}. Review the detailed findings below for specifics.",
        "talk_track": f"We ran a quick analysis on {company_name} and found some exposure data that might be worth discussing. Let me walk you through what we found.",
        "business_impact": "Identity exposure across breach datasets can indicate credential reuse risk and may warrant review of access controls and monitoring.",
        "transition": "This is typically where we help teams get visibility into their exposure and tighten their response posture.",
        "model_used": "placeholder",
        "prompt_hash": "",
    }
