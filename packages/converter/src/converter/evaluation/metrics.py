"""Strict, heuristic quality metrics for regression (not calibrated scores)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from converter.ir.models import BlockType, DocumentIR, WarningRecord

_STUCK_WORD = re.compile(
    r"[a-záéíóúñü]{3,}[A-ZÁÉÍÓÚÑ][a-záéíóúñü]{2,}"
)
_EMBEDDED_NEWLINE = re.compile(r"\n\s*\S")


@dataclass
class QualityMetrics:
    paragraph_count: int = 0
    title_count: int = 0
    orphan_line_count: int = 0
    warning_count: int = 0
    stuck_word_hits: int = 0
    embedded_newline_hits: int = 0
    running_matter_removed: int = 0
    issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "paragraph_count": self.paragraph_count,
            "title_count": self.title_count,
            "orphan_line_count": self.orphan_line_count,
            "warning_count": self.warning_count,
            "stuck_word_hits": self.stuck_word_hits,
            "embedded_newline_hits": self.embedded_newline_hits,
            "running_matter_removed": self.running_matter_removed,
            "issues": self.issues,
        }


def _count_pattern(text: str, pattern: re.Pattern[str]) -> int:
    return len(pattern.findall(text))


def evaluate_document_ir(document: DocumentIR) -> QualityMetrics:
    metrics = QualityMetrics(warning_count=len(document.warnings))
    editorial = document.engine_trace.get("editorial") or {}
    if isinstance(editorial, dict):
        metrics.running_matter_removed = int(editorial.get("running_matter_removed", 0))

    for block in document.blocks:
        if block.block_type == BlockType.PARAGRAPH:
            metrics.paragraph_count += 1
            text = block.current_text
            metrics.stuck_word_hits += _count_pattern(text, _STUCK_WORD)
            if _EMBEDDED_NEWLINE.search(text):
                metrics.embedded_newline_hits += 1
                metrics.issues.append(
                    f"paragraph {block.id} contains embedded newline"
                )
        elif block.block_type == BlockType.TITLE:
            metrics.title_count += 1
        elif block.block_type == BlockType.LINE:
            metrics.orphan_line_count += 1
            metrics.issues.append(f"unmerged line block {block.id}")

    for warning in document.warnings:
        if warning.code == "running_matter_ambiguous":
            metrics.issues.append(f"ambiguous running matter: {warning.message[:80]}")

    return metrics


def assert_no_regression(metrics: QualityMetrics, *, max_stuck: int = 0, max_newlines: int = 0) -> None:
    if metrics.stuck_word_hits > max_stuck:
        raise AssertionError(f"stuck_word_hits={metrics.stuck_word_hits} > {max_stuck}")
    if metrics.embedded_newline_hits > max_newlines:
        raise AssertionError(
            f"embedded_newline_hits={metrics.embedded_newline_hits} > {max_newlines}"
        )
