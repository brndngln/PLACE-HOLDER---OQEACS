# syntax=docker/dockerfile:1

FROM node:20-bullseye-slim as base

# Install system dependencies: Python, pip, git, curl, jq and gitleaks if available
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        git \
        curl \
        jq \
        gitleaks || true \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/verify

# Install Python verification tools for fast verification
RUN pip3 install --no-cache-dir \
        pytest==7.4.3 \
        pytest-cov==4.1.0 \
        semgrep==1.75.0 \
        detect-secrets==1.4.0

# Install Node.js verification tools
RUN npm install -g \
        jest@29.7.0 \
        vitest@1.0.0 \
        @stoplight/spectral-cli@6.7.0 || true

# Copy the verification script into the image
COPY verify.sh /usr/local/bin/verify.sh

# Make the script executable
RUN chmod +x /usr/local/bin/verify.sh

LABEL org.opencontainers.image.source="https://example.com/omni/verify-fast" \
      org.opencontainers.image.description="Fast verification image with testing and security scanning tools" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.authors="Omni Team <omni@example.com>" \
      org.opencontainers.image.title="Omni Verify Fast" \
      org.opencontainers.image.licenses="Apache-2.0"

ENTRYPOINT ["/usr/local/bin/verify.sh"]