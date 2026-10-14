"""Render PDF pages to RGB numpy arrays (OCR helper, optional pymupdf)."""

from __future__ import annotations

from pathlib import Path


def render_page_rgb(
    source_pdf: Path,
    page_index: int,
    scale: float = 2.0,
) -> tuple["object", float, float]:
    """Return (H×W×3 uint8 image, page_width_pt, page_height_pt)."""
    import numpy as np
    import pymupdf  # type: ignore[import-untyped]

    doc = pymupdf.open(str(source_pdf))
    try:
        page = doc.load_page(page_index)
        page_w = float(page.rect.width)
        page_h = float(page.rect.height)
        matrix = pymupdf.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        if pix.n == 4:
            img = img[:, :, :3].copy()
        elif pix.n == 1:
            img = np.stack([img[:, :, 0]] * 3, axis=-1)
        return img, page_w, page_h
    finally:
        doc.close()


def render_page_rgb_png(
    source_pdf: Path,
    page_index: int,
    dest_png: Path,
    scale: float = 2.0,
) -> tuple[float, float, int, int]:
    """Write page PNG; return (page_w_pt, page_h_pt, img_w, img_h)."""
    import pymupdf  # type: ignore[import-untyped]

    doc = pymupdf.open(str(source_pdf))
    try:
        page = doc.load_page(page_index)
        page_w = float(page.rect.width)
        page_h = float(page.rect.height)
        pix = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
        dest_png.parent.mkdir(parents=True, exist_ok=True)
        pix.save(str(dest_png))
        return page_w, page_h, int(pix.width), int(pix.height)
    finally:
        doc.close()
