"""Reflowable EPUB writer from DocumentIR."""

from __future__ import annotations

import html
from pathlib import Path

from ebooklib import epub  # type: ignore[import-untyped]

from converter.ir.models import BlockType, ContentBlock, DocumentIR


def _block_to_html(block: ContentBlock) -> str:
    text = html.escape(block.current_text)
    if block.block_type == BlockType.TITLE:
        level = block.title_level or 1
        level = max(1, min(6, level))
        return f"<h{level}>{text}</h{level}>"
    if block.block_type == BlockType.LIST_ITEM:
        return f"<li>{text}</li>"
    if block.block_type == BlockType.QUOTE:
        return f"<blockquote><p>{text}</p></blockquote>"
    return f"<p>{text}</p>"


def write_epub(document: DocumentIR, output_path: Path) -> None:
    book = epub.EpubBook()
    title = document.metadata.title or "Converted document"
    book.set_identifier(f"pdf-epub:{title}")
    book.set_title(title)
    book.set_language(document.metadata.language)

    css = epub.EpubItem(
        uid="style",
        file_name="style/default.css",
        media_type="text/css",
        content=(
            b"body { font-family: serif; line-height: 1.5; margin: 1em; }\n"
            b"h1, h2, h3 { margin-top: 1.2em; }\n"
            b"blockquote { margin-left: 1em; font-style: italic; }\n"
        ),
    )
    book.add_item(css)

    chapters: list[epub.EpubHtml] = []
    spine_blocks = document.sorted_blocks()
    if not spine_blocks:
        lang = document.metadata.language
        ch = epub.EpubHtml(title="Empty", file_name="chap_001.xhtml", lang=lang)
        ch.content = "<p>No content blocks were extracted.</p>"
        ch.add_item(css)
        book.add_item(ch)
        chapters.append(ch)
    else:
        chunk: list[ContentBlock] = []
        chunk_idx = 0

        def flush_chunk() -> None:
            nonlocal chunk_idx, chunk
            if not chunk:
                return
            chunk_idx += 1
            fname = f"chap_{chunk_idx:03d}.xhtml"
            ch = epub.EpubHtml(
                title=f"Section {chunk_idx}",
                file_name=fname,
                lang=document.metadata.language,
            )
            body = "\n".join(_block_to_html(b) for b in chunk)
            ch.content = (
                "<html><head><link rel='stylesheet' href='style/default.css'/>"
                f"</head><body>{body}</body></html>"
            )
            ch.add_item(css)
            book.add_item(ch)
            chapters.append(ch)
            chunk = []

        for block in spine_blocks:
            if block.block_type == BlockType.TITLE and chunk:
                flush_chunk()
            chunk.append(block)
        flush_chunk()

    book.toc = tuple(chapters)
    book.spine = ["nav"] + chapters
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    output_path.parent.mkdir(parents=True, exist_ok=True)
    epub.write_epub(str(output_path), book)
