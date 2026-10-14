from __future__ import annotations

import io

import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from reportlab.pdfgen import canvas
from rest_framework.test import APIClient


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def user(db) -> User:
    return User.objects.create_user(username="tester", password="testpass123")


@pytest.fixture
def pdf_bytes() -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(72, 720, "Hola mundo sintetico.")
    c.save()
    return buf.getvalue()


@pytest.mark.django_db
def test_upload_and_convert(api_client: APIClient, user: User, pdf_bytes: bytes) -> None:
    api_client.force_authenticate(user=user)
    upload = SimpleUploadedFile("sample.pdf", pdf_bytes, content_type="application/pdf")
    resp = api_client.post("/api/v1/documents/", {"file": upload, "language_hint": "es"})
    assert resp.status_code == 201
    doc_id = resp.json()["id"]

    conv = api_client.post(f"/api/v1/documents/{doc_id}/conversions/")
    assert conv.status_code == 201
    job_id = conv.json()["id"]

    detail = api_client.get(f"/api/v1/jobs/{job_id}/")
    assert detail.status_code == 200
    assert detail.json()["status"] in {"completed", "failed", "running", "queued"}

    if detail.json()["status"] == "completed":
        arts = api_client.get(f"/api/v1/jobs/{job_id}/artifacts/")
        assert arts.status_code == 200
        kinds = {a["kind"] for a in arts.json()}
        assert "epub" in kinds
