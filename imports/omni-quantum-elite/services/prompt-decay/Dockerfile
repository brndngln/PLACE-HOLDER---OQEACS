# syntax=docker/dockerfile:1

FROM python:3.11-slim as builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim as runtime

WORKDIR /app

RUN adduser --disabled-password --gecos "" omni

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY . .

USER omni

EXPOSE 8333

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8333/health || exit 1

LABEL org.opencontainers.image.source="https://example.com/omni/prompt-decay" \
      org.opencontainers.image.description="Prompt decay detection service" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.authors="Omni Team <omni@example.com>" \
      org.opencontainers.image.title="Omni Prompt Decay Detector" \
      org.opencontainers.image.licenses="Apache-2.0"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8333"]