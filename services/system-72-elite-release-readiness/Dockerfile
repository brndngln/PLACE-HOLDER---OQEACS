FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r appuser \
    && useradd -r -g appuser -s /usr/sbin/nologin appuser
COPY --from=builder /install /usr/local
COPY src/ ./src/
RUN chown -R appuser:appuser /app
USER appuser
EXPOSE 9917
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:9917/health || exit 1
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "9917"]
