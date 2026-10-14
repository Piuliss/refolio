from django.urls import path

from apps.conversions.views import (
    ConversionCreateView,
    JobArtifactsView,
    JobCancelView,
    JobDetailView,
    JobIssuesView,
    JobQualityReportView,
)

urlpatterns = [
    path(
        "documents/<uuid:document_id>/conversions/",
        ConversionCreateView.as_view(),
        name="conversion-create",
    ),
    path("jobs/<uuid:pk>/", JobDetailView.as_view(), name="job-detail"),
    path("jobs/<uuid:pk>/cancel/", JobCancelView.as_view(), name="job-cancel"),
    path("jobs/<uuid:pk>/artifacts/", JobArtifactsView.as_view(), name="job-artifacts"),
    path("jobs/<uuid:pk>/issues/", JobIssuesView.as_view(), name="job-issues"),
    path("jobs/<uuid:pk>/quality-report/", JobQualityReportView.as_view(), name="job-quality"),
]
