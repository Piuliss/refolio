from __future__ import annotations

from pathlib import Path

from converter.pipeline import ConversionPipeline


def test_native_pdf_pipeline(sample_pdf: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    result = ConversionPipeline().run(
        source_pdf=sample_pdf,
        output_dir=out,
        language_hint="es",
        run_epubcheck_validation=False,
    )
    assert result.epub_path.is_file()
    assert result.ir_path.is_file()
    assert len(result.document_ir.blocks) >= 2
    assert result.document_ir.metadata.language == "es"
