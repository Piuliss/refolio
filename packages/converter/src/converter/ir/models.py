"""Canonical intermediate representation (versioned, validated)."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

IR_SCHEMA_VERSION = "0.1.0"


class BlockType(StrEnum):
    TITLE = "title"
    PARAGRAPH = "paragraph"
    LIST_ITEM = "list_item"
    QUOTE = "quote"
    IMAGE = "image"
    TABLE = "table"
    PAGE_BREAK = "page_break"
    UNKNOWN = "unknown"


class ExtractionMethod(StrEnum):
    NATIVE_PDF = "native_pdf"
    DOCLING = "docling"
    OCR = "ocr"
    HYBRID = "hybrid"


class ReviewStatus(StrEnum):
    UNREVIEWED = "unreviewed"
    ACCEPTED = "accepted"
    FLAGGED = "flagged"
    REJECTED = "rejected"


class BoundingBox(BaseModel):
    """PDF-style coordinates: origin bottom-left, units in points."""

    x0: float
    y0: float
    x1: float
    y1: float
    page_index: int = Field(ge=0)


class Provenance(BaseModel):
    page_indices: list[int] = Field(default_factory=list)
    bboxes: list[BoundingBox] = Field(default_factory=list)
    extraction_method: ExtractionMethod
    provider: str
    provider_confidence: float | None = None


class WarningRecord(BaseModel):
    code: str
    message: str
    block_id: str | None = None
    page_index: int | None = None


class ContentBlock(BaseModel):
    id: str
    block_type: BlockType
    reading_order: int = Field(ge=0)
    original_text: str
    current_text: str
    title_level: int | None = Field(default=None, ge=1, le=6)
    provenance: Provenance
    review_status: ReviewStatus = ReviewStatus.UNREVIEWED
    relationships: dict[str, list[str]] = Field(default_factory=dict)


class PageRecord(BaseModel):
    index: int = Field(ge=0)
    width_pt: float | None = None
    height_pt: float | None = None
    label: str | None = None


class DocumentMetadata(BaseModel):
    title: str | None = None
    language: str = "es"
    source_filename: str | None = None


class DocumentIR(BaseModel):
    schema_version: str = IR_SCHEMA_VERSION
    metadata: DocumentMetadata
    pages: list[PageRecord] = Field(default_factory=list)
    blocks: list[ContentBlock] = Field(default_factory=list)
    warnings: list[WarningRecord] = Field(default_factory=list)
    engine_trace: dict[str, Any] = Field(default_factory=dict)

    def sorted_blocks(self) -> list[ContentBlock]:
        return sorted(self.blocks, key=lambda b: b.reading_order)
