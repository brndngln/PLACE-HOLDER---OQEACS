FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim
RUN groupadd -r omni && useradd -r -g omni -d /app -s /sbin/nologin omni
WORKDIR /app
COPY --from=builder /install /usr/local
COPY src/ src/
RUN chown -R omni:omni /app
USER omni
EXPOSE 9672
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "9672", "--log-level", "info"]
