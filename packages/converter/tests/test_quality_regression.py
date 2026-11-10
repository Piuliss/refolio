from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from converter.evaluation.metrics import assert_no_regression, evaluate_document_ir
from converter.ir.models import BlockType
from converter.pipeline import ConversionPipeline


def _two_page_book_pdf(path: Path) -> None:
    c = canvas.Canvas(str(path), pagesize=letter)
    for page in range(2):
        c.setFont("Helvetica", 9)
        c.drawString(72, 750, "SYNTHETIC BOOK HEADER")
        c.setFont("Helvetica", 12)
        if page == 0:
            c.drawString(72, 700, "Capítulo 1")
            c.drawString(72, 680, "Primer párrafo que continúa")
            c.drawString(72, 665, "en otra línea sin punto final")
        else:
            c.drawString(72, 700, "Segundo párrafo completo.")
        c.showPage()
    c.save()


def test_synthetic_book_quality(tmp_path: Path) -> None:
    pdf = tmp_path / "book.pdf"
    _two_page_book_pdf(pdf)
    result = ConversionPipeline().run(
        pdf,
        tmp_path / "out",
        language_hint="es",
        run_epubcheck_validation=False,
    )
    doc = result.document_ir
    metrics = evaluate_document_ir(doc)
    assert_no_regression(metrics)
    assert metrics.running_matter_removed >= 2
    assert metrics.title_count >= 1
    assert metrics.orphan_line_count == 0
    assert metrics.paragraph_count >= 2
    texts = [b.current_text for b in doc.sorted_blocks() if b.block_type == BlockType.PARAGRAPH]
    assert any("Primer párrafo" in t and "otra línea" in t for t in texts)
    assert not any("SYNTHETIC BOOK HEADER" in t for t in texts)


def test_multi_span_line_becomes_single_paragraph(tmp_path: Path) -> None:
    pdf = tmp_path / "words.pdf"
    c = canvas.Canvas(str(pdf), pagesize=letter)
    c.drawString(72, 700, "Hola ")
    c.drawString(100, 700, "mundo ")
    c.drawString(140, 700, "bonito")
    c.save()
    result = ConversionPipeline().run(
        pdf, tmp_path / "out", run_epubcheck_validation=False
    )
    metrics = evaluate_document_ir(result.document_ir)
    assert_no_regression(metrics)
    para = next(
        b for b in result.document_ir.blocks if b.block_type == BlockType.PARAGRAPH
    )
    assert "Hola mundo bonito" in para.current_text.replace("  ", " ")
