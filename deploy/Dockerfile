FROM python:3.12.8-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY packages/converter /app/packages/converter
COPY backend /app/backend
COPY pyproject.toml /app/pyproject.toml

RUN pip install --no-cache-dir pip==24.3.1 \
    && pip install --no-cache-dir -e /app/packages/converter \
    && pip install --no-cache-dir -e "/app/backend[dev]"

ENV PYTHONUNBUFFERED=1
