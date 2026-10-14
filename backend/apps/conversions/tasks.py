from __future__ import annotations

import os
from pathlib import Path

from celery import shared_task
from django.conf import settings
from django.core.files import File
from django.utils import timezone

from apps.conversions.models import (
    Artifact,
    ArtifactKind,
    ConversionJob,
    JobStatus,
    QualityReportRecord,
)
from converter.adapters.factory import get_parser
from converter.pipeline import ConversionPipeline


@shared_task(bind=True)
def run_conversion_job(self, job_id: str) -> None:
    job = ConversionJob.objects.select_related("document").get(pk=job_id)
    if job.cancel_requested:
        job.status = JobStatus.CANCELED
        job.finished_at = timezone.now()
        job.save(update_fields=["status", "finished_at", "updated_at"])
        return

    job.status = JobStatus.RUNNING
    job.started_at = timezone.now()
    job.celery_task_id = self.request.id or ""
    job.progress_message = "Parsing PDF"
    job.save(
        update_fields=[
            "status",
            "started_at",
            "celery_task_id",
            "progress_message",
            "updated_at",
        ]
    )

    work_root = Path(settings.CONVERTER_WORK_DIR) / str(job.id)
    work_root.mkdir(parents=True, exist_ok=True)

    try:
        if job.cancel_requested:
            raise JobCanceledError()

        os.environ["CONVERTER_PARSER"] = settings.CONVERTER_PARSER
        parser = get_parser(settings.CONVERTER_PARSER)
        job.parser_name = parser.info().name
        pipeline = ConversionPipeline(parser=parser)
        source = Path(job.document.file.path)
        result = pipeline.run(
            source_pdf=source,
            output_dir=work_root,
            language_hint=job.document.language_hint,
        )
        job.engine_version = result.engine_version
        job.progress_message = "Persisting artifacts"

        _store_artifact(job, ArtifactKind.IR_JSON, result.ir_path)
        _store_artifact(job, ArtifactKind.EPUB, result.epub_path)
        qr_path = work_root / "quality_report.json"
        _store_artifact(job, ArtifactKind.QUALITY_REPORT, qr_path)
        QualityReportRecord.objects.update_or_create(
            job=job,
            defaults={"payload": result.quality_report.to_dict()},
        )

        job.status = JobStatus.COMPLETED
        job.progress_message = "Done"
        job.finished_at = timezone.now()
        job.save()
    except JobCanceledError:
        job.status = JobStatus.CANCELED
        job.finished_at = timezone.now()
        job.save(update_fields=["status", "finished_at", "updated_at"])
    except Exception as exc:
        job.status = JobStatus.FAILED
        job.error_message = str(exc)
        job.finished_at = timezone.now()
        job.save(update_fields=["status", "error_message", "finished_at", "updated_at"])
        raise


class JobCanceledError(Exception):
    pass


def _store_artifact(job: ConversionJob, kind: str, path: Path) -> None:
    with path.open("rb") as fh:
        artifact = Artifact(job=job, kind=kind)
        artifact.file.save(path.name, File(fh), save=True)
