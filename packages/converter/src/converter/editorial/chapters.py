"""Conservative chapter heading detection (pattern-based, not font size)."""

from __future__ import annotations

import re

from converter.ir.models import BlockType, ChangeRecord, ContentBlock, TransformOp, WarningRecord

_CHAPTER = re.compile(
    r"^(?:cap[ií]tulo|chapter|parte)\s+([0-9]+|[IVXLC]+)\b",
    re.IGNORECASE,
)
_ROMAN_ONLY = re.compile(r"^[IVXLC]+\.?$")


def detect_chapters(blocks: list[ContentBlock]) -> tuple[list[ContentBlock], list[WarningRecord]]:
    warnings: list[WarningRecord] = []
    out: list[ContentBlock] = []
    for block in blocks:
        if block.block_type != BlockType.PARAGRAPH:
            out.append(block)
            continue
        text = block.current_text.strip()
        if _CHAPTER.match(text):
            out.append(
                block.model_copy(
                    update={
                        "block_type": BlockType.TITLE,
                        "title_level": 1,
                        "change_history": [
                            *block.change_history,
                            ChangeRecord(
                                op=TransformOp.PROMOTE_CHAPTER,
                                reason="chapter_heading_pattern",
                                evidence={"matched_text": text[:120]},
                            ),
                        ],
                    }
                )
            )
            continue
        if _ROMAN_ONLY.match(text) and len(text) <= 6:
            warnings.append(
                WarningRecord(
                    code="chapter_ambiguous",
                    message=f"Short roman token '{text}' not promoted to chapter (ambiguous).",
                    block_id=block.id,
                )
            )
        out.append(block)
    return out, warnings
