"""Render a SignalBrief report as a self-contained PDF via WeasyPrint."""

import logging
from io import BytesIO

from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone

from core.utils.masking import mask_dehashed_entry

from ..models import Analysis

logger = logging.getLogger(__name__)


def render_report_pdf(analysis: Analysis) -> bytes:
    """Build the report HTML for `analysis` and return PDF bytes.

    Includes the narrative + correlated findings + raw OSINT/DeHashed appendices,
    so the exported PDF is self-contained (matches what's on screen plus the
    underlying-data panel).
    """
    # Lazy import — WeasyPrint pulls in heavy native libs at import time.
    from weasyprint import HTML

    company = analysis.company
    company_ctx = {
        "domain": company.domain,
        "name": company.name,
    }
    try:
        enrichment = company.enrichment
        company_ctx["industry"] = enrichment.industry
        company_ctx["employee_range"] = enrichment.employee_range
    except Exception:
        company_ctx["industry"] = ""
        company_ctx["employee_range"] = ""

    narrative_obj = getattr(analysis, "_narrative", None)
    if narrative_obj is None:
        narrative_obj = analysis.narrative.first() if hasattr(analysis, "narrative") else None

    narrative_ctx = {}
    if narrative_obj:
        narrative_ctx = {
            "headline": narrative_obj.headline,
            "executive_brief": narrative_obj.executive_brief,
            "executive_summary": getattr(narrative_obj, "executive_summary", {}) or {},
            "findings": narrative_obj.findings or {},
            "recommendations": getattr(narrative_obj, "recommendations", []) or [],
            "correlated_data": narrative_obj.correlated_data or {},
            "transition": narrative_obj.transition,
            "posture": (narrative_obj.correlated_data or {}).get("posture", ""),
        }

    dehashed_ctx = None
    dehashed = getattr(analysis, "dehashed_result", None)
    if dehashed:
        entries = (dehashed.raw_response or {}).get("entries", []) or []
        masked = [mask_dehashed_entry(e) for e in entries]
        # Surface plaintext-exposed > hash-exposed > none, mirroring the audit panel.
        masked.sort(
            key=lambda e: (2 if e.get("password_exposed") else 1 if e.get("hash_exposed") else 0),
            reverse=True,
        )
        dehashed_ctx = {
            "queried_at": dehashed.queried_at,
            "result_count": dehashed.result_count,
            "unique_emails": dehashed.unique_emails,
            "breach_sources": dehashed.breach_sources,
            "entries": masked[:50],
        }

    osint_raw = {}
    for result in analysis.osint_results.all():
        if result.error_message:
            continue
        osint_raw[result.source] = {
            "queried_at": result.queried_at,
            "result_count": result.result_count,
            "data": result.raw_response or {},
        }

    html = render_to_string(
        "intelligence/report_pdf.html",
        {
            "company": company_ctx,
            "narrative": narrative_ctx,
            "dehashed": dehashed_ctx,
            "osint_raw": osint_raw,
            "generated_at": timezone.now(),
            "disclaimer": getattr(settings, "REPORT_DISCLAIMER", ""),
        },
    )

    buf = BytesIO()
    HTML(string=html).write_pdf(target=buf)
    return buf.getvalue()
