from __future__ import annotations

from pathlib import Path

from converter.validation.epubcheck import run_epubcheck


def test_epubcheck_unavailable_is_explicit(tmp_path: Path) -> None:
    fake = tmp_path / "x.epub"
    fake.write_bytes(b"not epub")
    result = run_epubcheck(fake)
    if not result.available:
        assert result.passed is None
        assert result.skipped_reason
