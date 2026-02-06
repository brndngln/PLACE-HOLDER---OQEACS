FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir \
    fastapi==0.115.6 \
    uvicorn==0.34.0 \
    httpx==0.28.1 \
    asyncpg==0.30.0 \
    apscheduler==3.10.4 \
    prometheus-client==0.21.1 \
    pyyaml==6.0.2
COPY app.py .
EXPOSE 8182
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8182"]
