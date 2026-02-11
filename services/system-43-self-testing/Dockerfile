# ---------- Stage 1: builder ----------
FROM python:3.12-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---------- Stage 2: runtime ----------
FROM python:3.12-slim AS runtime

LABEL maintainer="omni-quantum-elite"
LABEL omni.quantum.system="43"
LABEL omni.quantum.component="self-testing"

# Security: non-root user
RUN groupadd -r omni && useradd -r -g omni -d /app -s /sbin/nologin omni

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY src/ ./src/
COPY requirements.txt .

# Ownership
RUN chown -R omni:omni /app

USER omni

EXPOSE 9636

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    SERVICE_PORT=9636

CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "9636", "--workers", "1", "--log-level", "info"]
