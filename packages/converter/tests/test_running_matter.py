from __future__ import annotations

from converter.editorial.running_matter import remove_running_matter
from converter.ir.models import BlockType, BoundingBox, ContentBlock, ExtractionMethod, Provenance


def _margin_line(
    block_id: str,
    text: str,
    page: int,
    y_mid: float,
    page_h: float = 800.0,
) -> ContentBlock:
    half = 8.0
    return ContentBlock(
        id=block_id,
        block_type=BlockType.LINE,
        reading_order=page,
        original_text=text,
        current_text=text,
        provenance=Provenance(
            page_indices=[page],
            bboxes=[
                BoundingBox(
                    x0=50.0,
                    y0=y_mid - half,
                    x1=200.0,
                    y1=y_mid + half,
                    page_index=page,
                )
            ],
            extraction_method=ExtractionMethod.NATIVE_PDF,
            provider="test",
        ),
    )


def test_repeated_header_removed() -> None:
    blocks = [
        _margin_line("h0", "EDITORIAL HEADER", 0, y_mid=780.0),
        _margin_line("h1", "EDITORIAL HEADER", 1, y_mid=780.0),
        _margin_line("b0", "Body text on page one.", 0, y_mid=400.0),
        _margin_line("b1", "Body text on page two.", 1, y_mid=400.0),
    ]
    result = remove_running_matter(blocks, {0: 800.0, 1: 800.0}, page_count=2)
    texts = [b.current_text for b in result.blocks]
    assert "EDITORIAL HEADER" not in texts
    assert any("Body text" in t for t in texts)


def test_unique_top_line_not_removed() -> None:
    blocks = [
        _margin_line("u0", "Unique title page", 0, y_mid=780.0),
        _margin_line("b0", "Content", 0, y_mid=400.0),
    ]
    result = remove_running_matter(blocks, {0: 800.0}, page_count=1)
    assert len(result.blocks) == 2
