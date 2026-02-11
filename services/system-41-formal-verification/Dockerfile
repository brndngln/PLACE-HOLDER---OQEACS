FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    default-jre-headless \
    gcc \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r omni && useradd -r -g omni -d /app omni
COPY --from=builder /install /usr/local
COPY src/ ./src/
RUN mkdir -p /app/data/workdir /tmp/prometheus && chown -R omni:omni /app /tmp/prometheus
USER omni
EXPOSE 9634
HEALTHCHECK --interval=30s --timeout=10s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:9634/health')"
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "9634"]
