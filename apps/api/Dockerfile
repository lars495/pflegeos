FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        ffmpeg \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencies first (better caching)
COPY apps/api/requirements.txt /app/apps/api/requirements.txt
RUN pip install -r /app/apps/api/requirements.txt

# Repo-Layout: api liest packages/ als Geschwister
COPY apps/api /app/apps/api
COPY packages /app/packages
COPY scripts /app/scripts
COPY legal_requirements.yaml /app/legal_requirements.yaml

ENV PYTHONPATH=/app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD curl -fsS http://localhost:8000/healthz || exit 1

CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
