"""Engine adapter contracts (no Django)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Protocol, runtime_checkable

from converter.ir.models import DocumentIR


class AdapterCapability(StrEnum):
    NATIVE_TEXT = "native_text"
    LAYOUT_BLOCKS = "layout_blocks"
    READING_ORDER = "reading_order"
    TABLES = "tables"
    IMAGES = "images"
    OCR = "ocr"


@dataclass(frozen=True)
class AdapterInfo:
    name: str
    version: str
    capabilities: tuple[AdapterCapability, ...]
    license_spdx: str
    limitations: tuple[str, ...] = ()
    runtime_requirements: tuple[str, ...] = ()


@dataclass
class ParseContext:
    source_path: Path
    language_hint: str | None = None
    max_pages: int | None = None


@runtime_checkable
class DocumentParser(Protocol):
    """Extracts structured content from a PDF into the canonical IR."""

    def info(self) -> AdapterInfo: ...

    def parse(self, ctx: ParseContext) -> DocumentIR: ...  # noqa: F821


@runtime_checkable
class EpubWriter(Protocol):
    def write(self, document: DocumentIR, output_path: Path) -> None: ...  # noqa: F821


@runtime_checkable
class TechnicalValidator(Protocol):
    def validate(self, epub_path: Path) -> ValidationResult: ...  # noqa: F821


@dataclass
class ValidationMessage:
    severity: str
    message: str
    location: str | None = None


@dataclass
class ValidationResult:
    tool: str
    tool_version: str | None
    available: bool
    passed: bool | None
    messages: list[ValidationMessage] = field(default_factory=list)
    skipped_reason: str | None = None
