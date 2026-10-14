from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models

from apps.documents.models import Document


class JobStatus(models.TextChoices):
    QUEUED = "queued", "Queued"
    RUNNING = "running", "Running"
    AWAITING_REVIEW = "awaiting_review", "Awaiting review"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"
    CANCELED = "canceled", "Canceled"


class ArtifactKind(models.TextChoices):
    IR_JSON = "ir_json", "IR JSON"
    EPUB = "epub", "EPUB"
    QUALITY_REPORT = "quality_report", "Quality report"


def artifact_upload_to(instance: Artifact, filename: str) -> str:
    return f"jobs/{instance.job_id}/artifacts/{filename}"


class ConversionJob(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="jobs")
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversion_jobs",
    )
    status = models.CharField(
        max_length=32,
        choices=JobStatus.choices,
        default=JobStatus.QUEUED,
    )
    progress_message = models.CharField(max_length=512, blank=True)
    error_message = models.TextField(blank=True)
    parser_name = models.CharField(max_length=64, blank=True)
    engine_version = models.CharField(max_length=32, blank=True)
    celery_task_id = models.CharField(max_length=255, blank=True)
    cancel_requested = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class Artifact(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(ConversionJob, on_delete=models.CASCADE, related_name="artifacts")
    kind = models.CharField(max_length=32, choices=ArtifactKind.choices)
    file = models.FileField(upload_to=artifact_upload_to)
    created_at = models.DateTimeField(auto_now_add=True)


class QualityReportRecord(models.Model):
    job = models.OneToOneField(
        ConversionJob,
        on_delete=models.CASCADE,
        related_name="quality_report",
    )
    payload = models.JSONField(default=dict)
