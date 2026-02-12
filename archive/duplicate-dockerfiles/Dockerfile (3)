# syntax=docker/dockerfile:1

FROM python:3.11-slim as base

# Install system packages including jq and optional security scanners
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        git \
        curl \
        jq \
        afl++ \
        trivy \
        grype \
        osv-scanner \
        scancode-toolkit \
        nodejs \
        npm || true \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/verify

# Install Python fuzzing and mutation testing libraries
RUN pip install --no-cache-dir \
        atheris==2.4.0 \
        mutmut==2.4.0

# Install JavaScript mutation testing framework
RUN npm install -g @stryker-mutator/core@7.4.0 || true

# Copy verification script
COPY verify.sh /usr/local/bin/verify.sh

RUN chmod +x /usr/local/bin/verify.sh

LABEL org.opencontainers.image.source="https://example.com/omni/verify-nightly" \
      org.opencontainers.image.description="Nightly exhaustive verification image with fuzzing, mutation testing and vulnerability scanning" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.authors="Omni Team <omni@example.com>" \
      org.opencontainers.image.title="Omni Verify Nightly" \
      org.opencontainers.image.licenses="Apache-2.0"

ENTRYPOINT ["/usr/local/bin/verify.sh"]