# ADR 0002: Default parser `native_pdf`, optional Docling

## Status

Accepted (Phase 1)

## Context

Phase 1 requires one real parser adapter. Docling is preferred for structure but has heavy dependencies. CI and local dev must run without GPU or large model downloads.

## Decision

- Ship **`NativePdfParser`** (pypdf) as default (`CONVERTER_PARSER=native_pdf`).
- Ship **`DoclingParser`** behind the same interface, enabled when `docling` extra is installed and env selects `docling`.
- Document limitations of each in `docs/research.md`.

## Consequences

- End-to-end path is always testable with synthetic PDFs.
- Production deployments aiming at layout fidelity should install Docling explicitly and pin versions.
