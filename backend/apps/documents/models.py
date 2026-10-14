from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


def document_upload_to(instance: Document, filename: str) -> str:
    return f"documents/{instance.id}/{filename}"


class Document(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    original_filename = models.CharField(max_length=512)
    file = models.FileField(upload_to=document_upload_to)
    mime_type = models.CharField(max_length=128, blank=True)
    size_bytes = models.BigIntegerField(default=0)
    page_count = models.PositiveIntegerField(null=True, blank=True)
    language_hint = models.CharField(max_length=16, default="es")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.original_filename
