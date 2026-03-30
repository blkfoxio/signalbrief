"""Narrative models — AI-generated sales intelligence outputs."""

from django.db import models

from core.models import TimestampedModel


class Narrative(TimestampedModel):
    """AI-generated narrative tied to an analysis."""

    analysis = models.ForeignKey(
        "intelligence.Analysis",
        on_delete=models.CASCADE,
        related_name="narrative",
    )
    headline = models.CharField(max_length=500)
    executive_brief = models.TextField(blank=True, default="")
    findings = models.JSONField(default=dict, blank=True)
    correlated_data = models.JSONField(default=dict, blank=True)
    transition = models.TextField(blank=True, default="")
    model_used = models.CharField(max_length=100, blank=True, default="")
    prompt_hash = models.CharField(max_length=64, blank=True, default="")
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta(TimestampedModel.Meta):
        db_table = "narratives"

    def __str__(self):
        return f"Narrative: {self.headline[:80]}"
