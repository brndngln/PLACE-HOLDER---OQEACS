# syntax=docker/dockerfile:1

FROM node:20-bullseye-slim as base

# Install Python and build dependencies, including jq for JSON generation
RUN apt-get update \ 
    && apt-get install -y --no-install-recommends python3 python3-pip git curl jq \ 
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/verify

# Install Python verification tools
RUN pip3 install --no-cache-dir \
    pyright==1.1.350 \
    ruff==0.2.2 \
    black==24.2.0 \
    deptry==0.12.0

# Install Node.js verification tools
RUN npm install -g \
    typescript@5.3.3 \
    eslint@8.56.0 \
    prettier@3.2.5 \
    oxlint@0.3.2 || true

# Copy the verification script into the image
COPY verify.sh /usr/local/bin/verify.sh

# Make the script executable
RUN chmod +x /usr/local/bin/verify.sh

LABEL org.opencontainers.image.source="https://example.com/omni/verify-instant" \
      org.opencontainers.image.description="Instant verification image with type checking, linting and formatting tools" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.authors="Omni Team <omni@example.com>" \
      org.opencontainers.image.title="Omni Verify Instant" \
      org.opencontainers.image.licenses="Apache-2.0"

# Default command to run the verification script
ENTRYPOINT ["/usr/local/bin/verify.sh"]