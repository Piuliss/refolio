"""Notebook-only viewers (local dev). Not part of the production engine wheel."""

from __future__ import annotations

import html
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import bleach
from IPython.display import HTML, Image, display

# Strip active content; allow basic reflowable EPUB structure for preview.
_BLEACH_TAGS = frozenset(
    {
        "p",
        "div",
        "span",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "ul",
        "ol",
        "li",
        "blockquote",
        "br",
        "em",
        "strong",
        "a",
        "img",
        "table",
        "thead",
        "tbody",
        "tr",
        "th",
        "td",
    }
)
_BLEACH_ATTRS = {
    "*": ["class", "id", "lang", "dir"],
    "a": ["href", "title"],
    "img": ["src", "alt", "width", "height"],
}


def sanitize_document_html(fragment: str) -> str:
    return bleach.clean(
        fragment,
        tags=_BLEACH_TAGS,
        attributes=_BLEACH_ATTRS,
        strip=True,
    )


def render_pdf_pages(
    pdf_path: Path,
    output_dir: Path,
    *,
    page_indices: list[int] | None = None,
    dpi: int = 120,
    prefix: str = "page",
) -> list[Path]:
    """Render PDF pages to PNG files (requires PyMuPDF)."""
    import pymupdf  # type: ignore[import-untyped]

    output_dir.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open(pdf_path)
    indices = page_indices if page_indices is not None else list(range(doc.page_count))
    paths: list[Path] = []
    zoom = dpi / 72.0
    matrix = pymupdf.Matrix(zoom, zoom)
    for idx in indices:
        if idx < 0 or idx >= doc.page_count:
            continue
        page = doc.load_page(idx)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        out = output_dir / f"{prefix}_{idx:03d}.png"
        pix.save(str(out))
        paths.append(out)
    doc.close()
    return paths


def show_images(paths: list[Path], *, max_width: int = 640) -> None:
    for path in paths:
        if not path.is_file():
            print(f"Missing image: {path}")
            continue
        suffix = path.suffix.lower()
        if suffix not in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
            print(f"Skip non-image: {path}")
            continue
        display(Image(filename=str(path), width=max_width))


def _xhtml_body_text(xhtml_bytes: bytes) -> str:
    try:
        root = ET.fromstring(xhtml_bytes)
    except ET.ParseError:
        return sanitize_document_html(xhtml_bytes.decode("utf-8", errors="replace"))
    ns = {"x": "http://www.w3.org/1999/xhtml"}
    body = root.find(".//x:body", ns)
    if body is None:
        body = root.find(".//body")
    if body is None:
        return sanitize_document_html(xhtml_bytes.decode("utf-8", errors="replace"))
    inner = ET.tostring(body, encoding="unicode", method="html")
    return sanitize_document_html(inner)


def preview_epub_chapters(
    epub_path: Path,
    *,
    max_chapters: int = 5,
    iframe_height: int = 420,
) -> None:
    """Display sanitized HTML from real EPUB chapter files (local artifact only)."""
    if not epub_path.is_file():
        raise FileNotFoundError(f"EPUB not found: {epub_path}")

    with zipfile.ZipFile(epub_path, "r") as zf:
        names = sorted(n for n in zf.namelist() if n.lower().endswith((".xhtml", ".html")))
        if not names:
            print("No HTML chapters found inside EPUB.")
            return
        for name in names[:max_chapters]:
            raw = zf.read(name)
            safe_body = _xhtml_body_text(raw)
            title = html.escape(name)
            wrapped = (
                f"<h3 style='font-family:sans-serif'>{title}</h3>"
                f"<div style='border:1px solid #ccc;padding:8px;"
                f"max-height:{iframe_height}px;overflow:auto;background:#fafafa'>"
                f"{safe_body}</div>"
            )
            display(HTML(wrapped))


def _png_data_uri(path: Path) -> str:
    import base64

    payload = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{payload}"


def epub_text_stats(epub_path: Path) -> dict[str, int]:
    """Structural stats only (no text samples)."""
    import re

    if not epub_path.is_file():
        raise FileNotFoundError(epub_path)
    with zipfile.ZipFile(epub_path, "r") as zf:
        html_files = [n for n in zf.namelist() if n.lower().endswith((".xhtml", ".html"))]
        chars = 0
        for name in html_files:
            raw = zf.read(name).decode("utf-8", errors="replace")
            chars += len(re.sub(r"<[^>]+>", " ", raw))
        return {
            "html_files": len(html_files),
            "approx_text_chars": chars,
            "zip_bytes": epub_path.stat().st_size,
        }


def compare_epub_pair(baseline: Path, candidate: Path) -> dict[str, object]:
    """Compare two EPUB artifacts (metrics only)."""
    base = epub_text_stats(baseline)
    cand = epub_text_stats(candidate)
    ratio = cand["approx_text_chars"] / max(base["approx_text_chars"], 1)
    return {
        "baseline": base,
        "refolio": cand,
        "text_char_ratio": round(ratio, 4),
        "html_file_ratio": round(
            cand["html_files"] / max(base["html_files"], 1), 4
        ),
    }


def side_by_side_png(left: Path, right: Path, *, width: int = 480) -> None:
    """Compare two page renders (e.g. source PDF vs debug export)."""
    display(
        HTML(
            "<div style='display:flex;gap:12px;flex-wrap:wrap'>"
            f"<div><p>Left: {html.escape(left.name)}</p>"
            f"<img src='{_png_data_uri(left)}' width='{width}'/></div>"
            f"<div><p>Right: {html.escape(right.name)}</p>"
            f"<img src='{_png_data_uri(right)}' width='{width}'/></div>"
            "</div>"
        )
    )
