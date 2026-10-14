"""Tesseract OCR adapter (system binary — fast on macOS CPU)."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from converter.adapters.ocr_deps import format_missing_deps_message, missing_ocr_render_modules
from converter.adapters.ocr_engine import OcrLine, OcrPageResult
from converter.contracts import AdapterCapability, AdapterInfo


class TesseractOcrEngine:
    """Uses the local `tesseract` CLI; never invents text."""

    def __init__(self) -> None:
        self._scale = float(os.environ.get("CONVERTER_OCR_RENDER_SCALE", "2.0"))
        self._lang = os.environ.get("CONVERTER_TESSERACT_LANG", "eng")
        self._binary = os.environ.get("CONVERTER_TESSERACT_BIN", "tesseract")

    def info(self) -> AdapterInfo:
        return AdapterInfo(
            name="tesseract",
            version="cli",
            capabilities=(AdapterCapability.OCR,),
            license_spdx="Apache-2.0",
            limitations=(
                "Requires the tesseract system binary (e.g. brew install tesseract).",
                "Language packs must be installed separately (eng, spa, …).",
            ),
            runtime_requirements=("pymupdf", "numpy", "tesseract"),
        )

    def recognize_page(
        self,
        source_pdf: Path,
        page_index: int,
        language_hint: str | None = None,
    ) -> OcrPageResult:
        render_missing = missing_ocr_render_modules()
        if render_missing:
            return OcrPageResult(
                page_index=page_index,
                success=False,
                error_message=format_missing_deps_message(render_missing),
                provider=self.info().name,
            )
        binary = shutil.which(self._binary)
        if not binary:
            return OcrPageResult(
                page_index=page_index,
                success=False,
                error_message=(
                    f"tesseract binary not found ({self._binary!r}). "
                    "Install with Homebrew: brew install tesseract tesseract-lang"
                ),
                provider=self.info().name,
            )

        from converter.adapters.pdf_render import render_page_rgb_png

        lang = (language_hint or self._lang or "eng").split("-")[0].lower()
        if lang in {"es", "spa", "spanish"}:
            lang = "spa" if self._lang_available(binary, "spa") else "eng"

        try:
            with tempfile.TemporaryDirectory(prefix="refolio-tess-") as tmp:
                png_path = Path(tmp) / "page.png"
                page_w, page_h, img_w, img_h = render_page_rgb_png(
                    source_pdf, page_index, png_path, scale=self._scale
                )
                proc = subprocess.run(
                    [
                        binary,
                        str(png_path),
                        "stdout",
                        "-l",
                        lang,
                        "--psm",
                        "6",
                        "tsv",
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=120,
                )
        except subprocess.TimeoutExpired:
            return OcrPageResult(
                page_index=page_index,
                success=False,
                error_message="tesseract timed out after 120s",
                provider=self.info().name,
            )
        except Exception as exc:  # noqa: BLE001
            return OcrPageResult(
                page_index=page_index,
                success=False,
                error_message=f"tesseract failed: {type(exc).__name__}: {exc}",
                provider=self.info().name,
            )

        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "").strip()
            return OcrPageResult(
                page_index=page_index,
                success=False,
                error_message=f"tesseract exit {proc.returncode}: {err[:400]}",
                provider=self.info().name,
            )

        lines = _tsv_to_lines(proc.stdout, page_w, page_h, img_w, img_h)
        if not lines:
            return OcrPageResult(
                page_index=page_index,
                success=False,
                error_message="tesseract returned no text lines for this page.",
                provider=self.info().name,
            )
        return OcrPageResult(
            page_index=page_index,
            success=True,
            lines=tuple(lines),
            provider=self.info().name,
        )

    @staticmethod
    def _lang_available(binary: str, lang: str) -> bool:
        try:
            proc = subprocess.run(
                [binary, "--list-langs"],
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False
        out = (proc.stdout or "") + (proc.stderr or "")
        return any(line.strip() == lang for line in out.splitlines())


def _tsv_to_lines(
    tsv: str,
    page_w: float,
    page_h: float,
    img_w: int,
    img_h: int,
) -> list[OcrLine]:
    """Group TSV word rows into line-level boxes (PDF bottom-left coords)."""
    scale_x = page_w / float(img_w)
    scale_y = page_h / float(img_h)
    by_line: dict[tuple[int, int, int], list[tuple[str, float, float, float, float, float]]] = {}
    rows = tsv.splitlines()
    if not rows:
        return []
    header = rows[0].split("\t")
    col = {name: i for i, name in enumerate(header)}
    required = ("level", "page_num", "block_num", "line_num", "left", "top", "width", "height", "conf", "text")
    if any(k not in col for k in required):
        return []

    for row in rows[1:]:
        parts = row.split("\t")
        if len(parts) <= col["text"]:
            continue
        try:
            level = int(parts[col["level"]])
        except ValueError:
            continue
        if level != 5:  # word
            continue
        text = parts[col["text"]].strip()
        if not text:
            continue
        try:
            left = float(parts[col["left"]])
            top = float(parts[col["top"]])
            width = float(parts[col["width"]])
            height = float(parts[col["height"]])
            conf = float(parts[col["conf"]])
            key = (
                int(parts[col["page_num"]]),
                int(parts[col["block_num"]]),
                int(parts[col["line_num"]]),
            )
        except ValueError:
            continue
        by_line.setdefault(key, []).append((text, left, top, width, height, conf))

    ocr_lines: list[OcrLine] = []
    for key in sorted(by_line):
        words = by_line[key]
        words.sort(key=lambda w: w[1])
        text = " ".join(w[0] for w in words)
        left = min(w[1] for w in words)
        top = min(w[2] for w in words)
        right = max(w[1] + w[3] for w in words)
        bottom = max(w[2] + w[4] for w in words)
        confs = [w[5] for w in words if w[5] >= 0]
        avg_conf = (sum(confs) / len(confs) / 100.0) if confs else None
        x0 = left * scale_x
        x1 = right * scale_x
        y0 = page_h - bottom * scale_y
        y1 = page_h - top * scale_y
        ocr_lines.append(
            OcrLine(text=text, x0=x0, y0=y0, x1=x1, y1=y1, confidence=avg_conf)
        )
    ocr_lines.sort(key=lambda ln: (-(ln.y0 + ln.y1) / 2.0, ln.x0))
    return ocr_lines
