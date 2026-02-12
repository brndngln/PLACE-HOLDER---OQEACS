FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    redis-tools \
    restic \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN pip install --no-cache-dir \
    fastapi==0.115.6 uvicorn==0.34.0 httpx==0.28.1 \
    apscheduler==3.11.0 pyyaml==6.0.2 \
    prometheus-client==0.21.1 minio==7.2.12

COPY app.py .
RUN mkdir -p /backup/staging

EXPOSE 8187
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8187"]
