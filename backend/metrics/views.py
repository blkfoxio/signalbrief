"""Operator metrics — admin-only dashboard endpoints.

All metrics are derived from existing tables (User, Analysis, OsintResult,
DehashedResult). No new tracking models in v1.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, ExpressionWrapper, F, fields
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from intelligence.models import Analysis, DehashedResult, OsintResult

User = get_user_model()


def _since(days: int):
    return timezone.now() - timedelta(days=days)


def _daily_series(queryset, date_field: str, days: int = 30):
    """Return list of {date, count} for the last `days` days, zero-filled."""
    start = (timezone.now() - timedelta(days=days - 1)).date()
    rows = (
        queryset.filter(**{f"{date_field}__date__gte": start})
        .annotate(day=TruncDate(date_field))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )
    by_day = {row["day"]: row["count"] for row in rows}
    return [
        {"date": (start + timedelta(days=i)).isoformat(), "count": by_day.get(start + timedelta(days=i), 0)}
        for i in range(days)
    ]


@api_view(["GET"])
@permission_classes([IsAdminUser])
def overview(request):
    now = timezone.now()
    seven = _since(7)
    thirty = _since(30)

    total_users = User.objects.count()
    users_last_7d = User.objects.filter(date_joined__gte=seven).count()
    users_last_30d = User.objects.filter(date_joined__gte=thirty).count()
    active_users_7d = User.objects.filter(last_login__gte=seven).count()

    total_reports = Analysis.objects.count()
    reports_last_7d = Analysis.objects.filter(created_at__gte=seven).count()
    reports_last_30d = Analysis.objects.filter(created_at__gte=thirty).count()

    by_status_rows = Analysis.objects.values("status").annotate(count=Count("id"))
    reports_by_status = {row["status"]: row["count"] for row in by_status_rows}

    last30 = Analysis.objects.filter(created_at__gte=thirty)
    completed_30d = last30.filter(status=Analysis.Status.COMPLETED).count()
    failed_30d = last30.filter(status=Analysis.Status.FAILED).count()
    finished_30d = completed_30d + failed_30d
    pipeline_success_rate_30d = (completed_30d / finished_30d) if finished_30d else None

    duration_expr = ExpressionWrapper(
        F("updated_at") - F("created_at"), output_field=fields.DurationField()
    )
    avg_duration = (
        last30.filter(status=Analysis.Status.COMPLETED)
        .annotate(duration=duration_expr)
        .aggregate(avg=Avg("duration"))
        .get("avg")
    )
    avg_pipeline_duration_seconds = avg_duration.total_seconds() if avg_duration else None

    return Response(
        {
            "generated_at": now.isoformat(),
            "users": {
                "total": total_users,
                "last_7d": users_last_7d,
                "last_30d": users_last_30d,
                "active_7d": active_users_7d,
            },
            "reports": {
                "total": total_reports,
                "last_7d": reports_last_7d,
                "last_30d": reports_last_30d,
                "by_status": reports_by_status,
                "success_rate_30d": pipeline_success_rate_30d,
                "avg_duration_seconds_30d": avg_pipeline_duration_seconds,
            },
            "daily_reports_30d": _daily_series(Analysis.objects.all(), "created_at", 30),
            "daily_signups_30d": _daily_series(User.objects.all(), "date_joined", 30),
        }
    )


@api_view(["GET"])
@permission_classes([IsAdminUser])
def sources(request):
    """Per-OSINT-source health for the last 30 days."""
    thirty = _since(30)
    last30 = OsintResult.objects.filter(queried_at__gte=thirty)

    rows = []
    for value, label in OsintResult.Source.choices:
        source_qs = last30.filter(source=value)
        total = source_qs.count()
        errors = source_qs.exclude(error_message="").count()
        last_error = (
            source_qs.exclude(error_message="").order_by("-queried_at").values("queried_at", "error_message").first()
        )
        rows.append(
            {
                "source": value,
                "label": label,
                "total_calls_30d": total,
                "error_count_30d": errors,
                "success_rate": ((total - errors) / total) if total else None,
                "last_error_at": last_error["queried_at"].isoformat() if last_error else None,
                "last_error_message": last_error["error_message"] if last_error else None,
            }
        )

    # DeHashed: no per-call error column. Infer from analyses missing a DehashedResult.
    dh_total = DehashedResult.objects.filter(queried_at__gte=thirty).count()
    analyses_30d = Analysis.objects.filter(created_at__gte=thirty)
    finished = analyses_30d.exclude(status__in=[Analysis.Status.PENDING, Analysis.Status.PROCESSING]).count()
    missing = analyses_30d.filter(
        status__in=[Analysis.Status.COMPLETED, Analysis.Status.FAILED],
        dehashed_result__isnull=True,
    ).count()
    rows.append(
        {
            "source": "dehashed",
            "label": "DeHashed",
            "total_calls_30d": finished,
            "error_count_30d": missing,
            "success_rate": ((finished - missing) / finished) if finished else None,
            "last_error_at": None,
            "last_error_message": (
                f"{missing} of {finished} finished analyses missing DeHashed result" if missing else None
            ),
            "_note": f"{dh_total} DeHashed records stored",
        }
    )

    return Response({"sources": rows})


@api_view(["GET"])
@permission_classes([IsAdminUser])
def recent_failures(request):
    failed_analyses = (
        Analysis.objects.filter(status=Analysis.Status.FAILED)
        .select_related("company", "created_by")
        .order_by("-created_at")[:25]
    )
    failed_osint = (
        OsintResult.objects.exclude(error_message="")
        .select_related("analysis", "analysis__company")
        .order_by("-queried_at")[:25]
    )

    return Response(
        {
            "analyses": [
                {
                    "id": str(a.id),
                    "domain": a.company.domain if a.company_id else None,
                    "error_message": a.error_message,
                    "created_at": a.created_at.isoformat(),
                    "user_email": a.created_by.email if a.created_by_id else None,
                }
                for a in failed_analyses
            ],
            "osint_calls": [
                {
                    "analysis_id": str(o.analysis_id),
                    "domain": o.analysis.company.domain if o.analysis_id and o.analysis.company_id else None,
                    "source": o.source,
                    "query_value": o.query_value,
                    "error_message": o.error_message,
                    "queried_at": o.queried_at.isoformat(),
                }
                for o in failed_osint
            ],
        }
    )
