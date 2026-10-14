"""Initial content-quality heuristics (not calibrated scores)."""

from __future__ import annotations

from dataclasses import dataclass, field

from converter.contracts import ValidationResult
from converter.ir.models import DocumentIR


@dataclass
class QualityReport:
    schema_version: str = "0.1.0"
    block_count: int = 0
    page_count: int = 0
    warning_count: int = 0
    empty_block_count: int = 0
    epub_validation: ValidationResult | None = None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        ev = None
        if self.epub_validation:
            ev = {
                "tool": self.epub_validation.tool,
                "available": self.epub_validation.available,
                "passed": self.epub_validation.passed,
                "skipped_reason": self.epub_validation.skipped_reason,
                "message_count": len(self.epub_validation.messages),
            }
        return {
            "schema_version": self.schema_version,
            "block_count": self.block_count,
            "page_count": self.page_count,
            "warning_count": self.warning_count,
            "empty_block_count": self.empty_block_count,
            "epub_validation": ev,
            "notes": self.notes,
        }


def build_quality_report(
    document: DocumentIR,
    epub_validation: ValidationResult | None = None,
) -> QualityReport:
    empty = sum(1 for b in document.blocks if not b.current_text.strip())
    notes: list[str] = []
    if document.warnings:
        notes.append("IR contains parser warnings; review before publishing.")
    if empty:
        notes.append(f"{empty} block(s) have empty text.")
    if not document.blocks:
        notes.append("No content blocks — EPUB will be a placeholder chapter.")

    return QualityReport(
        block_count=len(document.blocks),
        page_count=len(document.pages),
        warning_count=len(document.warnings),
        empty_block_count=empty,
        epub_validation=epub_validation,
        notes=notes,
    )
