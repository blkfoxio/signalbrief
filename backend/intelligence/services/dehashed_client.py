"""DeHashed API v2 async client."""

import logging
from typing import Optional

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

DEHASHED_SEARCH_URL = "https://api.dehashed.com/v2/search"
MAX_RESULTS_PER_PAGE = 10000
DEFAULT_PAGE_SIZE = 500


async def search_by_domain(
    domain: str,
    page: int = 1,
    size: int = DEFAULT_PAGE_SIZE,
    de_dupe: bool = True,
) -> dict:
    """
    Search DeHashed by domain.
    Query syntax: domain:example.com
    Returns the raw API response dict.
    """
    return await _search(
        query=f"domain:{domain}",
        page=page,
        size=size,
        de_dupe=de_dupe,
    )


async def search_by_email(
    email: str,
    page: int = 1,
    size: int = DEFAULT_PAGE_SIZE,
    de_dupe: bool = True,
) -> dict:
    """Search DeHashed by specific email address."""
    return await _search(
        query=f"email:{email}",
        page=page,
        size=size,
        de_dupe=de_dupe,
    )


async def _search(
    query: str,
    page: int = 1,
    size: int = DEFAULT_PAGE_SIZE,
    de_dupe: bool = True,
    wildcard: bool = False,
    regex: bool = False,
) -> dict:
    """Execute a DeHashed v2 search query."""
    if not settings.DEHASHED_API:
        logger.error("DEHASHED_API key not configured")
        return {"entries": [], "total": 0, "error": "API key not configured"}

    # Cap size to API maximum
    size = min(size, MAX_RESULTS_PER_PAGE)

    payload = {
        "query": query,
        "page": page,
        "size": size,
        "wildcard": wildcard,
        "regex": regex,
        "de_dupe": de_dupe,
    }

    headers = {
        "Content-Type": "application/json",
        "Dehashed-Api-Key": settings.DEHASHED_API,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                DEHASHED_SEARCH_URL,
                json=payload,
                headers=headers,
            )

            if response.status_code == 429:
                logger.warning("DeHashed rate limit hit")
                return {"entries": [], "total": 0, "error": "Rate limit exceeded"}

            if response.status_code == 403:
                logger.warning("DeHashed insufficient credits")
                return {"entries": [], "total": 0, "error": "Insufficient credits"}

            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as e:
        logger.error(f"DeHashed HTTP error {e.response.status_code}: {e}")
        return {"entries": [], "total": 0, "error": f"HTTP {e.response.status_code}"}
    except httpx.RequestError as e:
        logger.error(f"DeHashed request error: {e}")
        return {"entries": [], "total": 0, "error": "Request failed"}
