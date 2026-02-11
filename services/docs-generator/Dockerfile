FROM python:3.12-slim AS builder
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim AS production
ARG BUILD_DATE
ARG VERSION=1.0.0
LABEL maintainer="Omni Quantum Elite"               version="${VERSION}"               build-date="${BUILD_DATE}"               org.opencontainers.image.title="omni-docs-generator"               org.opencontainers.image.description="Documentation Generator"               org.opencontainers.image.version="${VERSION}"

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl libpq5 && rm -rf /var/lib/apt/lists/* && groupadd -r omni && useradd -r -g omni -d /app -s /sbin/nologin omni && mkdir -p /app/data && chown -R omni:omni /app
COPY --from=builder /install /usr/local
COPY --chown=omni:omni app/ ./app/
COPY --chown=omni:omni alembic/ ./alembic/ 2>/dev/null || true
COPY --chown=omni:omni alembic.ini ./alembic.ini 2>/dev/null || true
COPY --chown=omni:omni scripts/ ./scripts/
COPY --chown=omni:omni config/ ./config/ 2>/dev/null || true
RUN chmod +x scripts/*.sh 2>/dev/null || true
USER omni
EXPOSE 9629
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=40s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:9629/health')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9629", "--workers", "2", "--loop", "uvloop", "--http", "httptools", "--log-level", "info", "--access-log", "--proxy-headers", "--forwarded-allow-ips", "*"]
