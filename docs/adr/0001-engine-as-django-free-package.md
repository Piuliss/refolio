# ADR 0001: Conversion engine as Django-free package

## Status

Accepted (Phase 0)

## Context

The platform needs the same conversion logic in Celery workers, CLI, and future desktop packaging. Coupling to Django ORM complicates testing and reuse.

## Decision

Implement all conversion logic in `packages/converter` with zero Django imports. Django apps orchestrate jobs, storage, and API only.

## Consequences

- Clear boundary for unit tests and future evaluation harness.
- Artifacts persisted by Django; engine reads/writes paths passed from the worker task.
