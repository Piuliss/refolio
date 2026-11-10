"""Paddle runtime setup for OCR on CPU (macOS) or GPU (Linux + CUDA)."""

from __future__ import annotations

import contextlib
import os
import sys

_CONFIGURED = False

# Paddle 3.x on Apple Silicon can fail text recognition with Place(undefined) during matmul.
_ALLOCATOR_HINT = (
    "On macOS (Apple Silicon) use Python 3.12 with paddlepaddle==2.6.2 in the project venv; "
    "paddlepaddle 3.x often breaks PaddleOCR recognition. "
    f"Reinstall: {sys.executable} -m pip install 'paddlepaddle==2.6.2'"
)


def _force_cpu() -> bool:
    return os.environ.get("CONVERTER_PADDLE_FORCE_CPU", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def _cuda_available() -> bool:
    import paddle

    if not paddle.is_compiled_with_cuda():
        return False
    try:
        return int(paddle.device.cuda.device_count()) > 0
    except Exception:  # noqa: BLE001
        return False


def configure_paddle_runtime() -> None:
    """Configure Paddle for GPU when CUDA is present; otherwise CPU-only."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    os.environ.setdefault("FLAGS_allocator_strategy", "auto_growth")
    import paddle

    if not _force_cpu() and _cuda_available():
        paddle.set_device("gpu:0")
    else:
        os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
        os.environ.setdefault("FLAGS_use_mkldnn", "0")
        # Avoid OpenMP oversubscription that can stall inference for tens of minutes on macOS.
        os.environ.setdefault("OMP_NUM_THREADS", "1")
        os.environ.setdefault("MKL_NUM_THREADS", "1")
        os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
        os.environ.setdefault("FLAGS_num_threads", "1")
        paddle.set_device("cpu")
    # Older paddle builds may not expose this flag.
    with contextlib.suppress(Exception):
        paddle.set_flags({"FLAGS_enable_pir_api": False})
    _CONFIGURED = True


def format_paddle_runtime_error(exc: BaseException) -> str | None:
    """Return an operator hint when the failure matches a known broken stack."""
    msg = str(exc)
    if "No allocator found for the place" in msg or "Place(undefined" in msg:
        return _ALLOCATOR_HINT
    return None
