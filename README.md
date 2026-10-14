# PDF → EPUB platform (Phase 1 slice)

High-fidelity PDF to reflowable EPUB — modular Django API + **Django-free** conversion engine.

## Prerequisites

- Python 3.12+
- Optional: Docker Compose for Postgres/Redis
- Optional: [EPUBCheck](https://www.w3.org/publishing/epubcheck/) JAR (`EPUBCHECK_JAR`)
- Optional: Docling (`pip install -e 'packages/converter[docling]'`)

## Quick start (engine CLI only)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e "packages/converter[dev]"
# generate or use any small PDF
converter /path/to/sample.pdf -o /tmp/out --skip-epubcheck
```

## Backend + worker (local)

```bash
cp .env.example .env
pip install -e packages/converter
pip install -e "backend[dev]"

# Postgres + Redis (non-default ports)
docker compose -f deploy/docker-compose.yml up -d db redis

cd backend
export DJANGO_SETTINGS_MODULE=config.settings.local
python manage.py migrate
python manage.py createsuperuser  # for API auth
python manage.py runserver 127.0.0.1:38421
```

Worker (separate terminal):

```bash
cd backend
celery -A config worker -l info
```

### API (authenticated)

- `POST /api/v1/documents/` — multipart `file` (PDF), optional `language_hint`
- `GET /api/v1/documents/{id}/`
- `POST /api/v1/documents/{id}/conversions/`
- `GET /api/v1/jobs/{id}/`
- `POST /api/v1/jobs/{id}/cancel/`
- `GET /api/v1/jobs/{id}/artifacts/`
- `GET /api/v1/jobs/{id}/issues/`

## Tests

```bash
pip install -e "packages/converter[dev]"
pip install -e "backend[dev]"
ruff check packages/converter/src backend
pytest packages/converter/tests backend/tests
```

Phase 2 adds editorial passes (paragraph join, running matter, chapter patterns) and per-page OCR routing heuristics. OCR engines are optional via `CONVERTER_OCR_ENGINE`; unconfigured OCR never fabricates text.

## Configuration

See `.env.example`. Key variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| `CONVERTER_PARSER` | `native_pdf` | `docling` if extra installed |
| `EPUBCHECK_JAR` | unset | Java EPUBCheck JAR path |
| `DATABASE_URL` | localhost:54329 | Postgres |
| `CELERY_BROKER_URL` | localhost:56379 | Redis |

## Docs

- [Architecture](docs/architecture.md)
- [Research](docs/research.md)
- [ADRs](docs/adr/)

## Phase scope

Phase 1 only: no React UI, no multi-engine OCR, no editorial reconstruction ruleset. See project plan in the agent store `docs/phase-0-1-plan.md`.
