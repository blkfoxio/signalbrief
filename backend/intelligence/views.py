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

from .models import Analysis, DehashedResult, OsintResult, SecuritySignal
from .serializers import AuditDataSerializer, ReportInputSerializer, ReportOutputSerializer
from .services.dehashed_client import search_by_domain, search_by_email
from .services.signal_extractor import extract_all_signals, extract_signals

from .services.hibp_client import search_by_domain as hibp_search
from .services.shodan_client import search_by_domain as shodan_search
from .services.leakcheck_client import search_by_domain as leakcheck_search
from .services.securitytrails_client import search_by_domain as securitytrails_search
from .services.censys_client import search_by_domain as censys_search
from .services.builtwith_client import search_by_domain as builtwith_search

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


@api_view(["GET", "DELETE"])
def report_detail(request, report_id):
    """Get or delete a single report."""
    try:
        analysis = (
            Analysis.objects.select_related("company", "company__enrichment")
            .prefetch_related("signals", "narrative", "osint_results")
            .get(id=report_id, created_by=request.user)
        )
    except Analysis.DoesNotExist:
        return Response({"error": "Report not found"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "DELETE":
        analysis.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

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


@api_view(["GET"])
def report_osint_raw(request, report_id, source):
    """Get raw OSINT data for a specific source."""
    try:
        analysis = Analysis.objects.get(id=report_id, created_by=request.user)
    except Analysis.DoesNotExist:
        return Response({"error": "Report not found"}, status=status.HTTP_404_NOT_FOUND)

    try:
        result = OsintResult.objects.get(analysis=analysis, source=source)
    except OsintResult.DoesNotExist:
        return Response({"error": f"No {source} data available"}, status=status.HTTP_404_NOT_FOUND)

    return Response({
        "source": result.source,
        "result_count": result.result_count,
        "query_value": result.query_value,
        "queried_at": result.queried_at,
        "data": result.raw_response,
    })


@api_view(["POST"])
@throttle_classes([ReportGenerationThrottle])
def report_rerun(request, report_id):
    """Rerun analysis for the same company — creates a new report."""
    try:
        original = Analysis.objects.select_related("company").get(
            id=report_id, created_by=request.user
        )
    except Analysis.DoesNotExist:
        return Response({"error": "Report not found"}, status=status.HTTP_404_NOT_FOUND)

    company = original.company
    return _run_pipeline(request, company)


def _list_reports(request):
    """List user's past analyses."""
    analyses = (
        Analysis.objects.filter(created_by=request.user)
        .select_related("company", "company__enrichment")
        .prefetch_related("signals", "osint_results")
        .order_by("-created_at")[:50]
    )
    serializer = ReportOutputSerializer(analyses, many=True)
    return Response(serializer.data)


@throttle_classes([ReportGenerationThrottle])
def _create_report(request):
    """Validate inputs, resolve domain, upsert company, then run pipeline."""
    serializer = ReportInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

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

    company, _ = Company.objects.update_or_create(
        domain=resolved["domain"],
        defaults={
            "name": resolved["company_name"] or resolved["domain"],
            "linkedin_url": resolved["linkedin_url"],
            "contact_email": resolved["contact_email"],
            "created_by": request.user,
        },
    )

    return _run_pipeline(request, company)


def _run_pipeline(request, company):
    """
    Core analysis pipeline — shared by create and rerun.
    1. Create Analysis record
    2. Parallel: DeHashed query + company enrichment
    3. Store raw results
    4. Extract signals
    5. Generate narrative
    6. Return complete report
    """
    analysis = Analysis.objects.create(
        company=company,
        status=Analysis.Status.PROCESSING,
        created_by=request.user,
    )

    try:
        # Parallel: All data sources
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            fetched = loop.run_until_complete(
                _parallel_fetch(company.domain, company.linkedin_url, company.contact_email)
            )
        finally:
            loop.close()

        dehashed_response = fetched.get("dehashed", {"entries": [], "total": 0})
        enrichment_data = fetched.get("enrichment", {})

        # Store enrichment
        if enrichment_data.get("confidence_score", 0) > 0:
            CompanyEnrichment.objects.update_or_create(
                company=company,
                defaults=enrichment_data,
            )

        # Store raw DeHashed results
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

        DehashedResult.objects.create(
            analysis=analysis,
            raw_response=dehashed_response,
            query_domain=company.domain,
            query_email=company.contact_email,
            result_count=dehashed_response.get("total", len(entries)),
            unique_emails=len(unique_emails),
            breach_sources=len(breach_sources),
        )

        # Store OSINT results from other sources
        osint_sources = ["hibp", "shodan", "leakcheck", "securitytrails", "censys", "builtwith"]
        osint_results = {}
        for source_name in osint_sources:
            source_data = fetched.get(source_name)
            if source_data and not source_data.get("error"):
                osint_results[source_name] = source_data
                # Determine result count based on source
                result_count = (
                    source_data.get("total", 0)
                    or len(source_data.get("breaches", []))
                    or len(source_data.get("hosts", []))
                    or len(source_data.get("results", []))
                    or len(source_data.get("technologies", []))
                    or source_data.get("total_subdomains", 0)
                )
                OsintResult.objects.create(
                    analysis=analysis,
                    source=source_name,
                    raw_response=source_data,
                    result_count=result_count,
                    query_value=company.domain,
                    error_message=source_data.get("error", ""),
                )

        # Extract signals from ALL sources
        signal_dicts = extract_all_signals(entries, osint_results)
        SecuritySignal.objects.bulk_create([
            SecuritySignal(
                analysis=analysis,
                source=sig.get("source", "dehashed"),
                signal_type=sig["signal_type"],
                value=sig["value"],
                severity=sig["severity"],
                title=sig["title"],
                description=sig["description"],
            )
            for sig in signal_dicts
        ])

        # Generate narrative
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
            risk_summary=narrative_data.get("risk_summary", ""),
            category_findings=narrative_data.get("category_findings", {}),
            executive_narrative=narrative_data.get("executive_narrative", ""),
            talk_track=narrative_data.get("talk_track", ""),
            business_impact=narrative_data.get("business_impact", ""),
            transition=narrative_data.get("transition", ""),
            model_used=narrative_data.get("model_used", ""),
            prompt_hash=narrative_data.get("prompt_hash", ""),
        )

        analysis.status = Analysis.Status.COMPLETED
        analysis.save(update_fields=["status", "updated_at"])
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


async def _parallel_fetch(domain: str, linkedin_url: str, contact_email: str) -> dict:
    """Run all data source queries in parallel."""
    from django.conf import settings

    tasks = {
        "dehashed": search_by_domain(domain),
        "enrichment": enrich_company(domain, linkedin_url),
    }

    # Only include OSINT sources that have API keys configured
    if settings.HIBP_API:
        tasks["hibp"] = hibp_search(domain)
    if settings.SHODAN_API:
        tasks["shodan"] = shodan_search(domain)
    if settings.LEAKCHECK_API:
        tasks["leakcheck"] = leakcheck_search(domain)
    if settings.SECURITYTRAILS_API:
        tasks["securitytrails"] = securitytrails_search(domain)
    if settings.CENSYS_API_TOKEN:
        tasks["censys"] = censys_search(domain)
    if settings.BUILTWITH_API:
        tasks["builtwith"] = builtwith_search(domain)

    keys = list(tasks.keys())
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)

    fetched = {}
    for key, result in zip(keys, results):
        if isinstance(result, Exception):
            logger.error(f"{key} query failed: {result}")
            fetched[key] = {} if key != "dehashed" else {"entries": [], "total": 0}
        else:
            fetched[key] = result

    return fetched
