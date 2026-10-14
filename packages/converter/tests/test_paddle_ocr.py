from __future__ import annotations

from pathlib import Path

import pytest

from converter.adapters.ocr_engine import get_ocr_engine
from converter.adapters.paddle_bootstrap import format_paddle_runtime_error
from converter.adapters.routed_pdf import RoutedPdfParser
from converter.contracts import ParseContext
from converter.ir.models import PageRoute


def test_format_paddle_runtime_error_allocator() -> None:
    hint = format_paddle_runtime_error(
        RuntimeError("(NotFound) No allocator found for the place, Place(undefined:0)")
    )
    assert hint is not None
    assert "2.6.2" in hint


def test_get_ocr_engine_paddle_factory() -> None:
    engine = get_ocr_engine("paddle")
    assert engine is not None
    assert engine.info().name == "paddleocr"


def test_factura_page_ocr_smoke() -> None:
    pytest.importorskip("paddleocr")
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
    parser = RoutedPdfParser(ocr=get_ocr_engine("paddle"))
    doc = parser.parse(ParseContext(source_path=factura, max_pages=1, language_hint="es"))
    assert doc.page_diagnostics[0].route == PageRoute.OCR_APPLIED
    assert any(b.current_text.strip() for b in doc.blocks)
