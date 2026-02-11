FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim
WORKDIR /app
RUN groupadd -r omni && useradd -r -g omni -d /app omni
COPY --from=builder /install /usr/local
COPY src/ ./src/
RUN mkdir -p /app/data /tmp/prometheus && chown -R omni:omni /app /tmp/prometheus
USER omni
EXPOSE 8325
HEALTHCHECK --interval=30s --timeout=10s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8325/health')"
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8325"]
