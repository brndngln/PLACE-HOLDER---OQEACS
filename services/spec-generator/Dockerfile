# syntax=docker/dockerfile:1.4
##
## Omni Quantum Spec Generator Service Dockerfile
##
## This Dockerfile builds a container for the specification generation
## microservice. It uses a multi‑stage build to wheel dependencies and
## produces a slim runtime image. The container runs as an unprivileged
## user and exposes port 8332. A health check probes the `/health`
## endpoint. See README.md for details.

FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
# Install dependencies into wheel format to avoid network access during runtime
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --upgrade pip && \
    pip wheel --no-cache-dir -r requirements.txt -w /wheels

FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_HOME=/app
WORKDIR $APP_HOME
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*.whl && rm -rf /wheels
COPY main.py ./
RUN adduser --disabled-password --gecos "" omni && chown -R omni:omni $APP_HOME
USER omni
EXPOSE 8332
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
  CMD wget --spider -q http://localhost:8332/health || exit 1
ENTRYPOINT ["uvicorn", "main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8332"]