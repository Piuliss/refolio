from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from converter.adapters.ocr_engine import get_ocr_engine
from converter.adapters.routed_pdf import RoutedPdfParser
from converter.contracts import ParseContext
from converter.ir.models import PageRoute


def test_get_ocr_engine_tesseract_factory() -> None:
    engine = get_ocr_engine("tesseract")
    assert engine is not None
    assert engine.info().name == "tesseract"


def test_factura_page_tesseract_smoke() -> None:
    if not shutil.which("tesseract"):
        pytest.skip("tesseract binary not installed")
    factura = (
        Path(__file__).resolve().parents[3]
        / "notebooks"
        / ".local"
        / "pdfs"
        / "facturas"
        / "IMAG0007.PDF"
    )
    if not factura.is_file():
        pytest.skip("local factura fixture not present")
    parser = RoutedPdfParser(ocr=get_ocr_engine("tesseract"))
    doc = parser.parse(ParseContext(source_path=factura, max_pages=1, language_hint="es"))
    assert doc.page_diagnostics[0].route == PageRoute.OCR_APPLIED
    assert any(b.current_text.strip() for b in doc.blocks)
