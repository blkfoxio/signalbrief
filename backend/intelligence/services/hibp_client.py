"""Have I Been Pwned (HIBP) API async client.

NOT currently called from the analysis pipeline. Domain search on HIBP requires
HIBP Pro plus ownership verification of the queried domain (DNS TXT record,
verification email, file upload, or meta tag). Pre-sales reports cannot meet
that prerequisite, so this client stays dormant until a verification flow is
added (see https://haveibeenpwned.com/API/v3#DomainSearchOverview and the
domain-verification API at /api/v3/domainverification/dns).

Endpoint reference for future re-enablement: GET /api/v3/breacheddomain/{domain}
returns breaches scoped to a verified domain.
"""

import logging

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

HIBP_DOMAIN_SEARCH_URL = "https://haveibeenpwned.com/api/v3/breacheddomain"


async def search_by_domain(domain: str) -> dict:
    """
    Search HIBP for breaches scoped to a verified domain.

    Requires HIBP Pro and prior domain ownership verification. Without
    verification HIBP returns 401/403; this client is intentionally not wired
    into the pipeline until verification is supported.
    """
    if not settings.HIBP_API:
        logger.warning("HIBP_API key not configured, skipping")
        return {"breaches": [], "error": "API key not configured"}

    headers = {
        "hibp-api-key": settings.HIBP_API,
        "user-agent": "SignalBrief",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{HIBP_DOMAIN_SEARCH_URL}/{domain}",
                headers=headers,
            )

            if response.status_code == 404:
                return {"breaches": [], "total": 0}

            if response.status_code == 429:
                logger.warning("HIBP rate limit hit")
                return {"breaches": [], "error": "Rate limit exceeded"}

            if response.status_code in (401, 403):
                logger.warning("HIBP unauthorized (domain not verified or API key invalid)")
                return {"breaches": [], "error": "Unauthorized (domain verification required)"}

            response.raise_for_status()
            breaches = response.json()

            return {
                "breaches": breaches,
                "total": len(breaches),
            }

    except httpx.HTTPStatusError as e:
        logger.error(f"HIBP HTTP error {e.response.status_code}: {e}")
        return {"breaches": [], "error": f"HTTP {e.response.status_code}"}
    except httpx.RequestError as e:
        logger.error(f"HIBP request error: {e}")
        return {"breaches": [], "error": "Request failed"}
