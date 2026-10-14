# ADR 0003: EPUBCheck never fakes success

## Status

Accepted (Phase 1)

## Context

Principle 10: no fabricated completeness. EPUBCheck may be missing in dev/CI.

## Decision

`run_epubcheck` returns `passed=null` and `skipped_reason` when the tool is unavailable. Quality reports surface skipped validation; issues endpoint emits a warning.

## Consequences

- `completed` jobs may have `epub_validation.passed=null` — distinct from technical pass/fail.
- Operators set `EPUBCHECK_JAR` or install `epubcheck` for full validation.
