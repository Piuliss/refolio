from __future__ import annotations

from pathlib import Path

from converter.adapters.ocr_engine import UnconfiguredOcrEngine
from converter.adapters.routed_pdf import RoutedPdfParser
from converter.contracts import ParseContext
from converter.ir.models import PageRoute


def test_ocr_recommended_emits_warning_without_engine(empty_pdf: Path) -> None:
    parser = RoutedPdfParser(ocr=None)
    doc = parser.parse(ParseContext(source_path=empty_pdf))
    assert doc.page_diagnostics
    assert doc.page_diagnostics[0].route == PageRoute.OCR_SKIPPED_UNAVAILABLE
    assert any(w.code == "ocr_skipped_unavailable" for w in doc.warnings)


def test_stub_ocr_does_not_fake_success(sample_pdf: Path) -> None:
    parser = RoutedPdfParser(ocr=UnconfiguredOcrEngine())
    doc = parser.parse(ParseContext(source_path=sample_pdf, language_hint="es"))
    assert not any(w.code == "ocr_applied" for w in doc.warnings)
    # Native text pages stay on native route.
    assert any(d.route == PageRoute.NATIVE for d in doc.page_diagnostics)
