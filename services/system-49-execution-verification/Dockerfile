# ---------- Stage 1: builder ----------
FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---------- Stage 2: runtime ----------
FROM python:3.12-slim AS runtime

LABEL maintainer="omni-quantum-elite"
LABEL omni.quantum.system="49"
LABEL omni.quantum.component="execution-verification"

# Install Node.js for JS/TS execution and bash utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    nodejs \
    npm \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Security: non-root user
RUN groupadd -r omni && useradd -r -g omni -d /app -s /sbin/nologin omni

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY src/ ./src/
COPY requirements.txt .

# Create temp directory for sandbox execution
RUN mkdir -p /app/sandbox_tmp && chown -R omni:omni /app

USER omni

EXPOSE 9653

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    SERVICE_PORT=9653

CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "9653", "--workers", "1", "--log-level", "info"]
