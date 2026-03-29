"""Report orchestration views — the core async pipeline."""

import asyncio
import logging

from asgiref.sync import sync_to_async
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from companies.models import Company, CompanyEnrichment
from companies.services.enrichment_service import enrich_company
from companies.services.input_resolver import resolve_inputs
from narratives.models import Narrative
from narratives.services.openai_generator import generate_narrative

from .models import Analysis, DehashedResult, SecuritySignal
from .serializers import AuditDataSerializer, ReportInputSerializer, ReportOutputSerializer
from .services.dehashed_client import search_by_domain, search_by_email
from .services.signal_extractor import extract_signals

logger = logging.getLogger(__name__)


class ReportGenerationThrottle(UserRateThrottle):
    rate = "10/hour"


@api_view(["GET", "POST"])
def report_list_create(request):
    """
    GET: List user's past analyses.
    POST: Create a new analysis (the main pipeline).
    """
    if request.method == "GET":
        return _list_reports(request)
    return _create_report(request)


@api_view(["GET"])
def report_detail(request, report_id):
    """Get a single report with full narrative and signals."""
    try:
        analysis = (
            Analysis.objects.select_related("company", "company__enrichment")
            .prefetch_related("signals", "narrative")
            .get(id=report_id, created_by=request.user)
        )
    except Analysis.DoesNotExist:
        return Response({"error": "Report not found"}, status=status.HTTP_404_NOT_FOUND)

    return Response(ReportOutputSerializer(analysis).data)


@api_view(["GET"])
def report_audit(request, report_id):
    """Get raw DeHashed data for audit mode (masked)."""
    try:
        analysis = Analysis.objects.select_related("dehashed_result").get(
            id=report_id, created_by=request.user
        )
    except Analysis.DoesNotExist:
        return Response({"error": "Report not found"}, status=status.HTTP_404_NOT_FOUND)

    dehashed = getattr(analysis, "dehashed_result", None)
    if not dehashed:
        return Response({"error": "No DeHashed data available"}, status=status.HTTP_404_NOT_FOUND)

    return Response(AuditDataSerializer(dehashed).data)


def _list_reports(request):
    """List user's past analyses."""
    analyses = (
        Analysis.objects.filter(created_by=request.user)
        .select_related("company", "company__enrichment")
        .prefetch_related("signals")
        .order_by("-created_at")[:50]
    )
    serializer = ReportOutputSerializer(analyses, many=True)
    return Response(serializer.data)


@throttle_classes([ReportGenerationThrottle])
def _create_report(request):
    """
    Main orchestration pipeline:
    1. Validate and resolve inputs
    2. Upsert company
    3. Parallel: DeHashed query + LinkedIn enrichment
    4. Extract signals
    5. Generate narrative
    6. Return complete report
    """
    serializer = ReportInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    # Step 1: Resolve inputs
    resolved = resolve_inputs(
        domain=data.get("domain", ""),
        company_name=data.get("company_name", ""),
        linkedin_url=data.get("linkedin_url", ""),
        contact_email=data.get("contact_email", ""),
    )

    if not resolved["domain"]:
        return Response(
            {"error": "Could not resolve a valid domain. Please provide a company domain or contact email."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Step 2: Upsert company
    company, _ = Company.objects.update_or_create(
        domain=resolved["domain"],
        defaults={
            "name": resolved["company_name"] or resolved["domain"],
            "linkedin_url": resolved["linkedin_url"],
            "contact_email": resolved["contact_email"],
            "created_by": request.user,
        },
    )

    # Create analysis record
    analysis = Analysis.objects.create(
        company=company,
        status=Analysis.Status.PROCESSING,
        created_by=request.user,
    )

    try:
        # Step 3: Run DeHashed query + enrichment in parallel
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            dehashed_response, enrichment_data = loop.run_until_complete(
                _parallel_fetch(resolved["domain"], resolved["linkedin_url"], resolved["contact_email"])
            )
        finally:
            loop.close()

        # Store enrichment
        if enrichment_data.get("confidence_score", 0) > 0:
            CompanyEnrichment.objects.update_or_create(
                company=company,
                defaults=enrichment_data,
            )

        # Step 4: Store raw DeHashed results
        entries = dehashed_response.get("entries", [])
        unique_emails = set()
        breach_sources = set()
        for entry in entries:
            emails = entry.get("email", [])
            if isinstance(emails, str):
                emails = [emails]
            for e in emails:
                if e:
                    unique_emails.add(e.lower())
            source = entry.get("database_name", "")
            if source:
                breach_sources.add(source)

        dehashed_result = DehashedResult.objects.create(
            analysis=analysis,
            raw_response=dehashed_response,
            query_domain=resolved["domain"],
            query_email=resolved["contact_email"],
            result_count=dehashed_response.get("total", len(entries)),
            unique_emails=len(unique_emails),
            breach_sources=len(breach_sources),
        )

        # Step 5: Extract signals
        signal_dicts = extract_signals(entries)
        signal_objects = []
        for sig in signal_dicts:
            signal_objects.append(
                SecuritySignal(
                    analysis=analysis,
                    signal_type=sig["signal_type"],
                    value=sig["value"],
                    severity=sig["severity"],
                    title=sig["title"],
                    description=sig["description"],
                )
            )
        SecuritySignal.objects.bulk_create(signal_objects)

        # Step 6: Generate narrative
        company_context = {
            "company_name": company.name,
            "domain": company.domain,
            "industry": "",
            "employee_range": "",
        }
        try:
            enrichment = company.enrichment
            company_context["industry"] = enrichment.industry
            company_context["employee_range"] = enrichment.employee_range
        except CompanyEnrichment.DoesNotExist:
            pass

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            narrative_data = loop.run_until_complete(
                generate_narrative(company_context, signal_dicts)
            )
        finally:
            loop.close()

        narrative = Narrative.objects.create(
            analysis=analysis,
            headline=narrative_data.get("headline", ""),
            executive_narrative=narrative_data.get("executive_narrative", ""),
            talk_track=narrative_data.get("talk_track", ""),
            business_impact=narrative_data.get("business_impact", ""),
            transition=narrative_data.get("transition", ""),
            model_used=narrative_data.get("model_used", ""),
            prompt_hash=narrative_data.get("prompt_hash", ""),
        )

        # Mark completed
        analysis.status = Analysis.Status.COMPLETED
        analysis.save(update_fields=["status", "updated_at"])

        # Attach narrative for serializer
        analysis._narrative = narrative

        return Response(ReportOutputSerializer(analysis).data, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.exception(f"Analysis pipeline failed: {e}")
        analysis.status = Analysis.Status.FAILED
        analysis.error_message = str(e)
        analysis.save(update_fields=["status", "error_message", "updated_at"])
        return Response(
            {"error": "Analysis failed. Please try again.", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


async def _parallel_fetch(domain: str, linkedin_url: str, contact_email: str) -> tuple[dict, dict]:
    """Run DeHashed query and LinkedIn enrichment in parallel."""
    dehashed_task = search_by_domain(domain)
    enrichment_task = enrich_company(domain, linkedin_url)

    results = await asyncio.gather(dehashed_task, enrichment_task, return_exceptions=True)

    dehashed_response = results[0] if not isinstance(results[0], Exception) else {"entries": [], "total": 0}
    enrichment_data = results[1] if not isinstance(results[1], Exception) else {}

    if isinstance(results[0], Exception):
        logger.error(f"DeHashed query failed: {results[0]}")
    if isinstance(results[1], Exception):
        logger.warning(f"Enrichment failed: {results[1]}")

    return dehashed_response, enrichment_data
