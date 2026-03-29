"""Intelligence models: Analysis, DeHashed results, and security signals."""

from django.conf import settings
from django.db import models

from core.models import TimestampedModel


class Analysis(TimestampedModel):
    """Top-level analysis record tying together company, DeHashed, signals, and narrative."""

    class Status(models.TextChoices):
        PENDING = "pending"
        PROCESSING = "processing"
        COMPLETED = "completed"
        FAILED = "failed"

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="analyses",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    error_message = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="analyses",
    )

    class Meta(TimestampedModel.Meta):
        verbose_name_plural = "analyses"
        db_table = "analyses"

    def __str__(self):
        return f"Analysis {self.id} - {self.company.domain} ({self.status})"


class DehashedResult(TimestampedModel):
    """Raw DeHashed API response storage for auditability."""

    analysis = models.OneToOneField(Analysis, on_delete=models.CASCADE, related_name="dehashed_result")
    raw_response = models.JSONField(default=dict)
    query_domain = models.CharField(max_length=255)
    query_email = models.EmailField(blank=True, default="")
    result_count = models.IntegerField(default=0)
    unique_emails = models.IntegerField(default=0)
    breach_sources = models.IntegerField(default=0)
    queried_at = models.DateTimeField(auto_now_add=True)

    class Meta(TimestampedModel.Meta):
        db_table = "dehashed_results"

    def __str__(self):
        return f"DeHashed: {self.query_domain} ({self.result_count} results)"


class SecuritySignal(TimestampedModel):
    """Deterministic security signal extracted from DeHashed data."""

    class Severity(models.TextChoices):
        LOW = "low"
        MEDIUM = "medium"
        HIGH = "high"
        CRITICAL = "critical"

    analysis = models.ForeignKey(Analysis, on_delete=models.CASCADE, related_name="signals")
    signal_type = models.CharField(max_length=100)
    value = models.JSONField(default=dict)
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.LOW)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")

    class Meta(TimestampedModel.Meta):
        db_table = "security_signals"

    def __str__(self):
        return f"{self.signal_type}: {self.title}"
