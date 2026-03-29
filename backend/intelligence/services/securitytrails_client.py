"""SecurityTrails API async client for DNS and subdomain intelligence."""

import logging

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

SECURITYTRAILS_BASE = "https://api.securitytrails.com/v1"


async def search_by_domain(domain: str) -> dict:
    """
    Query SecurityTrails for subdomains and DNS records.
    Returns dict with subdomains, DNS data, and metadata.
    """
    if not settings.SECURITYTRAILS_API:
        logger.warning("SECURITYTRAILS_API key not configured, skipping")
        return {"subdomains": [], "dns": {}, "error": "API key not configured"}

    headers = {
        "APIKEY": settings.SECURITYTRAILS_API,
        "Accept": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Parallel: subdomains + DNS records
            subdomain_task = client.get(
                f"{SECURITYTRAILS_BASE}/domain/{domain}/subdomains",
                headers=headers,
                params={"children_only": "false"},
            )
            dns_task = client.get(
                f"{SECURITYTRAILS_BASE}/domain/{domain}",
                headers=headers,
            )

            subdomain_resp, dns_resp = await subdomain_task, await dns_task

            result = {"subdomains": [], "dns": {}, "total_subdomains": 0}

            # Parse subdomains
            if subdomain_resp.status_code == 200:
                sub_data = subdomain_resp.json()
                subdomains = sub_data.get("subdomains", [])
                result["subdomains"] = subdomains
                result["total_subdomains"] = len(subdomains)
            elif subdomain_resp.status_code == 429:
                result["error"] = "Rate limit exceeded"
                return result

            # Parse DNS records
            if dns_resp.status_code == 200:
                dns_data = dns_resp.json()
                current_dns = dns_data.get("current_dns", {})
                result["dns"] = current_dns
                result["alexa_rank"] = dns_data.get("alexa_rank")
                result["hostname"] = dns_data.get("hostname")

            return result

    except httpx.HTTPStatusError as e:
        logger.error(f"SecurityTrails HTTP error {e.response.status_code}: {e}")
        return {"subdomains": [], "dns": {}, "error": f"HTTP {e.response.status_code}"}
    except httpx.RequestError as e:
        logger.error(f"SecurityTrails request error: {e}")
        return {"subdomains": [], "dns": {}, "error": "Request failed"}
