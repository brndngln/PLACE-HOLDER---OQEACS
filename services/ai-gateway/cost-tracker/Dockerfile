# ===========================================================================
# SYSTEM 3 -- AI GATEWAY: Cost Tracker Dockerfile
# Omni Quantum Elite AI Coding System
# ===========================================================================

FROM python:3.12-slim AS base

LABEL maintainer="omni-quantum-elite"
LABEL system="3"
LABEL component="cost-tracker"

WORKDIR /app

# System deps
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application
COPY main.py .

# Non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser
USER appuser

EXPOSE 4001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "4001", "--log-level", "info"]
