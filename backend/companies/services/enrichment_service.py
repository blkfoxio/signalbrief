"""Company enrichment via NinjaPear API (formerly Proxycurl)."""

import logging

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

NINJAPEAR_COMPANY_URL = "https://nubela.co/api/v1/company/details"

# GICS industry code to human-readable name mapping (top-level sectors)
GICS_SECTORS = {
    10: "Energy",
    15: "Materials",
    20: "Industrials",
    25: "Consumer Discretionary",
    30: "Consumer Staples",
    35: "Health Care",
    40: "Financials",
    45: "Information Technology",
    50: "Communication Services",
    55: "Utilities",
    60: "Real Estate",
}


async def enrich_company(domain: str, linkedin_url: str = "") -> dict:
    """
    Fetch company enrichment data from NinjaPear.
    Uses domain (website) as the primary lookup — no LinkedIn URL needed.
    Returns enrichment dict with industry, employee_range, description, etc.
    """
    if not settings.PROXYCURL_API:
        return _empty_enrichment()

    # Prefer domain as the website param; NinjaPear takes a website URL
    website = f"https://{domain}" if domain else ""
    if not website and not linkedin_url:
        return _empty_enrichment()

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                NINJAPEAR_COMPANY_URL,
                params={"website": website},
                headers={"Authorization": f"Bearer {settings.PROXYCURL_API}"},
            )
            response.raise_for_status()
            data = response.json()

        return _parse_response(data)

    except httpx.HTTPStatusError as e:
        logger.warning(f"NinjaPear HTTP error {e.response.status_code}: {e}")
        return _empty_enrichment()
    except Exception as e:
        logger.warning(f"NinjaPear enrichment failed: {e}")
        return _empty_enrichment()


def _parse_response(data: dict) -> dict:
    """Parse NinjaPear company details response into our enrichment format."""
    employee_count = data.get("employee_count") or 0
    employee_range = _size_to_range(employee_count)
    industry = _resolve_industry(data.get("industry"))

    return {
        "industry": industry,
        "employee_range": employee_range,
        "description": data.get("description", ""),
        "hq_location": _format_location(data),
        "confidence_score": _calculate_confidence(data),
        "raw_data": data,
    }


def _resolve_industry(gics_code) -> str:
    """Convert GICS 8-digit industry code to a readable sector name."""
    if not gics_code:
        return ""
    try:
        code = int(gics_code)
        # Extract 2-digit sector code from 8-digit GICS code
        sector_code = code // 1000000
        return GICS_SECTORS.get(sector_code, f"Industry ({code})")
    except (ValueError, TypeError):
        # If it's already a string name, return as-is
        return str(gics_code)


def _size_to_range(size: int) -> str:
    """Convert numeric employee count to a range string."""
    if size <= 0:
        return ""
    if size <= 10:
        return "1-10"
    if size <= 50:
        return "11-50"
    if size <= 200:
        return "51-200"
    if size <= 500:
        return "201-500"
    if size <= 1000:
        return "501-1000"
    if size <= 5000:
        return "1001-5000"
    if size <= 10000:
        return "5001-10000"
    return "10001+"


def _format_location(data: dict) -> str:
    """Extract HQ location from NinjaPear addresses array."""
    addresses = data.get("addresses", [])
    # Find headquarters or first address
    for addr in addresses:
        if isinstance(addr, dict):
            if addr.get("address_type") == "HEADQUARTERS" or addr.get("is_primary"):
                parts = [addr.get("city", ""), addr.get("state", ""), addr.get("country", "")]
                return ", ".join(p for p in parts if p)
    # Fallback to first address
    if addresses and isinstance(addresses[0], dict):
        addr = addresses[0]
        parts = [addr.get("city", ""), addr.get("state", ""), addr.get("country", "")]
        return ", ".join(p for p in parts if p)
    return ""


def _calculate_confidence(data: dict) -> float:
    """Calculate enrichment confidence based on available fields."""
    score = 0.0
    if data.get("industry"):
        score += 0.3
    if data.get("employee_count"):
        score += 0.3
    if data.get("description"):
        score += 0.2
    if data.get("name"):
        score += 0.1
    if data.get("addresses"):
        score += 0.1
    return min(score, 1.0)


def _empty_enrichment() -> dict:
    return {
        "industry": "",
        "employee_range": "",
        "description": "",
        "hq_location": "",
        "confidence_score": 0.0,
        "raw_data": {},
    }
