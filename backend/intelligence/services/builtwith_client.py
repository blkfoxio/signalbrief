"""BuiltWith Free API async client for technology footprint intelligence."""

import logging

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

BUILTWITH_URL = "https://api.builtwith.com/free1/api.json"


async def search_by_domain(domain: str) -> dict:
    """
    Query BuiltWith for the technology stack of a domain.
    Free API returns group/category counts (not individual tech names).
    Returns dict with categories list and metadata.
    """
    if not settings.BUILTWITH_API:
        logger.warning("BUILTWITH_API key not configured, skipping")
        return {"technologies": [], "error": "API key not configured"}

    params = {
        "KEY": settings.BUILTWITH_API,
        "LOOKUP": domain,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                BUILTWITH_URL,
                params=params,
            )

            if response.status_code == 429:
                logger.warning("BuiltWith rate limit hit")
                return {"technologies": [], "error": "Rate limit exceeded"}

            if response.status_code in (401, 403):
                logger.warning("BuiltWith auth error")
                return {"technologies": [], "error": "Unauthorized"}

            response.raise_for_status()
            data = response.json()

            # Free API returns groups with categories — live/dead are counts, not arrays
            technologies = []
            groups = data.get("groups", [])
            for group in groups:
                group_name = group.get("name", "")
                live_count = group.get("live", 0)
                for cat in group.get("categories", []):
                    cat_name = cat.get("name", "")
                    cat_live = cat.get("live", 0)
                    technologies.append({
                        "name": cat_name,
                        "group": group_name,
                        "category": cat_name,
                        "live_count": cat_live,
                    })

            # Categorize security-related technologies
            security_keywords = {
                "security", "ssl", "cdn", "firewall", "waf",
                "monitoring", "certificate",
            }
            security_tools = [
                t for t in technologies
                if any(kw in t.get("category", "").lower() for kw in security_keywords)
                or any(kw in t.get("group", "").lower() for kw in security_keywords)
            ]

            total_live = sum(g.get("live", 0) for g in groups)

            return {
                "technologies": technologies,
                "security_tools": security_tools,
                "total": total_live,
                "total_security": len(security_tools),
                "groups": [{"name": g.get("name", ""), "live": g.get("live", 0)} for g in groups],
            }

    except httpx.HTTPStatusError as e:
        logger.error(f"BuiltWith HTTP error {e.response.status_code}: {e}")
        return {"technologies": [], "error": f"HTTP {e.response.status_code}"}
    except httpx.RequestError as e:
        logger.error(f"BuiltWith request error: {e}")
        return {"technologies": [], "error": "Request failed"}
