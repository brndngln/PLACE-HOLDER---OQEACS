FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi==0.115.0 \
    uvicorn==0.30.0 \
    httpx==0.27.0 \
    redis==5.0.0 \
    asyncpg==0.29.0 \
    sqlalchemy[asyncio]==2.0.30 \
    pydantic==2.7.0 \
    docker==7.1.0 \
    apscheduler==3.10.4 \
    prometheus-client==0.21.0

COPY app.py .
COPY service_registry.py .

EXPOSE 9500

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "9500", "--workers", "2"]
