"""Intelligence/reports URL routes."""

from django.urls import path

from . import views

urlpatterns = [
    path("", views.report_list_create, name="report-list-create"),
    path("<uuid:report_id>/", views.report_detail, name="report-detail"),
    path("<uuid:report_id>/raw/", views.report_audit, name="report-audit"),
]
