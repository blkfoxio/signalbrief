"""Censys Platform API async client for certificate and host intelligence."""

import logging

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

CENSYS_HOSTS_URL = "https://app.censys.io/api/v1/hosts/search"
CENSYS_CERTS_URL = "https://app.censys.io/api/v1/certificates/search"


async def search_by_domain(domain: str) -> dict:
    """
    Search Censys for hosts and certificates associated with a domain.
    Uses Personal Access Token (Bearer auth) for the Censys Platform.
    Returns dict with hosts, certificates, and metadata.
    """
    if not settings.CENSYS_API_TOKEN:
        logger.warning("CENSYS_API_TOKEN not configured, skipping")
        return {"hosts": [], "certificates": [], "error": "API key not configured"}

    headers = {
        "Authorization": f"Bearer {settings.CENSYS_API_TOKEN}",
        "Accept": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            host_response = await client.get(
                CENSYS_HOSTS_URL,
                headers=headers,
                params={"q": domain, "per_page": 25},
            )

            if host_response.status_code == 429:
                logger.warning("Censys rate limit hit")
                return {"hosts": [], "certificates": [], "error": "Rate limit exceeded"}

            if host_response.status_code in (401, 403):
                logger.warning(f"Censys auth error ({host_response.status_code})")
                return {"hosts": [], "certificates": [], "error": "Unauthorized"}

            result = {"hosts": [], "certificates": [], "total_hosts": 0}

            if host_response.status_code == 200:
                host_data = host_response.json()
                hits = host_data.get("result", {}).get("hits", [])
                result["hosts"] = hits
                result["total_hosts"] = host_data.get("result", {}).get("total", 0)

            cert_response = await client.get(
                CENSYS_CERTS_URL,
                headers=headers,
                params={"q": domain, "per_page": 25},
            )

            if cert_response.status_code == 200:
                cert_data = cert_response.json()
                certs = cert_data.get("result", {}).get("hits", [])
                result["certificates"] = certs
                result["total_certificates"] = len(certs)

            return result

    except httpx.HTTPStatusError as e:
        logger.error(f"Censys HTTP error {e.response.status_code}: {e}")
        return {"hosts": [], "certificates": [], "error": f"HTTP {e.response.status_code}"}
    except httpx.RequestError as e:
        logger.error(f"Censys request error: {e}")
        return {"hosts": [], "certificates": [], "error": "Request failed"}
