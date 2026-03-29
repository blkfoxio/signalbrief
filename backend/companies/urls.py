"""Company URL routes."""

from django.urls import path

from . import views

urlpatterns = [
    path("", views.company_list, name="company-list"),
    path("<str:domain>/", views.company_detail, name="company-detail"),
]
