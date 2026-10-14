"""PaddleOCR adapter (optional extra — local CPU, no cloud)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from converter.adapters.ocr_deps import (
    format_missing_deps_message,
    missing_ocr_render_modules,
    missing_paddle_modules,
)
from converter.adapters.paddle_bootstrap import configure_paddle_runtime, format_paddle_runtime_error
from converter.adapters.ocr_engine import OcrLine, OcrPageResult
from converter.contracts import AdapterCapability, AdapterInfo

PADDLEOCR_PACKAGE_VERSION = "2.10.0"


class PaddleOcrEngine:
    """PP-OCR via paddleocr; models download on first use."""

    def __init__(self) -> None:
        self._lang = os.environ.get("CONVERTER_PADDLE_LANG", "es")
        self._scale = float(os.environ.get("CONVERTER_OCR_RENDER_SCALE", "1.5"))
        # Angle classifier doubles work; invoices are usually upright.
        angle = os.environ.get("CONVERTER_PADDLE_USE_ANGLE_CLS", "0").strip().lower()
        self._use_angle_cls = angle in {"1", "true", "yes", "on"}
        self._clients: dict[str, Any] = {}

    def info(self) -> AdapterInfo:
        return AdapterInfo(
            name="paddleocr",
            version=PADDLEOCR_PACKAGE_VERSION,
            capabilities=(AdapterCapability.OCR,),
            license_spdx="Apache-2.0",
            limitations=(
                "Requires paddleocr + paddlepaddle (optional extra).",
                "First run downloads detection/recognition models.",
                "CPU inference; large books are slow.",
            ),
            runtime_requirements=("paddleocr", "paddlepaddle", "pymupdf", "numpy"),
        )

    def _client_for_lang(self, lang: str) -> Any:
        if lang in self._clients:
            return self._clients[lang]
        configure_paddle_runtime()
        from paddleocr import PaddleOCR  # type: ignore[import-untyped]

        client = PaddleOCR(
            use_angle_cls=self._use_angle_cls,
            lang=lang,
            show_log=False,
            use_gpu=False,
            enable_mkldnn=False,
        )
        self._clients[lang] = client
        return client

    def recognize_page(
        self,
        source_pdf: Path,
        page_index: int,
        language_hint: str | None = None,
    ) -> OcrPageResult:
        lang = (language_hint or self._lang or "es").split("-")[0].lower()
        render_missing = missing_ocr_render_modules()
        if render_missing:
            return OcrPageResult(
                page_index=page_index,
                success=False,
                error_message=format_missing_deps_message(render_missing),
                provider=self.info().name,
            )
        paddle_missing = missing_paddle_modules()
        if paddle_missing:
            return OcrPageResult(
                page_index=page_index,
                success=False,
                error_message=format_missing_deps_message(paddle_missing),
                provider=self.info().name,
            )

        from converter.adapters.pdf_render import render_page_rgb

        try:
            img, page_w, page_h = render_page_rgb(source_pdf, page_index, scale=self._scale)
            ocr = self._client_for_lang(lang)
            raw = ocr.ocr(img, cls=self._use_angle_cls)
        except Exception as exc:  # noqa: BLE001 — surface real OCR failure to IR warnings
            detail = f"PaddleOCR failed: {type(exc).__name__}: {exc}"
            hint = format_paddle_runtime_error(exc)
            if hint:
                detail = f"{detail} Hint: {hint}"
            return OcrPageResult(
                page_index=page_index,
                success=False,
                error_message=detail,
                provider=self.info().name,
            )

        if not raw or raw[0] is None:
            return OcrPageResult(
                page_index=page_index,
                success=False,
                error_message="PaddleOCR returned no detections for this page.",
                provider=self.info().name,
            )

        scale_x = page_w / img.shape[1]
        scale_y = page_h / img.shape[0]
        ocr_lines: list[OcrLine] = []
        for item in raw[0]:
            box, rec = item
            text = (rec[0] or "").strip()
            score = float(rec[1]) if len(rec) > 1 else None
            if not text:
                continue
            xs = [float(p[0]) for p in box]
            ys = [float(p[1]) for p in box]
            x0 = min(xs) * scale_x
            x1 = max(xs) * scale_x
            y_top_img = min(ys) * scale_y
            y_bottom_img = max(ys) * scale_y
            y0 = page_h - y_bottom_img
            y1 = page_h - y_top_img
            ocr_lines.append(
                OcrLine(
                    text=text,
                    x0=x0,
                    y0=y0,
                    x1=x1,
                    y1=y1,
                    confidence=score,
                )
            )

        if not ocr_lines:
            return OcrPageResult(
                page_index=page_index,
                success=False,
                error_message="PaddleOCR detections contained no text.",
                provider=self.info().name,
            )

        ocr_lines.sort(key=lambda ln: (-(ln.y0 + ln.y1) / 2.0, ln.x0))
        return OcrPageResult(
            page_index=page_index,
            success=True,
            lines=tuple(ocr_lines),
            provider=self.info().name,
        )
