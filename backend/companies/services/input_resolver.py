"""Input resolution: normalize user inputs into canonical identifiers."""

from core.utils.validators import extract_domain_from_email, normalize_domain, validate_domain_format


def resolve_inputs(
    domain: str = "",
    company_name: str = "",
    linkedin_url: str = "",
    contact_email: str = "",
) -> dict:
    """
    Resolve raw user inputs into normalized internal fields.
    Returns a dict with resolved domain, confidence, and metadata.
    """
    resolved_domain = ""
    confidence = 0.0

    # Priority 1: Direct domain input
    if domain:
        resolved_domain = normalize_domain(domain)
        if validate_domain_format(resolved_domain):
            confidence = 1.0

    # Priority 2: Extract domain from contact email
    if not resolved_domain and contact_email:
        extracted = extract_domain_from_email(contact_email)
        if validate_domain_format(extracted):
            resolved_domain = extracted
            confidence = 0.95

    # Priority 3: LinkedIn URL might help but can't derive domain
    # The enrichment service handles LinkedIn resolution separately

    return {
        "domain": resolved_domain,
        "company_name": company_name.strip() if company_name else "",
        "linkedin_url": linkedin_url.strip() if linkedin_url else "",
        "contact_email": contact_email.strip().lower() if contact_email else "",
        "domain_confidence": confidence,
        "domain_source": _get_source(domain, contact_email, confidence),
    }


def _get_source(domain: str, contact_email: str, confidence: float) -> str:
    if confidence >= 1.0 and domain:
        return "direct_input"
    if confidence >= 0.9 and contact_email:
        return "email_extraction"
    return "unresolved"
