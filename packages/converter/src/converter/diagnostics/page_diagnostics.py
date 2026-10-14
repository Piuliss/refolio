"""Per-page text diagnostics and native/OCR routing heuristics."""

from __future__ import annotations

import re

from converter.ir.models import PageDiagnostic, PageRoute

_ALNUM = re.compile(r"[0-9A-Za-zÀ-ÿ]", re.UNICODE)

# Heuristic thresholds (documented signals, not calibrated probabilities).
MIN_CHARS_NATIVE = 24
MIN_ALNUM_RATIO = 0.35


def _alnum_ratio(text: str) -> float:
    if not text:
        return 0.0
    alnum = len(_ALNUM.findall(text))
    return alnum / max(len(text), 1)


def diagnose_page(page_index: int, page_text: str) -> PageDiagnostic:
    char_count = len(page_text.strip())
    ratio = _alnum_ratio(page_text)
    signals: dict[str, float | int | bool] = {
        "min_chars_native": MIN_CHARS_NATIVE,
        "min_alnum_ratio": MIN_ALNUM_RATIO,
    }
    route = PageRoute.NATIVE
    if char_count < MIN_CHARS_NATIVE or ratio < MIN_ALNUM_RATIO:
        route = PageRoute.OCR_RECOMMENDED
        signals["low_text"] = char_count < MIN_CHARS_NATIVE
        signals["low_alnum_ratio"] = ratio < MIN_ALNUM_RATIO
    return PageDiagnostic(
        page_index=page_index,
        char_count=char_count,
        alnum_ratio=round(ratio, 4),
        route=route,
        signals=signals,
    )


def page_text_from_lines(lines: list[str]) -> str:
    return "\n".join(lines)
