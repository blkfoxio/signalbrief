"""Company serializers."""

from rest_framework import serializers

from .models import Company, CompanyEnrichment


class CompanyEnrichmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyEnrichment
        fields = ["industry", "employee_range", "description", "hq_location", "confidence_score"]
        read_only_fields = fields


class CompanySerializer(serializers.ModelSerializer):
    enrichment = CompanyEnrichmentSerializer(read_only=True)

    class Meta:
        model = Company
        fields = ["id", "domain", "name", "linkedin_url", "contact_email", "enrichment", "created_at"]
        read_only_fields = fields
