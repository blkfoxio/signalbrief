"""Narrative serializers."""

from rest_framework import serializers

from .models import Narrative


class NarrativeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Narrative
        fields = [
            "headline",
            "executive_narrative",
            "talk_track",
            "business_impact",
            "transition",
            "generated_at",
        ]
        read_only_fields = fields
