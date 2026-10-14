from __future__ import annotations

from converter.diagnostics.page_diagnostics import diagnose_page
from converter.ir.models import PageRoute


def test_native_route_for_normal_text() -> None:
    diag = diagnose_page(0, "Capítulo uno\nTexto con suficientes caracteres alfanuméricos.")
    assert diag.route == PageRoute.NATIVE
    assert diag.char_count > 20


def test_ocr_recommended_for_sparse_page() -> None:
    diag = diagnose_page(1, "   ")
    assert diag.route == PageRoute.OCR_RECOMMENDED


def test_ocr_recommended_for_symbol_heavy_text() -> None:
    diag = diagnose_page(2, "### *** ...")
    assert diag.route == PageRoute.OCR_RECOMMENDED
