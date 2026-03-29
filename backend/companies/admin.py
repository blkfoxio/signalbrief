from django.contrib import admin

from .models import Company, CompanyEnrichment


class CompanyEnrichmentInline(admin.StackedInline):
    model = CompanyEnrichment
    extra = 0


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("domain", "name", "created_by", "created_at")
    search_fields = ("domain", "name")
    inlines = [CompanyEnrichmentInline]
