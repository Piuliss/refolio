"""Native-text PDF parser (pypdf) with line-level geometry."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

from converter.contracts import AdapterCapability, AdapterInfo, DocumentParser, ParseContext
from converter.ir.models import (
    BlockType,
    ContentBlock,
    DocumentIR,
    DocumentMetadata,
    ExtractionMethod,
    PageRecord,
    Provenance,
    WarningRecord,
)


@dataclass
class PdfReaderMeta:
    title: str | None
    page_count: int
    pages: list[PageRecord]


def extract_page_lines(
    source_path: Path,
    page_index: int,
) -> list[tuple[str, float, float, float, float]]:
    """Return (text, x0, y0, x1, y1) per visual line on a page."""
    reader = PdfReader(str(source_path))
    page = reader.pages[page_index]
    mediabox = page.mediabox
    page_h = float(mediabox.height)
    page_w = float(mediabox.width)

    spans: list[tuple[float, float, str]] = []

    def visitor(text: str, cm: object, tm: tuple[float, ...], font_dict: object, font_size: float) -> None:
        if not text or not text.strip():
            return
        x = float(tm[4])
        y = float(tm[5])
        spans.append((y, x, text))

    page.extract_text(visitor_text=visitor)
    if not spans:
        raw = page.extract_text() or ""
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        return [(ln, 72.0, page_h - 72.0, page_w - 72.0, page_h - 84.0) for ln in lines]

    # Group spans on similar baseline (y).
    spans.sort(key=lambda s: (-s[0], s[1]))
    grouped: list[list[tuple[float, float, str]]] = []
    y_tol = 2.5
    for y, x, text in spans:
        if not grouped or abs(grouped[-1][0][0] - y) > y_tol:
            grouped.append([(y, x, text)])
        else:
            grouped[-1].append((y, x, text))

    lines_out: list[tuple[str, float, float, float, float]] = []
    for row in grouped:
        row.sort(key=lambda s: s[1])
        text = "".join(t[2] for t in row).strip()
        if not text:
            continue
        xs = [t[1] for t in row]
        ys = [t[0] for t in row]
        x0, x1 = min(xs), max(xs) + 40.0
        y0, y1 = min(ys) - 2.0, max(ys) + font_size_guess(row)
        lines_out.append((text, x0, y0, x1, min(y1, page_h)))
    return lines_out


def font_size_guess(row: list[tuple[float, float, str]]) -> float:
    return 12.0


class NativePdfParser(DocumentParser):
    def info(self) -> AdapterInfo:
        return AdapterInfo(
            name="native_pdf",
            version="0.2.0",
            capabilities=(AdapterCapability.NATIVE_TEXT, AdapterCapability.LAYOUT_BLOCKS),
            license_spdx="BSD-3-Clause",
            limitations=(
                "Scanned PDFs without text layer need OCR routing.",
                "Line grouping uses heuristics on text matrix positions.",
            ),
            runtime_requirements=("pypdf",),
        )

    def read_metadata(self, ctx: ParseContext) -> PdfReaderMeta:
        reader = PdfReader(str(ctx.source_path))
        pages: list[PageRecord] = []
        limit = len(reader.pages)
        if ctx.max_pages is not None:
            limit = min(limit, ctx.max_pages)
        for idx in range(limit):
            page = reader.pages[idx]
            mediabox = page.mediabox
            pages.append(
                PageRecord(
                    index=idx,
                    width_pt=float(mediabox.width),
                    height_pt=float(mediabox.height),
                )
            )
        title = reader.metadata.title if reader.metadata else None
        return PdfReaderMeta(title=title, page_count=len(reader.pages), pages=pages)

    def parse(self, ctx: ParseContext) -> DocumentIR:
        meta_reader = self.read_metadata(ctx)
        pages = meta_reader.pages
        blocks: list[ContentBlock] = []
        warnings: list[WarningRecord] = []
        order = 0

        for page_rec in pages:
            idx = page_rec.index
            lines = extract_page_lines(ctx.source_path, idx)
            if not lines:
                warnings.append(
                    WarningRecord(
                        code="empty_page_text",
                        message="No extractable text on page; may be scanned or image-only.",
                        page_index=idx,
                    )
                )
                continue
            for text, x0, y0, x1, y1 in lines:
                block_id = f"blk_{uuid.uuid4().hex[:12]}"
                from converter.ir.models import BoundingBox

                blocks.append(
                    ContentBlock(
                        id=block_id,
                        block_type=BlockType.LINE,
                        reading_order=order,
                        original_text=text,
                        current_text=text,
                        provenance=Provenance(
                            page_indices=[idx],
                            bboxes=[
                                BoundingBox(
                                    x0=x0,
                                    y0=y0,
                                    x1=x1,
                                    y1=y1,
                                    page_index=idx,
                                )
                            ],
                            extraction_method=ExtractionMethod.NATIVE_PDF,
                            provider="native_pdf",
                        ),
                    )
                )
                order += 1

        meta = DocumentMetadata(
            title=meta_reader.title,
            language=ctx.language_hint or "es",
            source_filename=Path(ctx.source_path).name,
        )
        return DocumentIR(
            metadata=meta,
            pages=pages,
            blocks=blocks,
            warnings=warnings,
            engine_trace={"parser": self.info().name, "page_count": meta_reader.page_count},
        )
