# --- Stage 1: Builder ---
FROM python:3.12-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# --- Stage 2: Runtime ---
FROM python:3.12-slim AS runtime

RUN groupadd --gid 1001 omni \
    && useradd --uid 1001 --gid omni --shell /bin/bash --create-home omni

COPY --from=builder /install /usr/local

WORKDIR /app

COPY src/ ./src/

RUN chown -R omni:omni /app

USER omni

EXPOSE 8330

CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8330", "--log-level", "info"]
