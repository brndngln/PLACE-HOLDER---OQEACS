# syntax=docker/dockerfile:1

FROM python:3.11-slim as base

# Install required system packages including git, curl, jq and optional analysis tools
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        git \
        curl \
        jq \
        docker.io || true \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/verify

# Install Python dependencies for integration testing, benchmarking and analysis
RUN pip install --no-cache-dir \
        pytest==7.4.3 \
        pytest-asyncio==0.23.3 \
        pytest-benchmark==4.0.1 \
        testcontainers[postgresql]==3.7.1 \
        testcontainers[redis]==3.7.1

# Attempt to install optional CodeQL and Infer tools
RUN curl -sSL https://github.com/github/codeql-cli-binaries/releases/latest/download/codeql-linux64.zip -o /tmp/codeql.zip || true \
    && ( unzip /tmp/codeql.zip -d /opt/codeql || true ) \
    && rm -f /tmp/codeql.zip

# Attempt to install Facebook Infer if available
RUN apt-get update \
    && apt-get install -y --no-install-recommends infer || true \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/opt/codeql/codeql:${PATH}"

# Copy verification script
COPY verify.sh /usr/local/bin/verify.sh

# Make script executable
RUN chmod +x /usr/local/bin/verify.sh

LABEL org.opencontainers.image.source="https://example.com/omni/verify-deep" \
      org.opencontainers.image.description="Deep verification image with integration tests and advanced static analysis" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.authors="Omni Team <omni@example.com>" \
      org.opencontainers.image.title="Omni Verify Deep" \
      org.opencontainers.image.licenses="Apache-2.0"

ENTRYPOINT ["/usr/local/bin/verify.sh"]