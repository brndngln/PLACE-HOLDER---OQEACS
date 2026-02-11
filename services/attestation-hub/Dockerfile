FROM python:3.12-slim AS builder
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/* && \
    groupadd -r omni && useradd -r -g omni -d /app -s /usr/sbin/nologin omni && \
    mkdir -p /app/data && chown -R omni:omni /app
COPY --from=builder /install /usr/local
COPY --chown=omni:omni app/ ./app/
COPY --chown=omni:omni sdk/ ./sdk/
COPY --chown=omni:omni scripts/ ./scripts/
RUN chmod +x scripts/*.sh
USER omni
EXPOSE 9653
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=40s CMD python -c "import httpx; r=httpx.get('http://localhost:9653/health', timeout=5.0); raise SystemExit(0 if r.status_code==200 else 1)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9653"]
