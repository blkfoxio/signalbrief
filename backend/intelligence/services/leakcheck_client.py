"""LeakCheck API async client for stealer log intelligence."""

import logging

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

LEAKCHECK_URL = "https://leakcheck.io/api/v2/query"


async def search_by_domain(domain: str) -> dict:
    """
    Search LeakCheck for stealer log entries by domain.
    Returns dict with results list and metadata.
    """
    if not settings.LEAKCHECK_API:
        logger.warning("LEAKCHECK_API key not configured, skipping")
        return {"results": [], "error": "API key not configured"}

    headers = {
        "X-API-Key": settings.LEAKCHECK_API,
    }

    params = {
        "query": domain,
        "type": "domain",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                LEAKCHECK_URL,
                headers=headers,
                params=params,
            )

            if response.status_code == 404:
                return {"results": [], "total": 0}

            if response.status_code == 429:
                logger.warning("LeakCheck rate limit hit")
                return {"results": [], "error": "Rate limit exceeded"}

            if response.status_code in (401, 403):
                logger.warning("LeakCheck auth error")
                return {"results": [], "error": "Unauthorized"}

            response.raise_for_status()
            data = response.json()

            results = data.get("result", [])
            return {
                "results": results,
                "total": len(results),
                "found": data.get("found", 0),
            }

    except httpx.HTTPStatusError as e:
        logger.error(f"LeakCheck HTTP error {e.response.status_code}: {e}")
        return {"results": [], "error": f"HTTP {e.response.status_code}"}
    except httpx.RequestError as e:
        logger.error(f"LeakCheck request error: {e}")
        return {"results": [], "error": "Request failed"}
