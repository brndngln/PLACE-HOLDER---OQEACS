FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl docker.io \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN pip install --no-cache-dir \
    fastapi==0.115.6 uvicorn==0.34.0 httpx==0.28.1 \
    asyncpg==0.30.0 redis==5.2.1 \
    apscheduler==3.11.0 docker==7.1.0 \
    prometheus-client==0.21.1 pyyaml==6.0.2

COPY app.py service_registry.py ./

EXPOSE 9500
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "9500"]
