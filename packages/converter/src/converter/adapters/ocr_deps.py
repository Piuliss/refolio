"""Runtime dependency checks for the optional OCR path."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_RENDER_MODULES: tuple[tuple[str, str], ...] = (
    ("numpy", "numpy"),
    ("pymupdf", "pymupdf"),
)

_PADDLE_MODULES: tuple[tuple[str, str], ...] = (
    ("paddleocr", "paddleocr"),
    ("paddle", "paddle"),
)


def default_converter_package_dir() -> Path:
    """Absolute path to packages/converter (editable install target)."""
    return Path(__file__).resolve().parents[3]


def pip_install_render_quick() -> str:
    return (
        f'{sys.executable} -m pip install "numpy>=1.26,<2" "pymupdf>=1.25.5,<2"'
    )


def pip_install_ocr_extra(converter_dir: Path | None = None) -> str:
    pkg = (converter_dir or default_converter_package_dir()).resolve()
    return f'{sys.executable} -m pip install -e "{pkg}[ocr]"'


def pip_install_notebook_ocr(converter_dir: Path | None = None) -> str:
    pkg = (converter_dir or default_converter_package_dir()).resolve()
    return f'{sys.executable} -m pip install -e "{pkg}[dev,notebook,ocr]"'


def missing_modules(modules: tuple[tuple[str, str], ...]) -> list[str]:
    missing: list[str] = []
    for label, import_name in modules:
        try:
            __import__(import_name)
        except ImportError:
            missing.append(label)
    return missing


def missing_ocr_render_modules() -> list[str]:
    return missing_modules(_RENDER_MODULES)


def missing_paddle_modules() -> list[str]:
    return missing_modules(_PADDLE_MODULES)


def format_missing_deps_message(
    missing: list[str],
    *,
    for_notebook: bool = False,
    converter_dir: Path | None = None,
) -> str:
    names = ", ".join(missing)
    use_notebook_line = for_notebook or bool(os.environ.get("JPY_PARENT_PID"))
    full_cmd = (
        pip_install_notebook_ocr(converter_dir)
        if use_notebook_line
        else pip_install_ocr_extra(converter_dir)
    )
    render_only = set(missing) <= {"numpy", "pymupdf"}
    parts = [f"OCR dependencies missing ({names})."]
    if render_only:
        parts.append(f"Quick (page render only): {pip_install_render_quick()}")
    parts.append(f"Full OCR stack: {full_cmd}")
    return " ".join(parts)
