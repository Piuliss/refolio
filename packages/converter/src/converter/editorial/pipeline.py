"""Run editorial transforms on a parsed DocumentIR."""

from __future__ import annotations

from converter.editorial.chapters import detect_chapters
from converter.editorial.paragraphs import reconstruct_paragraphs
from converter.editorial.running_matter import remove_running_matter
from converter.ir.models import DocumentIR


def apply_editorial_passes(document: DocumentIR) -> DocumentIR:
    page_heights = {
        p.index: (p.height_pt or 792.0) for p in document.pages
    }
    page_count = len(document.pages)

    rm = remove_running_matter(document.blocks, page_heights, page_count)
    paragraphs = reconstruct_paragraphs(rm.blocks)
    chapters, chapter_warnings = detect_chapters(paragraphs)

    trace = dict(document.engine_trace)
    trace["editorial"] = {
        "running_matter_removed": len(rm.removed_block_ids),
        "paragraph_blocks": sum(1 for b in chapters if b.block_type.value == "paragraph"),
        "chapter_titles": sum(1 for b in chapters if b.block_type.value == "title"),
    }

    return document.model_copy(
        update={
            "blocks": chapters,
            "warnings": [*document.warnings, *rm.warnings, *chapter_warnings],
            "engine_trace": trace,
        }
    )
