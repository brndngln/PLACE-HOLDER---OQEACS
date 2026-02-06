# syntax=docker/dockerfile:1.4
##
## Omni Quantum Cross‑Project Learning Service Dockerfile
##
## This Dockerfile builds a lightweight container for the
## cross‑project learning microservice. The build uses a
## multi‑stage approach to keep the runtime image small and
## to ensure that dependencies are pinned at specific
## versions. The final image runs as an unprivileged user,
## exposes the service on port 8334 and includes a simple
## health check. See README.md for usage.

FROM python:3.11-slim AS builder

WORKDIR /app

COPY requirements.txt .

# Install build dependencies and wheel the requirements.  We set
# PIP_NO_CACHE_DIR to avoid caching packages in the layer and
# upgrade pip to ensure compatibility.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --upgrade pip && \
    pip wheel --no-cache-dir -r requirements.txt -w /wheels

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_HOME=/app \
    PATH="/home/omni/.local/bin:$PATH"

WORKDIR $APP_HOME

COPY --from=builder /wheels /wheels
# Install dependencies from prebuilt wheels
RUN pip install --no-cache-dir /wheels/*.whl && rm -rf /wheels

COPY main.py ./

# Create an unprivileged user to run the service
RUN adduser --disabled-password --gecos "" omni && \
    chown -R omni:omni $APP_HOME
USER omni

EXPOSE 8334

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
  CMD wget --spider -q http://localhost:8334/health || exit 1

ENTRYPOINT ["uvicorn", "main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8334"]