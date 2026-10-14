"""Docling structured PDF parser adapter."""

from __future__ import annotations

import uuid
from pathlib import Path

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


def _map_label(label: str) -> BlockType:
    normalized = label.lower()
    if normalized in {"title", "section_header", "heading"}:
        return BlockType.TITLE
    if normalized in {"list_item"}:
        return BlockType.LIST_ITEM
    if normalized in {"caption", "figure"}:
        return BlockType.IMAGE
    if normalized in {"table"}:
        return BlockType.TABLE
    return BlockType.PARAGRAPH


class DoclingParser(DocumentParser):
    def info(self) -> AdapterInfo:
        return AdapterInfo(
            name="docling",
            version="2.138.0",
            capabilities=(
                AdapterCapability.NATIVE_TEXT,
                AdapterCapability.LAYOUT_BLOCKS,
                AdapterCapability.READING_ORDER,
                AdapterCapability.TABLES,
                AdapterCapability.IMAGES,
            ),
            license_spdx="MIT",
            limitations=(
                "Heavy ML dependencies; first run may download models.",
                "OCR paths not enabled in Phase 1 default configuration.",
            ),
            runtime_requirements=("docling==2.138.0", "optional GPU"),
        )

    def parse(self, ctx: ParseContext) -> DocumentIR:
        from docling.document_converter import DocumentConverter  # type: ignore[import-not-found]

        converter = DocumentConverter()
        result = converter.convert(str(ctx.source_path))
        doc = result.document

        pages: list[PageRecord] = []
        blocks: list[ContentBlock] = []
        warnings: list[WarningRecord] = []
        order = 0

        for page_no, page in enumerate(doc.pages):
            if ctx.max_pages is not None and page_no >= ctx.max_pages:
                break
            size = page.size
            pages.append(
                PageRecord(
                    index=page_no,
                    width_pt=float(size.width) if size else None,
                    height_pt=float(size.height) if size else None,
                )
            )

        for item, _level in doc.iterate_items():
            text = getattr(item, "text", None) or ""
            if not str(text).strip():
                continue
            label = getattr(item, "label", "paragraph")
            block_type = _map_label(str(label))
            prov_pages: list[int] = []
            if hasattr(item, "prov") and item.prov:
                for p in item.prov:
                    if hasattr(p, "page_no"):
                        prov_pages.append(int(p.page_no))
            if not prov_pages and pages:
                prov_pages = [pages[0].index]

            block_id = f"blk_{uuid.uuid4().hex[:12]}"
            blocks.append(
                ContentBlock(
                    id=block_id,
                    block_type=block_type,
                    reading_order=order,
                    original_text=str(text).strip(),
                    current_text=str(text).strip(),
                    title_level=1 if block_type == BlockType.TITLE else None,
                    provenance=Provenance(
                        page_indices=prov_pages,
                        extraction_method=ExtractionMethod.DOCLING,
                        provider="docling",
                    ),
                )
            )
            order += 1

        if not blocks:
            warnings.append(
                WarningRecord(
                    code="docling_no_blocks",
                    message=(
                        "Docling returned no text blocks; check PDF or enable OCR later."
                    ),
                )
            )

        meta = DocumentMetadata(
            title=getattr(doc, "name", None) or Path(ctx.source_path).stem,
            language=ctx.language_hint or "es",
            source_filename=Path(ctx.source_path).name,
        )
        return DocumentIR(
            metadata=meta,
            pages=pages,
            blocks=blocks,
            warnings=warnings,
            engine_trace={"parser": "docling", "docling_export": "iterate_items"},
        )
