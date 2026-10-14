"""End-to-end conversion pipeline (engine core)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from converter.adapters.factory import get_parser
from converter.contracts import DocumentParser, ParseContext
from converter.epub.writer import write_epub
from converter.ir.models import DocumentIR
from converter.ir.schema import validate_ir_document
from converter.quality.report import QualityReport, build_quality_report
from converter.validation.epubcheck import run_epubcheck
from converter.version import ENGINE_VERSION


@dataclass
class ConversionResult:
    document_ir: DocumentIR
    epub_path: Path
    ir_path: Path
    quality_report: QualityReport
    engine_version: str = ENGINE_VERSION


class ConversionPipeline:
    def __init__(self, parser: DocumentParser | None = None) -> None:
        self._parser = parser or get_parser()

    def run(
        self,
        source_pdf: Path,
        output_dir: Path,
        language_hint: str | None = None,
        max_pages: int | None = None,
        run_epubcheck_validation: bool = True,
    ) -> ConversionResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        ctx = ParseContext(
            source_path=source_pdf,
            language_hint=language_hint,
            max_pages=max_pages,
        )
        document = self._parser.parse(ctx)
        ir_path = output_dir / "document.ir.json"
        ir_data = document.model_dump(mode="json")
        validate_ir_document(ir_data)
        ir_path.write_text(
            json.dumps(ir_data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        epub_path = output_dir / "output.epub"
        write_epub(document, epub_path)

        validation = run_epubcheck(epub_path) if run_epubcheck_validation else None
        report = build_quality_report(document, validation)
        (output_dir / "quality_report.json").write_text(
            json.dumps(report.to_dict(), indent=2) + "\n",
            encoding="utf-8",
        )
        return ConversionResult(
            document_ir=document,
            epub_path=epub_path,
            ir_path=ir_path,
            quality_report=report,
        )
