"""Have I Been Pwned (HIBP) API async client."""

import logging

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

HIBP_BREACHES_URL = "https://haveibeenpwned.com/api/v3/breaches"
HIBP_DOMAIN_SEARCH_URL = "https://haveibeenpwned.com/api/v3/breaches"


async def search_by_domain(domain: str) -> dict:
    """
    Search HIBP for breaches associated with a domain.
    Uses the breaches endpoint filtered by domain.
    Returns dict with breaches list and metadata.
    """
    if not settings.HIBP_API:
        logger.warning("HIBP_API key not configured, skipping")
        return {"breaches": [], "error": "API key not configured"}

    headers = {
        "hibp-api-key": settings.HIBP_API,
        "user-agent": "SignalBrief",
    }

    params = {"domain": domain}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                HIBP_BREACHES_URL,
                headers=headers,
                params=params,
            )

            if response.status_code == 404:
                return {"breaches": [], "total": 0}

            if response.status_code == 429:
                logger.warning("HIBP rate limit hit")
                return {"breaches": [], "error": "Rate limit exceeded"}

            if response.status_code == 401:
                logger.warning("HIBP unauthorized - check API key")
                return {"breaches": [], "error": "Unauthorized"}

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
