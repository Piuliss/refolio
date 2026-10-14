"""Conservative paragraph reconstruction from lines."""

from __future__ import annotations

import re
import uuid

from converter.ir.models import (
    BlockType,
    ChangeRecord,
    ContentBlock,
    ExtractionMethod,
    Provenance,
    TransformOp,
)

_SENTENCE_END = re.compile(r"[.!?…][\"')\]]*\s*$")
_HYPHEN_BREAK = re.compile(r"-\s*$")
_CONTINUATION_START = re.compile(r"^[a-záéíóúñü]")


def _merge_text(left: str, right: str) -> str:
    if _HYPHEN_BREAK.search(left):
        return left.rstrip()[:-1] + right.lstrip()
    return f"{left.rstrip()} {right.lstrip()}"


def _should_join(prev: ContentBlock, nxt: ContentBlock) -> tuple[bool, str]:
    if prev.block_type != BlockType.LINE or nxt.block_type != BlockType.LINE:
        return False, ""
    if prev.provenance.page_indices != nxt.provenance.page_indices:
        # Cross-page join only with explicit hyphen continuation.
        if _HYPHEN_BREAK.search(prev.current_text):
            return True, "hyphen_across_page"
        return False, ""
    prev_text = prev.current_text.strip()
    nxt_text = nxt.current_text.strip()
    if not prev_text or not nxt_text:
        return False, ""
    if _SENTENCE_END.search(prev_text):
        return False, ""
    if _HYPHEN_BREAK.search(prev_text):
        return True, "hyphen_line_break"
    if _CONTINUATION_START.match(nxt_text):
        return True, "lowercase_continuation"
    return False, ""


def reconstruct_paragraphs(blocks: list[ContentBlock]) -> list[ContentBlock]:
    """Merge LINE blocks into PARAGRAPH blocks using conservative rules."""
    out: list[ContentBlock] = []
    order = 0
    i = 0
    sorted_blocks = sorted(blocks, key=lambda b: b.reading_order)

    while i < len(sorted_blocks):
        block = sorted_blocks[i]
        if block.block_type != BlockType.LINE:
            block.reading_order = order
            out.append(block)
            order += 1
            i += 1
            continue

        merged = block
        reasons: list[str] = []
        j = i + 1
        while j < len(sorted_blocks):
            nxt = sorted_blocks[j]
            ok, reason = _should_join(merged, nxt)
            if not ok:
                break
            reasons.append(reason)
            new_text = _merge_text(merged.current_text, nxt.current_text)
            pages = sorted(
                set(merged.provenance.page_indices + nxt.provenance.page_indices)
            )
            bboxes = merged.provenance.bboxes + nxt.provenance.bboxes
            merged = merged.model_copy(
                update={
                    "current_text": new_text,
                    "provenance": Provenance(
                        page_indices=pages,
                        bboxes=bboxes,
                        extraction_method=merged.provenance.extraction_method,
                        provider=merged.provenance.provider,
                        provider_confidence=merged.provenance.provider_confidence,
                    ),
                    "change_history": [
                        *merged.change_history,
                        ChangeRecord(
                            op=TransformOp.JOIN_LINES,
                            reason=reason,
                            evidence={"joined_block_id": nxt.id},
                            previous_text=merged.current_text,
                        ),
                    ],
                }
            )
            j += 1

        para_id = f"blk_{uuid.uuid4().hex[:12]}"
        out.append(
            ContentBlock(
                id=para_id,
                block_type=BlockType.PARAGRAPH,
                reading_order=order,
                original_text=block.original_text,
                current_text=merged.current_text,
                provenance=merged.provenance,
                change_history=[
                    *block.change_history,
                    ChangeRecord(
                        op=TransformOp.JOIN_LINES,
                        reason="paragraph_reconstructed",
                        evidence={"join_steps": reasons},
                    ),
                ],
            )
        )
        order += 1
        i = j

    return out
