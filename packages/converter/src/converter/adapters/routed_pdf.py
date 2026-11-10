"""Native extraction with per-page diagnostics and selective OCR routing."""

from __future__ import annotations

import uuid
from pathlib import Path

from converter.adapters.native_pdf import NativePdfParser, extract_page_lines
from converter.adapters.ocr_engine import OcrEngine, get_ocr_engine
from converter.contracts import AdapterCapability, AdapterInfo, DocumentParser, ParseContext
from converter.diagnostics.page_diagnostics import diagnose_page, page_text_from_lines
from converter.ir.models import (
    BlockType,
    BoundingBox,
    ChangeRecord,
    ContentBlock,
    DocumentIR,
    DocumentMetadata,
    ExtractionMethod,
    PageDiagnostic,
    PageRecord,
    PageRoute,
    Provenance,
    TransformOp,
    WarningRecord,
)


def _lines_to_blocks(
    page_index: int,
    lines: list[tuple[str, float, float, float, float]],
    order_start: int,
    method: ExtractionMethod,
    provider: str,
) -> tuple[list[ContentBlock], int]:
    blocks: list[ContentBlock] = []
    order = order_start
    for text, x0, y0, x1, y1 in lines:
        if not text.strip():
            continue
        block_id = f"blk_{uuid.uuid4().hex[:12]}"
        blocks.append(
            ContentBlock(
                id=block_id,
                block_type=BlockType.LINE,
                reading_order=order,
                original_text=text,
                current_text=text,
                provenance=Provenance(
                    page_indices=[page_index],
                    bboxes=[
                        BoundingBox(
                            x0=x0,
                            y0=y0,
                            x1=x1,
                            y1=y1,
                            page_index=page_index,
                        )
                    ],
                    extraction_method=method,
                    provider=provider,
                ),
                change_history=[
                    ChangeRecord(
                        op=TransformOp.EXTRACT,
                        reason="line_extracted",
                        evidence={"page_index": page_index},
                    )
                ],
            )
        )
        order += 1
    return blocks, order


class RoutedPdfParser(DocumentParser):
    """Default Phase 2 parser: native lines first, OCR only when needed."""

    def __init__(
        self,
        native: NativePdfParser | None = None,
        ocr: OcrEngine | None = None,
    ) -> None:
        self._native = native or NativePdfParser()
        self._ocr = ocr

    def info(self) -> AdapterInfo:
        caps = (
            AdapterCapability.NATIVE_TEXT,
            AdapterCapability.LAYOUT_BLOCKS,
            AdapterCapability.READING_ORDER,
        )
        return AdapterInfo(
            name="routed_pdf",
            version="0.2.0",
            capabilities=(*caps, AdapterCapability.OCR),
            license_spdx="BSD-3-Clause",
            limitations=(
                "OCR runs only for pages flagged by diagnostics when an engine is configured.",
                "Unconfigured OCR never invents text.",
            ),
            runtime_requirements=("pypdf",),
        )

    def parse(self, ctx: ParseContext) -> DocumentIR:
        reader_meta = self._native.read_metadata(ctx)
        pages: list[PageRecord] = []
        blocks: list[ContentBlock] = []
        warnings: list[WarningRecord] = []
        diagnostics: list[PageDiagnostic] = []
        order = 0
        ocr_engine = self._ocr if self._ocr is not None else get_ocr_engine()

        page_limit = reader_meta.page_count
        if ctx.max_pages is not None:
            page_limit = min(page_limit, ctx.max_pages)

        for idx in range(page_limit):
            page_info = reader_meta.pages[idx]
            pages.append(page_info)
            native_lines = extract_page_lines(ctx.source_path, idx)
            page_text = page_text_from_lines([ln[0] for ln in native_lines])
            diag = diagnose_page(idx, page_text)
            method = ExtractionMethod.NATIVE_PDF
            provider = "native_pdf"
            lines = native_lines

            if diag.route == PageRoute.OCR_RECOMMENDED:
                if ocr_engine is None:
                    diag = diag.model_copy(
                        update={"route": PageRoute.OCR_SKIPPED_UNAVAILABLE}
                    )
                    warnings.append(
                        WarningRecord(
                            code="ocr_skipped_unavailable",
                            message=(
                                "Page needs OCR but no engine is configured; "
                                "native extraction may be empty or unreliable."
                            ),
                            page_index=idx,
                        )
                    )
                else:
                    ocr_result = ocr_engine.recognize_page(
                        ctx.source_path, idx, ctx.language_hint
                    )
                    if ocr_result.success and ocr_result.lines:
                        diag = diag.model_copy(update={"route": PageRoute.OCR_APPLIED})
                        method = ExtractionMethod.OCR
                        provider = ocr_result.provider
                        lines = [
                            (
                                ln.text,
                                ln.x0,
                                ln.y0,
                                ln.x1,
                                ln.y1,
                            )
                            for ln in ocr_result.lines
                        ]
                    else:
                        diag = diag.model_copy(
                            update={"route": PageRoute.OCR_SKIPPED_UNAVAILABLE}
                        )
                        warnings.append(
                            WarningRecord(
                                code="ocr_failed",
                                message=ocr_result.error_message
                                or "OCR did not return text for this page.",
                                page_index=idx,
                            )
                        )

            diagnostics.append(diag)
            if not lines:
                warnings.append(
                    WarningRecord(
                        code="empty_page_text",
                        message="No extractable text on page after routing.",
                        page_index=idx,
                    )
                )
                continue

            new_blocks, order = _lines_to_blocks(
                idx, lines, order, method, provider
            )
            blocks.extend(new_blocks)

        meta = DocumentMetadata(
            title=reader_meta.title,
            language=ctx.language_hint or "es",
            source_filename=Path(ctx.source_path).name,
        )
        return DocumentIR(
            metadata=meta,
            pages=pages,
            blocks=blocks,
            warnings=warnings,
            page_diagnostics=diagnostics,
            engine_trace={
                "parser": self.info().name,
                "page_count": reader_meta.page_count,
                "ocr_engine": (
                    ocr_engine.info().name if ocr_engine is not None else None
                ),
            },
        )
