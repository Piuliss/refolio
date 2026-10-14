from __future__ import annotations

from pathlib import Path

import pytest
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    pdf_path = tmp_path / "sample.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    c.setFont("Helvetica", 12)
    c.drawString(72, 720, "Capitulo uno")
    c.drawString(72, 700, "Este es un parrafo de prueba para conversion EPUB.")
    c.showPage()
    c.setFont("Helvetica", 12)
    c.drawString(72, 720, "Segunda pagina con otro parrafo sintetico.")
    c.save()
    return pdf_path
