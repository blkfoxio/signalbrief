"""Company and enrichment models."""

from django.conf import settings
from django.db import models

from core.models import TimestampedModel


class Company(TimestampedModel):
    """A prospect company identified by its canonical domain."""

    domain = models.CharField(max_length=255, unique=True, db_index=True)
    name = models.CharField(max_length=255, blank=True, default="")
    linkedin_url = models.URLField(blank=True, default="")
    contact_email = models.EmailField(blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="companies",
    )

    class Meta(TimestampedModel.Meta):
        verbose_name_plural = "companies"
        db_table = "companies"

    def __str__(self):
        return self.name or self.domain


class CompanyEnrichment(TimestampedModel):
    """Enrichment data for a company (from Proxycurl/LinkedIn)."""

    company = models.OneToOneField(Company, on_delete=models.CASCADE, related_name="enrichment")
    industry = models.CharField(max_length=255, blank=True, default="")
    employee_range = models.CharField(max_length=50, blank=True, default="")
    description = models.TextField(blank=True, default="")
    hq_location = models.CharField(max_length=255, blank=True, default="")
    confidence_score = models.FloatField(default=0.0)
    raw_data = models.JSONField(default=dict, blank=True)

    class Meta(TimestampedModel.Meta):
        db_table = "company_enrichments"

    def __str__(self):
        return f"Enrichment for {self.company}"
