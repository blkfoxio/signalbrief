"""Shodan API async client with InternetDB fallback for free tier."""

import logging
import socket

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

SHODAN_DNS_RESOLVE_URL = "https://api.shodan.io/dns/resolve"
SHODAN_HOST_URL = "https://api.shodan.io/shodan/host"
INTERNETDB_URL = "https://internetdb.shodan.io"


async def search_by_domain(domain: str) -> dict:
    """
    Search Shodan for exposed services on a domain.
    Step 1: Resolve domain to IP(s) via DNS.
    Step 2: Query host info for each IP.
    Returns dict with hosts list and metadata.
    """
    if not settings.SHODAN_API:
        logger.warning("SHODAN_API key not configured, skipping")
        return {"hosts": [], "error": "API key not configured"}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Step 1: DNS resolve
            dns_response = await client.get(
                SHODAN_DNS_RESOLVE_URL,
                params={"hostnames": domain, "key": settings.SHODAN_API},
            )

            if dns_response.status_code == 429:
                logger.warning("Shodan rate limit hit")
                return {"hosts": [], "error": "Rate limit exceeded"}

            if dns_response.status_code == 403:
                logger.warning("Shodan 403 on DNS resolve — free tier may not support this endpoint, trying InternetDB fallback")
                return await _internetdb_fallback(domain)

            dns_response.raise_for_status()
            dns_data = dns_response.json()

            ip_address = dns_data.get(domain)
            if not ip_address:
                return {"hosts": [], "total": 0}

            # Step 2: Host lookup
            host_response = await client.get(
                f"{SHODAN_HOST_URL}/{ip_address}",
                params={"key": settings.SHODAN_API},
            )

            if host_response.status_code == 404:
                return {"hosts": [], "total": 0}

            if host_response.status_code == 429:
                logger.warning("Shodan rate limit hit on host lookup")
                return {"hosts": [], "error": "Rate limit exceeded"}

            host_response.raise_for_status()
            host_data = host_response.json()

            return {
                "hosts": [host_data],
                "ip": ip_address,
                "total_ports": len(host_data.get("ports", [])),
                "total_vulns": len(host_data.get("vulns", [])),
            }

    except httpx.HTTPStatusError as e:
        logger.error(f"Shodan HTTP error {e.response.status_code}: {e}")
        # Fall back to InternetDB on any paid-tier error
        if e.response.status_code in (401, 403):
            return await _internetdb_fallback(domain)
        return {"hosts": [], "error": f"HTTP {e.response.status_code}"}
    except httpx.RequestError as e:
        logger.error(f"Shodan request error: {e}")
        return {"hosts": [], "error": "Request failed"}


async def _internetdb_fallback(domain: str) -> dict:
    """
    Free Shodan InternetDB lookup — no API key required.
    Returns basic port/vuln/CPE data for an IP.
    https://internetdb.shodan.io/
    """
    try:
        ip_address = socket.gethostbyname(domain)
    except socket.gaierror:
        logger.warning(f"Could not resolve {domain} to IP for InternetDB lookup")
        return {"hosts": [], "total": 0}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(f"{INTERNETDB_URL}/{ip_address}")

            if response.status_code == 404:
                return {"hosts": [], "total": 0}

            response.raise_for_status()
            data = response.json()

            # InternetDB returns: ip, ports[], cpes[], hostnames[], tags[], vulns[]
            host_data = {
                "ip_str": ip_address,
                "ports": data.get("ports", []),
                "vulns": data.get("vulns", []),
                "hostnames": data.get("hostnames", []),
                "tags": data.get("tags", []),
                "cpes": data.get("cpes", []),
                "data": [{"product": cpe, "version": ""} for cpe in data.get("cpes", [])],
            }

            return {
                "hosts": [host_data],
                "ip": ip_address,
                "total_ports": len(host_data["ports"]),
                "total_vulns": len(host_data["vulns"]),
                "source": "internetdb",
            }

    except Exception as e:
        logger.error(f"InternetDB fallback failed: {e}")
        return {"hosts": [], "error": "InternetDB fallback failed"}
