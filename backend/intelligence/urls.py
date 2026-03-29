"""Intelligence/reports URL routes."""

from django.urls import path

from . import views

urlpatterns = [
    path("", views.report_list_create, name="report-list-create"),
    path("<uuid:report_id>/", views.report_detail, name="report-detail"),
    path("<uuid:report_id>/raw/", views.report_audit, name="report-audit"),
    path("<uuid:report_id>/raw/<str:source>/", views.report_osint_raw, name="report-osint-raw"),
    path("<uuid:report_id>/rerun/", views.report_rerun, name="report-rerun"),
]
