# Research notes — engines and validation (Phase 0)

Status key: **integrated** = adapter in repo; **evaluated** = documented only; **pending** = not verified in this environment.

| Component | Paper / source | License (verify before ship) | Use in platform | Limitations | Status |
|-----------|----------------|------------------------------|-----------------|-------------|--------|
| **Docling** | [arXiv:2408.09869](https://arxiv.org/abs/2408.09869), [docs](https://docling-project.github.io/docling/) | MIT (project repo) | Primary structured `DocumentParser` when installed (`CONVERTER_PARSER=docling`) | Heavy deps; model download; OCR not default in P1 | **integrated** (optional extra) |
| **PaddleOCR 3.0** | [arXiv:2507.05595](https://arxiv.org/abs/2507.05595), [GitHub](https://github.com/PaddlePaddle/PaddleOCR) | Apache-2.0 (verify per release) | Future alternate OCR/layout baseline behind `OcrEngine` / parser | GPU/CPU footprint; not loaded in P1 | **evaluated** |
| **olmOCR 2** | [arXiv:2510.19817](https://arxiv.org/abs/2510.19817), [GitHub](https://github.com/allenai/olmocr) | Apache-2.0 (verify) | Inspiration for VLM/OCR fallback on hard pages | Cloud weights; cost; not for all pages | **evaluated** |
| **olmOCR (v1)** | [arXiv:2502.18443](https://arxiv.org/abs/2502.18443) | — | Superseded by v2 for planning | — | **evaluated** |
| **GOT-OCR2.0** | [arXiv:2409.01704](https://arxiv.org/abs/2409.01704), [GitHub](https://github.com/Ucas-HaoranWei/GOT-OCR2.0) | Check repo | Possible unified OCR+format model later | Resource-heavy; integration TBD | **evaluated** |
| **DocTr** (geometric unwarping) | [arXiv:2110.12942](https://arxiv.org/abs/2110.12942) | Verify official repo from paper | **Not** Mindee docTR; future `ImagePreprocessor` for curved scans | Separate from text OCR | **evaluated** |
| **OmniDocBench** | [arXiv:2412.07626](https://arxiv.org/abs/2412.07626), [GitHub](https://github.com/opendatalab/OmniDocBench) | Dataset license per repo | Future offline metrics harness; no commercial books in git | Metrics ≠ editorial EPUB quality | **evaluated** |
| **EPUBCheck** | [W3C docs](https://www.w3.org/publishing/epubcheck/docs/) | BSD-style (tool) | Technical EPUB validation subprocess | Does not judge OCR/fidelity | **integrated** (hook; tool optional) |
| **native_pdf (pypdf)** | pypdf project | BSD-3-Clause | Default P1 parser — real native text extraction | No layout/reading order; useless on pure scans | **integrated** |

## Docling — what we reproduce vs inspire

- **Reproduce (P1 adapter):** call Docling `DocumentConverter`, map items to IR blocks with provenance, preserve text without rewriting.
- **Inspire only:** full Docling export formats (DocTags, etc.) as canonical IR — we use our own `DocumentIR` schema v0.1.0.
- **Not in P1:** Docling OCR pipelines, table structure fidelity guarantees, batch benchmarks from the paper.

## PaddleOCR / olmOCR / GOT

No weights loaded in Phase 1. Selection criteria for Phase 4: license, offline viability, Spanish text quality on our fixtures, memory per page, adapter surface fit.

## EPUB generation library

**ebooklib** (LGPL-3.0) chosen for Phase 1 reflowable packaging — widely used, programmatic API. Revisit if licensing or feature gaps block distribution.

## OmniDocBench

Use only with public/synthetic fixtures stored outside commercial titles. Harness will live under `evaluation/` in a later phase; no score claims without pinned versions and recorded hardware.

## Verified in this environment (2026-10-14)

- Python 3.12, OpenJDK 21 present (for EPUBCheck JAR).
- `docling` 2.138.0 publishable on PyPI — optional install, not required for CI default.
- EPUBCheck binary not preinstalled; validation reports `available=false` unless configured.
