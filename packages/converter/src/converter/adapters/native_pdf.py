"""Native-text PDF parser (pypdf) with line-level geometry."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

from converter.contracts import AdapterCapability, AdapterInfo, DocumentParser, ParseContext
from converter.ir.models import (
    BlockType,
    BoundingBox,
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


def _span_xy(tm: tuple[float, ...], page_w: float, page_h: float) -> tuple[float, float]:
    """Map text matrix translation to PDF user space (origin bottom-left).

    Most writers use tm[4]=x, tm[5]=y; some (e.g. ReportLab via pypdf) swap them.
    """
    if len(tm) < 6:
        return 0.0, 0.0
    e = float(tm[4])
    f = float(tm[5])
    if e <= page_w and f <= page_h:
        return e, f
    if f <= page_w and e <= page_h:
        return f, e
    return e, f


def _merge_row_spans(row: list[tuple[float, float, str, float]]) -> str:
    """Join same-line spans; insert spaces when glyph positions gap."""
    row = sorted(row, key=lambda s: s[0])
    if not row:
        return ""
    parts: list[str] = []
    prev_x = row[0][0]
    prev_text = row[0][2]
    prev_size = row[0][3]
    parts.append(prev_text)
    for x, _y, text, size in row[1:]:
        char_w = max(prev_size * 0.45, 2.0)
        estimated_end = prev_x + len(prev_text.rstrip()) * char_w
        gap = x - estimated_end
        if gap > 1.5 and not parts[-1].endswith(("-", " ")) and not text.startswith(" "):
            parts.append(" ")
        parts.append(text)
        prev_x, prev_text, prev_size = x, text, size
    merged = "".join(parts)
    return " ".join(merged.split()) if "\n" in merged else merged.strip()


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

    spans: list[tuple[float, float, str, float]] = []

    def visitor(
        text: str,
        cm: object,
        tm: tuple[float, ...],
        font_dict: object,
        font_size: float,
    ) -> None:
        if not text or not text.strip():
            return
        x, y = _span_xy(tm, page_w, page_h)
        spans.append((x, y, text, font_size))

    page.extract_text(visitor_text=visitor)
    if not spans:
        raw = page.extract_text() or ""
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        return [(ln, 72.0, page_h - 72.0, page_w - 72.0, page_h - 84.0) for ln in lines]

    spans.sort(key=lambda s: (-s[1], s[0]))
    grouped: list[list[tuple[float, float, str, float]]] = []
    y_tol = 3.0
    for x, y, text, size in spans:
        if not grouped or abs(grouped[-1][0][1] - y) > y_tol:
            grouped.append([(x, y, text, size)])
        else:
            grouped[-1].append((x, y, text, size))

    lines_out: list[tuple[str, float, float, float, float]] = []
    for row in grouped:
        text = _merge_row_spans(row)
        if not text:
            continue
        xs = [t[0] for t in row]
        ys = [t[1] for t in row]
        sizes = [t[3] for t in row]
        font_size = max(sizes) if sizes else 12.0
        x0, x1 = min(xs), max(xs) + font_size * 2
        y0, y1 = min(ys) - 2.0, max(ys) + font_size
        lines_out.append((text, x0, y0, x1, min(y1, page_h)))
    lines_out.sort(key=lambda line: (-line[2], line[1]))
    return lines_out


class NativePdfParser(DocumentParser):
    def info(self) -> AdapterInfo:
        return AdapterInfo(
            name="native_pdf",
            version="0.2.1",
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
