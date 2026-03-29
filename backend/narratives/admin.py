from django.contrib import admin

from .models import Narrative


@admin.register(Narrative)
class NarrativeAdmin(admin.ModelAdmin):
    list_display = ("headline", "model_used", "generated_at")
    search_fields = ("headline",)
    readonly_fields = ("prompt_hash",)
