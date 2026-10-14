"""Repeated headers, footers, and isolated page numbers."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from converter.ir.models import (
    BlockType,
    ChangeRecord,
    ContentBlock,
    TransformOp,
    WarningRecord,
)

TOP_BAND_RATIO = 0.10
BOTTOM_BAND_RATIO = 0.10
MIN_REPEAT_FRACTION = 0.55
PAGE_NUMBER_MAX_LEN = 6


@dataclass
class RunningMatterResult:
    blocks: list[ContentBlock]
    removed_block_ids: list[str]
    warnings: list[WarningRecord]


def _page_height(block: ContentBlock, default: float = 792.0) -> float:
    if block.provenance.bboxes:
        return max(b.y1 for b in block.provenance.bboxes) + 50.0
    return default


def _in_top_band(block: ContentBlock, page_h: float) -> bool:
    if not block.provenance.bboxes:
        return False
    y_mid = sum((b.y0 + b.y1) / 2 for b in block.provenance.bboxes) / len(
        block.provenance.bboxes
    )
    return y_mid >= page_h * (1.0 - TOP_BAND_RATIO)


def _in_bottom_band(block: ContentBlock, page_h: float) -> bool:
    if not block.provenance.bboxes:
        return False
    y_mid = sum((b.y0 + b.y1) / 2 for b in block.provenance.bboxes) / len(
        block.provenance.bboxes
    )
    return y_mid <= page_h * BOTTOM_BAND_RATIO


def _looks_like_page_number(text: str) -> bool:
    t = text.strip()
    if not t or len(t) > PAGE_NUMBER_MAX_LEN:
        return False
    return t.isdigit() or t in {"i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x"}


def remove_running_matter(
    blocks: list[ContentBlock],
    page_heights: dict[int, float],
    page_count: int,
) -> RunningMatterResult:
    if page_count < 2:
        return RunningMatterResult(blocks=blocks, removed_block_ids=[], warnings=[])

    line_blocks = [b for b in blocks if b.block_type == BlockType.LINE]
    text_counts: Counter[str] = Counter(b.current_text.strip() for b in line_blocks if b.current_text.strip())

    removed_ids: list[str] = []
    warnings: list[WarningRecord] = []
    kept: list[ContentBlock] = []

    for block in blocks:
        if block.block_type != BlockType.LINE:
            kept.append(block)
            continue
        text = block.current_text.strip()
        page_idx = block.provenance.page_indices[0] if block.provenance.page_indices else 0
        page_h = page_heights.get(page_idx, 792.0)
        repeat_count = text_counts.get(text, 0)
        repeat_fraction = repeat_count / max(page_count, 1)
        in_margin = _in_top_band(block, page_h) or _in_bottom_band(block, page_h)
        is_page_num = _looks_like_page_number(text)

        if is_page_num and in_margin:
            removed_ids.append(block.id)
            continue

        if repeat_fraction >= MIN_REPEAT_FRACTION and in_margin and len(text) >= 3:
            block.change_history.append(
                ChangeRecord(
                    op=TransformOp.REMOVE_RUNNING_MATTER,
                    reason="repeated_margin_line",
                    evidence={
                        "repeat_fraction": round(repeat_fraction, 3),
                        "text_sample": text[:80],
                    },
                    previous_text=block.current_text,
                )
            )
            removed_ids.append(block.id)
            continue

        if repeat_fraction >= MIN_REPEAT_FRACTION and not in_margin:
            warnings.append(
                WarningRecord(
                    code="running_matter_ambiguous",
                    message=(
                        f"Repeated line '{text[:40]}' is not clearly in margin; kept for review."
                    ),
                    block_id=block.id,
                    page_index=page_idx,
                )
            )
        kept.append(block)

    return RunningMatterResult(blocks=kept, removed_block_ids=removed_ids, warnings=warnings)
