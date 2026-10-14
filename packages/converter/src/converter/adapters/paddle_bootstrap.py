"""Paddle runtime setup for local CPU OCR (macOS / Linux)."""

from __future__ import annotations

import os
import sys

_CONFIGURED = False

# Paddle 3.x on Apple Silicon can fail text recognition with Place(undefined) during matmul.
_ALLOCATOR_HINT = (
    "On macOS (Apple Silicon) use Python 3.12 with paddlepaddle==2.6.2 in the project venv; "
    "paddlepaddle 3.x often breaks PaddleOCR recognition. "
    f"Reinstall: {sys.executable} -m pip install 'paddlepaddle==2.6.2'"
)


def configure_paddle_runtime() -> None:
    """Set CPU-only flags before Paddle loads inference models."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
    os.environ.setdefault("FLAGS_use_mkldnn", "0")
    os.environ.setdefault("FLAGS_allocator_strategy", "auto_growth")
    # Avoid OpenMP oversubscription that can stall inference for tens of minutes on macOS.
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    os.environ.setdefault("FLAGS_num_threads", "1")
    import paddle  # type: ignore[import-untyped]

    paddle.set_device("cpu")
    try:
        paddle.set_flags({"FLAGS_enable_pir_api": False})
    except Exception:  # noqa: BLE001 — older paddle builds
        pass
    _CONFIGURED = True


def format_paddle_runtime_error(exc: BaseException) -> str | None:
    """Return an operator hint when the failure matches a known broken stack."""
    msg = str(exc)
    if "No allocator found for the place" in msg or "Place(undefined" in msg:
        return _ALLOCATOR_HINT
    return None
