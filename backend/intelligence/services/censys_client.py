"""Censys Platform API v3 async client for host and certificate intelligence."""

import logging
import socket

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

CENSYS_BASE = "https://api.platform.censys.io/v3"


async def search_by_domain(domain: str) -> dict:
    """
    Look up host data for a domain on the Censys Platform API v3.
    Resolves domain to IP, then queries the global host asset endpoint.
    Uses Personal Access Token (Bearer auth).
    """
    if not settings.CENSYS_API_TOKEN:
        logger.warning("CENSYS_API_TOKEN not configured, skipping")
        return {"hosts": [], "certificates": [], "error": "API key not configured"}

    # Resolve domain to IP first
    try:
        ip_address = socket.gethostbyname(domain)
    except socket.gaierror:
        logger.warning(f"Could not resolve {domain} to IP for Censys lookup")
        return {"hosts": [], "certificates": [], "total_hosts": 0}

    headers = {
        "Authorization": f"Bearer {settings.CENSYS_API_TOKEN}",
        "Accept": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Host asset lookup
            host_response = await client.get(
                f"{CENSYS_BASE}/global/asset/host/{ip_address}",
                headers=headers,
            )

            if host_response.status_code == 429:
                logger.warning("Censys rate limit hit")
                return {"hosts": [], "certificates": [], "error": "Rate limit exceeded"}

            if host_response.status_code in (401, 403):
                logger.warning(f"Censys auth error ({host_response.status_code})")
                return {"hosts": [], "certificates": [], "error": "Unauthorized"}

            result = {"hosts": [], "certificates": [], "total_hosts": 0, "ip": ip_address}

            if host_response.status_code == 200:
                raw = host_response.json()
                # v3 wraps data under result.resource
                resource = raw.get("result", {}).get("resource", raw)
                result["hosts"] = [resource]
                result["total_hosts"] = 1

                # Extract services/ports
                services = resource.get("services", [])
                result["total_services"] = len(services)
                result["ports"] = [s.get("port") for s in services if s.get("port")]

                # Extract useful metadata
                asn = resource.get("autonomous_system", {})
                result["asn"] = asn.get("description", "")
                location = resource.get("location", {})
                result["location"] = f"{location.get('city', '')}, {location.get('country', '')}".strip(", ")

            return result

    except httpx.HTTPStatusError as e:
        logger.error(f"Censys HTTP error {e.response.status_code}: {e}")
        return {"hosts": [], "certificates": [], "error": f"HTTP {e.response.status_code}"}
    except httpx.RequestError as e:
        logger.error(f"Censys request error: {e}")
        return {"hosts": [], "certificates": [], "error": "Request failed"}
