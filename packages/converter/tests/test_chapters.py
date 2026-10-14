from __future__ import annotations

from converter.editorial.chapters import detect_chapters
from converter.ir.models import BlockType, ContentBlock, ExtractionMethod, Provenance


def _para(text: str) -> ContentBlock:
    return ContentBlock(
        id="p1",
        block_type=BlockType.PARAGRAPH,
        reading_order=0,
        original_text=text,
        current_text=text,
        provenance=Provenance(
            extraction_method=ExtractionMethod.NATIVE_PDF,
            provider="test",
        ),
    )


def test_chapter_pattern_promoted() -> None:
    blocks, warnings = detect_chapters([_para("Capítulo 3 La planificación")])
    assert blocks[0].block_type == BlockType.TITLE
    assert blocks[0].title_level == 1
    assert not warnings


def test_large_text_not_auto_chapter() -> None:
    blocks, warnings = detect_chapters([_para("IV")])
    assert blocks[0].block_type == BlockType.PARAGRAPH
    assert any(w.code == "chapter_ambiguous" for w in warnings)
