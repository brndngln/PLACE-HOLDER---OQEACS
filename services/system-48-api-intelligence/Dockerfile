# Stage 1: Build dependencies
FROM python:3.12-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Production image
FROM python:3.12-slim AS production

RUN groupadd --gid 1001 omni && \
    useradd --uid 1001 --gid omni --shell /bin/bash --create-home omni

WORKDIR /app

COPY --from=builder /install /usr/local
COPY src/ ./src/

RUN chown -R omni:omni /app

USER omni

EXPOSE 9652

CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "9652", "--workers", "1"]
