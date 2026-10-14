"""OCR adapter interface and explicit unconfigured implementation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from converter.contracts import AdapterCapability, AdapterInfo


@dataclass(frozen=True)
class OcrLine:
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    confidence: float | None = None


@dataclass
class OcrPageResult:
    page_index: int
    success: bool
    lines: tuple[OcrLine, ...] = ()
    error_message: str | None = None
    provider: str = "unconfigured"


@runtime_checkable
class OcrEngine(Protocol):
    def info(self) -> AdapterInfo: ...

    def recognize_page(
        self,
        source_pdf: Path,
        page_index: int,
        language_hint: str | None = None,
    ) -> OcrPageResult: ...


class UnconfiguredOcrEngine:
    """Does not fabricate OCR output; reports explicit unavailability."""

    def info(self) -> AdapterInfo:
        return AdapterInfo(
            name="ocr_unconfigured",
            version="0.1.0",
            capabilities=(AdapterCapability.OCR,),
            license_spdx="N/A",
            limitations=("No OCR engine installed or selected.",),
            runtime_requirements=(),
        )

    def recognize_page(
        self,
        source_pdf: Path,
        page_index: int,
        language_hint: str | None = None,
    ) -> OcrPageResult:
        return OcrPageResult(
            page_index=page_index,
            success=False,
            error_message=(
                "OCR was recommended for this page but no OCR engine is configured. "
                "Set CONVERTER_OCR_ENGINE when a real adapter is available."
            ),
            provider=self.info().name,
        )


def get_ocr_engine(name: str | None = None) -> OcrEngine | None:
    import os

    selected = (name or os.environ.get("CONVERTER_OCR_ENGINE", "")).strip().lower()
    if not selected or selected in {"none", "off", "unconfigured"}:
        return None
    if selected == "stub":
        return UnconfiguredOcrEngine()
    raise ValueError(f"Unknown OCR engine: {selected}")
