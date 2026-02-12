# syntax=docker/dockerfile:1.4
##
## Omni Quantum IaC Linting Image
##
## This Dockerfile builds an image with tools required for infrastructure
## security linting. It installs Hadolint, Checkov and ShellCheck. The
## build uses a multi‑stage approach to minimize final image size and uses
## a non‑root user for execution.

FROM python:3.11-slim AS builder

WORKDIR /work

# Install system dependencies for shellcheck and hadolint
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends wget bash ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies for Checkov
COPY requirements.txt /tmp/
RUN pip install --no-cache-dir --upgrade pip && \
    pip wheel --no-cache-dir -r /tmp/requirements.txt -w /wheels

# Download hadolint binary
RUN wget -qO /tmp/hadolint https://github.com/hadolint/hadolint/releases/download/v2.12.0/hadolint-Linux-x86_64 && \
    chmod +x /tmp/hadolint

# Download shellcheck binary
RUN wget -qO /tmp/shellcheck.tar.xz https://github.com/koalaman/shellcheck/releases/download/v0.9.0/shellcheck-v0.9.0.linux.x86_64.tar.xz && \
    mkdir -p /tmp/sc && \
    tar -xf /tmp/shellcheck.tar.xz -C /tmp/sc && \
    mv /tmp/sc/shellcheck-v0.9.0/shellcheck /tmp/shellcheck && \
    chmod +x /tmp/shellcheck && \
    rm -rf /tmp/sc

FROM python:3.11-slim

LABEL org.opencontainers.image.title="Omni Quantum IaC Linting" \
      org.opencontainers.image.description="Container for IaC and script security linting" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.authors="Omni Quantum Team" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.source="https://example.com/omni-quantum" \
      org.opencontainers.image.documentation="https://example.com/docs/omni-quantum"

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/home/omni/.local/bin:$PATH"

WORKDIR /app

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*.whl && rm -rf /wheels

COPY --from=builder /tmp/hadolint /usr/local/bin/hadolint
COPY --from=builder /tmp/shellcheck /usr/local/bin/shellcheck

# Create non‑root user
RUN adduser --disabled-password --gecos "" omni && chown -R omni:omni /app
USER omni

COPY lint.sh /app/lint.sh
RUN chmod +x /app/lint.sh

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s CMD ["/usr/local/bin/hadolint", "--version"]

ENTRYPOINT ["/app/lint.sh"]