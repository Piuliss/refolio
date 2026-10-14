"""CLI entrypoint for local conversion."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from converter.pipeline import ConversionPipeline


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Convert PDF to EPUB via the engine IR.")
    parser.add_argument("pdf", type=Path, help="Source PDF path")
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        required=True,
        help="Directory for IR, EPUB, and quality report",
    )
    parser.add_argument("--language", default="es", help="Document language hint (default: es)")
    parser.add_argument("--max-pages", type=int, default=None, help="Limit pages processed")
    parser.add_argument(
        "--skip-epubcheck",
        action="store_true",
        help="Skip EPUBCheck (validation will not run)",
    )
    args = parser.parse_args(argv)

    if not args.pdf.is_file():
        print(f"Error: PDF not found: {args.pdf}", file=sys.stderr)
        return 1

    result = ConversionPipeline().run(
        source_pdf=args.pdf,
        output_dir=args.output_dir,
        language_hint=args.language,
        max_pages=args.max_pages,
        run_epubcheck_validation=not args.skip_epubcheck,
    )
    print(f"Wrote IR: {result.ir_path}")
    print(f"Wrote EPUB: {result.epub_path}")
    ev = result.quality_report.epub_validation
    if ev and ev.available:
        print(f"EPUBCheck passed: {ev.passed}")
    elif ev:
        print(f"EPUBCheck skipped: {ev.skipped_reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
