# syntax=docker/dockerfile:1

FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim as runtime

WORKDIR /app

# Create non‑root user
RUN adduser --disabled-password --gecos "" omni

# Copy installed dependencies
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=info

USER omni

EXPOSE 8350

# Health check to /health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -s http://localhost:8350/health || exit 1

LABEL org.opencontainers.image.source="https://example.com/omni/code-scorer" \
      org.opencontainers.image.description="Service for scoring code across multiple quality dimensions" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.authors="Omni Team <omni@example.com>" \
      org.opencontainers.image.title="Omni Code Scorer" \
      org.opencontainers.image.licenses="Apache-2.0"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8350"]