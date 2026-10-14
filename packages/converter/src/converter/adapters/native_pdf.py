"""Minimal native-text PDF parser (pypdf). Real extraction, no OCR."""

from __future__ import annotations

import uuid
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


class NativePdfParser(DocumentParser):
    def info(self) -> AdapterInfo:
        return AdapterInfo(
            name="native_pdf",
            version="0.1.0",
            capabilities=(AdapterCapability.NATIVE_TEXT,),
            license_spdx="BSD-3-Clause",
            limitations=(
                "No layout or reading-order reconstruction beyond page sequence.",
                "Scanned PDFs without text layer produce empty or sparse output.",
                "Does not merge broken lines into paragraphs.",
            ),
            runtime_requirements=("pypdf",),
        )

    def parse(self, ctx: ParseContext) -> DocumentIR:
        reader = PdfReader(str(ctx.source_path))
        pages: list[PageRecord] = []
        blocks: list[ContentBlock] = []
        warnings: list[WarningRecord] = []
        order = 0

        page_limit = len(reader.pages)
        if ctx.max_pages is not None:
            page_limit = min(page_limit, ctx.max_pages)

        for idx in range(page_limit):
            page = reader.pages[idx]
            mediabox = page.mediabox
            pages.append(
                PageRecord(
                    index=idx,
                    width_pt=float(mediabox.width),
                    height_pt=float(mediabox.height),
                )
            )
            text = page.extract_text() or ""
            paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
            if not paragraphs and text.strip():
                paragraphs = [ln.strip() for ln in text.splitlines() if ln.strip()]

            if not paragraphs:
                warnings.append(
                    WarningRecord(
                        code="empty_page_text",
                        message="No extractable text on page; may be scanned or image-only.",
                        page_index=idx,
                    )
                )
                continue

            for para in paragraphs:
                block_id = f"blk_{uuid.uuid4().hex[:12]}"
                blocks.append(
                    ContentBlock(
                        id=block_id,
                        block_type=BlockType.PARAGRAPH,
                        reading_order=order,
                        original_text=para,
                        current_text=para,
                        provenance=Provenance(
                            page_indices=[idx],
                            extraction_method=ExtractionMethod.NATIVE_PDF,
                            provider="native_pdf",
                        ),
                    )
                )
                order += 1

        meta = DocumentMetadata(
            title=reader.metadata.title if reader.metadata else None,
            language=ctx.language_hint or "es",
            source_filename=Path(ctx.source_path).name,
        )
        return DocumentIR(
            metadata=meta,
            pages=pages,
            blocks=blocks,
            warnings=warnings,
            engine_trace={"parser": self.info().name, "page_count": len(reader.pages)},
        )
