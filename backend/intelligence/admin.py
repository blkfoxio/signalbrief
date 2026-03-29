from django.contrib import admin

from .models import Analysis, DehashedResult, SecuritySignal


class DehashedResultInline(admin.StackedInline):
    model = DehashedResult
    extra = 0
    readonly_fields = ("raw_response",)


class SecuritySignalInline(admin.TabularInline):
    model = SecuritySignal
    extra = 0


@admin.register(Analysis)
class AnalysisAdmin(admin.ModelAdmin):
    list_display = ("id", "company", "status", "created_by", "created_at")
    list_filter = ("status",)
    search_fields = ("company__domain", "company__name")
    inlines = [DehashedResultInline, SecuritySignalInline]
