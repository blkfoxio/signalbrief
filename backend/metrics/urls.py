from django.urls import path

from . import views

urlpatterns = [
    path("overview/", views.overview, name="metrics-overview"),
    path("sources/", views.sources, name="metrics-sources"),
    path("recent-failures/", views.recent_failures, name="metrics-recent-failures"),
    path("users/", views.users_list, name="metrics-users"),
    path("reports/", views.reports_list, name="metrics-reports"),
]
