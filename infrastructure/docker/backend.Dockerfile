# syntax=docker/dockerfile:1.7
# Build context: backend-ai/
# Build:  docker build -f infrastructure/docker/backend.Dockerfile -t ai-equity-backend backend-ai
# Run:    docker run --rm -p 8001:8001 --env-file backend-ai/.env ai-equity-backend
#
# The same image runs three different ECS services. Override CMD per service:
#   api:    (default) uvicorn src.main:app --host 0.0.0.0 --port 8001
#   worker: celery -A src.celery_app worker -l INFO
#   beat:   celery -A src.celery_app beat   -l INFO
#   migrate (one-shot): alembic upgrade head

ARG PYTHON_VERSION=3.11

# ---------- builder ----------
FROM python:${PYTHON_VERSION}-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# build-essential + libpq-dev are kept defensively: psycopg2-binary ships wheels
# today, but unrelated transitive deps (e.g. pinned source-only releases) can
# pull a compiler without warning. Stripped from the runtime stage.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY requirements.txt ./
RUN pip install --user -r requirements.txt

# ---------- runtime ----------
FROM python:${PYTHON_VERSION}-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH=/home/appuser/.local/bin:$PATH \
    APP_ENV=production \
    API_HOST=0.0.0.0 \
    API_PORT=8001

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
        ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
 && groupadd --system --gid 1000 appuser \
 && useradd  --system --uid 1000 --gid appuser --create-home --home-dir /home/appuser appuser

WORKDIR /app

COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local
COPY --chown=appuser:appuser src/         /app/src/
COPY --chown=appuser:appuser alembic/     /app/alembic/
COPY --chown=appuser:appuser alembic.ini  /app/alembic.ini
COPY --chown=appuser:appuser scripts/     /app/scripts/

USER appuser

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:${API_PORT}/healthz || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001"]
