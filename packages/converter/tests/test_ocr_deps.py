from __future__ import annotations

from pathlib import Path

from converter.adapters.ocr_deps import (
    default_converter_package_dir,
    format_missing_deps_message,
    pip_install_notebook_ocr,
    pip_install_ocr_extra,
    pip_install_render_quick,
)


def test_pip_install_ocr_extra_uses_absolute_package_path() -> None:
    pkg = default_converter_package_dir()
    line = pip_install_ocr_extra(pkg)
    assert str(pkg) in line
    assert "[ocr]" in line
    assert line.startswith("python") or " -m pip install" in line


def test_pip_install_notebook_ocr_includes_extras() -> None:
    line = pip_install_notebook_ocr()
    assert "[dev,notebook,ocr]" in line


def test_format_missing_deps_message_render_quick() -> None:
    msg = format_missing_deps_message(["numpy"], for_notebook=True)
    assert "numpy" in msg
    assert pip_install_render_quick() in msg
    assert pip_install_notebook_ocr() in msg


def test_format_missing_deps_message_paddle_only() -> None:
    msg = format_missing_deps_message(["paddleocr", "paddle"])
    assert "Full OCR stack:" in msg
    assert pip_install_ocr_extra() in msg
    assert pip_install_render_quick() not in msg


def test_default_converter_package_dir_exists() -> None:
    pkg = default_converter_package_dir()
    assert pkg.is_dir()
    assert (pkg / "pyproject.toml").is_file()
