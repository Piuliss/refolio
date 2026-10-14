from __future__ import annotations

from converter.editorial.paragraphs import reconstruct_paragraphs
from converter.ir.models import BlockType, ContentBlock, ExtractionMethod, Provenance


def _line(block_id: str, text: str, order: int, page: int = 0) -> ContentBlock:
    return ContentBlock(
        id=block_id,
        block_type=BlockType.LINE,
        reading_order=order,
        original_text=text,
        current_text=text,
        provenance=Provenance(
            page_indices=[page],
            extraction_method=ExtractionMethod.NATIVE_PDF,
            provider="test",
        ),
    )


def test_join_hyphenated_lines() -> None:
    blocks = [
        _line("a", "interesante-", 0),
        _line("b", "continuación", 1),
    ]
    out = reconstruct_paragraphs(blocks)
    assert len(out) == 1
    assert out[0].block_type == BlockType.PARAGRAPH
    assert "interesantecontinuación" in out[0].current_text.replace(" ", "")


def test_no_join_after_sentence_end() -> None:
    blocks = [
        _line("a", "Fin de frase.", 0),
        _line("b", "otra oración", 1),
    ]
    out = reconstruct_paragraphs(blocks)
    assert len(out) == 2


def test_join_lowercase_continuation() -> None:
    blocks = [
        _line("a", "Primera parte sin punto", 0),
        _line("b", "segunda parte", 1),
    ]
    out = reconstruct_paragraphs(blocks)
    assert len(out) == 1
    assert "Primera parte" in out[0].current_text
