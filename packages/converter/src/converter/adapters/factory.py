"""Parser adapter selection."""

from __future__ import annotations

import os

from converter.contracts import DocumentParser


def get_parser(name: str | None = None) -> DocumentParser:
    selected = (name or os.environ.get("CONVERTER_PARSER", "native_pdf")).lower()
    if selected == "docling":
        from converter.adapters.docling_parser import DoclingParser

        return DoclingParser()
    if selected == "native_pdf":
        from converter.adapters.routed_pdf import RoutedPdfParser

        return RoutedPdfParser()
    if selected == "native_pdf_raw":
        from converter.adapters.native_pdf import NativePdfParser

        return NativePdfParser()
    raise ValueError(f"Unknown parser adapter: {selected}")
