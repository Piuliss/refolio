# Architecture (Phase 0–1)

## Goal

High-fidelity PDF → EPUB conversion with a **Django-free engine** reusable from Celery workers, HTTP API, and a future CLI/desktop. Phase 1 delivers one vertical slice: upload → persistent job → parse → IR → EPUB → quality report → artifacts.

## Repository layout

```
backend/                 # Django + DRF API, Celery task orchestration
  config/                # Settings, Celery app, URLs
  apps/documents/        # PDF upload metadata + private storage
  apps/conversions/      # Jobs, artifacts, quality report records
packages/converter/      # Engine (no Django imports)
  src/converter/
    ir/                  # Versioned Pydantic IR + JSON Schema validation
    adapters/            # DocumentParser implementations
    epub/                # Reflowable EPUB writer (ebooklib)
    validation/          # EPUBCheck runner (explicit skip if unavailable)
    quality/             # Heuristic quality report (not calibrated scores)
deploy/                  # Docker Compose (Postgres, Redis, web, worker)
docs/                    # Architecture, research, ADRs
```

Frontend (`React/Vite`) and evaluation harness are **out of scope** for Phase 1.

## Layering

| Layer | Responsibility | Depends on |
|-------|----------------|------------|
| API (`backend`) | Auth, upload, job lifecycle, artifact URLs | Django, Postgres, Celery |
| Worker (`backend` tasks) | Runs engine, persists artifacts | `converter` package |
| Engine (`converter`) | Parse → IR → EPUB → validate → report | pypdf, ebooklib, optional docling |

**Rule:** `packages/converter` must not import Django or touch the ORM.

## Pipeline (Phase 1)

1. **Upload** — PDF only, size-capped, stored under per-document media paths.
2. **Job** — `ConversionJob` row (`queued` → `running` → `completed`/`failed`/`canceled`).
3. **Parse** — `DocumentParser` adapter (default `native_pdf`; optional `docling` via `CONVERTER_PARSER`).
4. **IR** — `DocumentIR` validated against generated JSON Schema.
5. **EPUB** — Reflowable XHTML chapters via ebooklib; semantic tags where block types allow.
6. **EPUBCheck** — Subprocess if `EPUBCHECK_JAR` or `epubcheck` on PATH; otherwise `passed=null` with `skipped_reason` (never fake success).
7. **Artifacts** — `document.ir.json`, `output.epub`, `quality_report.json` linked to the job.

## Data model (API)

- **Document** — owner, file, language hint, basic metadata.
- **ConversionJob** — status, parser/engine version, Celery task id, cancel flag.
- **Artifact** — typed files (IR, EPUB, quality report).
- **QualityReportRecord** — JSON payload from engine heuristics + EPUBCheck summary.

Full structured IR lives in **JSON artifacts**, not duplicated in Postgres columns (Phase 1).

## Job states

`queued`, `running`, `awaiting_review` (reserved), `completed`, `failed`, `canceled`.

Celery results are **not** the source of truth; the job row and artifacts are.

## Security (Phase 1 baseline)

- Authenticated API (`IsAuthenticated`); private media per owner.
- PDF extension + size validation on upload.
- Worker work dirs under configurable `CONVERTER_WORK_DIR`.
- Local Compose binds services on non-default ports; no document egress to third parties.

## Extension points (later phases)

- `OcrEngine`, `StructureReconstructor`, `AiReviewer` adapters (contracts in `converter/contracts.py`).
- Editorial reconstruction ops on IR with provenance.
- Review UI and regeneration without re-OCR.
- Second OCR/parser engine behind the same `DocumentParser` interface.

## ADRs

See `docs/adr/` for recorded decisions (engine package, default parser, EPUB library, artifact storage).
