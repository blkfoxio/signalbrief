"""Narrative serializers."""

from rest_framework import serializers

from .models import Narrative


class NarrativeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Narrative
        fields = [
            "headline",
            "executive_brief",
            "findings",
            "correlated_data",
            "transition",
            "generated_at",
        ]
        read_only_fields = fields
