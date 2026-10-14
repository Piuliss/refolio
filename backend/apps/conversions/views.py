from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.conversions.models import ConversionJob, JobStatus, QualityReportRecord
from apps.conversions.serializers import (
    ArtifactSerializer,
    ConversionJobSerializer,
    QualityReportSerializer,
)
from apps.conversions.tasks import run_conversion_job
from apps.documents.models import Document


class ConversionCreateView(generics.CreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ConversionJobSerializer

    def create(self, request, *args, **kwargs):
        doc_id = kwargs["document_id"]
        document = get_object_or_404(Document.objects.filter(owner=request.user), pk=doc_id)
        job = ConversionJob.objects.create(
            document=document,
            requested_by=request.user,
            status=JobStatus.QUEUED,
        )
        async_result = run_conversion_job.delay(str(job.id))
        job.celery_task_id = async_result.id or ""
        job.save(update_fields=["celery_task_id", "updated_at"])
        serializer = self.get_serializer(job)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class JobDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ConversionJobSerializer

    def get_queryset(self):
        return ConversionJob.objects.filter(requested_by=self.request.user)


class JobCancelView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        job = get_object_or_404(ConversionJob.objects.filter(requested_by=request.user), pk=pk)
        if job.status in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELED}:
            return Response(
                {"detail": f"Job already terminal: {job.status}"},
                status=status.HTTP_409_CONFLICT,
            )
        job.cancel_requested = True
        job.save(update_fields=["cancel_requested", "updated_at"])
        return Response(ConversionJobSerializer(job).data)


class JobArtifactsView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ArtifactSerializer

    def get_queryset(self):
        job = get_object_or_404(
            ConversionJob.objects.filter(requested_by=self.request.user),
            pk=self.kwargs["pk"],
        )
        return job.artifacts.all()


class JobIssuesView(APIView):
    """Phase 1: issues derived from quality report warnings (no review UI yet)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        job = get_object_or_404(ConversionJob.objects.filter(requested_by=request.user), pk=pk)
        try:
            report = job.quality_report
        except QualityReportRecord.DoesNotExist:
            return Response({"issues": []})
        issues = []
        payload = report.payload
        for note in payload.get("notes", []):
            issues.append({"severity": "info", "message": note})
        ev = payload.get("epub_validation") or {}
        if ev.get("passed") is False:
            issues.append({"severity": "error", "message": "EPUBCheck reported validation errors."})
        if ev.get("skipped_reason"):
            issues.append({"severity": "warning", "message": ev["skipped_reason"]})
        return Response({"issues": issues})


class JobQualityReportView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = QualityReportSerializer

    def get_object(self):
        job = get_object_or_404(
            ConversionJob.objects.filter(requested_by=self.request.user),
            pk=self.kwargs["pk"],
        )
        return get_object_or_404(QualityReportRecord, job=job)
