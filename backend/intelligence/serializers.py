"""Intelligence serializers for reports API."""

from rest_framework import serializers

from companies.serializers import CompanyEnrichmentSerializer
from core.utils.masking import mask_dehashed_entry
from core.utils.validators import validate_domain_format, validate_linkedin_url

from .models import Analysis, DehashedResult, OsintResult, SecuritySignal


class ReportInputSerializer(serializers.Serializer):
    """Input serializer for creating a new analysis report."""

    domain = serializers.CharField(required=False, allow_blank=True, default="")
    company_name = serializers.CharField(required=False, allow_blank=True, default="")
    linkedin_url = serializers.URLField(required=False, allow_blank=True, default="")
    contact_email = serializers.EmailField(required=False, allow_blank=True, default="")

    def validate(self, data):
        # At least one identifier must be provided
        if not any([data.get("domain"), data.get("contact_email"), data.get("linkedin_url"), data.get("company_name")]):
            raise serializers.ValidationError("At least one field must be provided.")

        if data.get("linkedin_url") and not validate_linkedin_url(data["linkedin_url"]):
            raise serializers.ValidationError({"linkedin_url": "Must be a valid LinkedIn company URL."})

        return data


class SecuritySignalSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecuritySignal
        fields = ["source", "signal_type", "value", "severity", "title", "description"]
        read_only_fields = fields


class OsintResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = OsintResult
        fields = ["source", "result_count", "query_value", "queried_at", "error_message"]
        read_only_fields = fields


class NarrativeOutputSerializer(serializers.Serializer):
    """Inline serializer for narrative data within report response."""

    headline = serializers.CharField()
    executive_brief = serializers.CharField(allow_blank=True, default="")
    findings = serializers.DictField(default=dict)
    correlated_data = serializers.DictField(default=dict)
    transition = serializers.CharField(allow_blank=True, default="")


class ReportOutputSerializer(serializers.ModelSerializer):
    """Full report response serializer."""

    company = serializers.SerializerMethodField()
    signals = SecuritySignalSerializer(many=True, read_only=True)
    narrative = serializers.SerializerMethodField()
    osint_sources = serializers.SerializerMethodField()

    class Meta:
        model = Analysis
        fields = ["id", "status", "company", "signals", "narrative", "osint_sources", "created_at"]
        read_only_fields = fields

    def get_company(self, obj):
        company = obj.company
        data = {
            "domain": company.domain,
            "name": company.name,
        }
        try:
            enrichment = company.enrichment
            data["industry"] = enrichment.industry
            data["employee_range"] = enrichment.employee_range
            data["description"] = enrichment.description
        except Exception:
            data["industry"] = ""
            data["employee_range"] = ""
            data["description"] = ""
        return data

    def get_narrative(self, obj):
        narrative = getattr(obj, "_narrative", None)
        if narrative is None:
            narrative = obj.narrative.first() if hasattr(obj, "narrative") else None
        if narrative:
            return {
                "headline": narrative.headline,
                "executive_brief": narrative.executive_brief,
                "findings": narrative.findings,
                "correlated_data": narrative.correlated_data,
                "transition": narrative.transition,
            }
        return None

    def get_osint_sources(self, obj):
        """List OSINT sources that returned data for this analysis."""
        results = obj.osint_results.all() if hasattr(obj, "osint_results") else []
        return OsintResultSerializer(results, many=True).data


class AuditDataSerializer(serializers.Serializer):
    """Serializer for audit mode raw DeHashed data."""

    query_domain = serializers.CharField()
    query_email = serializers.CharField()
    result_count = serializers.IntegerField()
    unique_emails = serializers.IntegerField()
    breach_sources = serializers.IntegerField()
    queried_at = serializers.DateTimeField()
    entries = serializers.SerializerMethodField()

    def get_entries(self, obj):
        raw = obj.raw_response
        entries = raw.get("entries", [])
        return [mask_dehashed_entry(e) for e in entries]
