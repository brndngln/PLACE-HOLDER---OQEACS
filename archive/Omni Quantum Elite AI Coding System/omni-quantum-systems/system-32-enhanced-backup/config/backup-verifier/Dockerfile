FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends restic postgresql-client && rm -rf /var/lib/apt/lists/*
WORKDIR /app
RUN pip install --no-cache-dir fastapi==0.115.6 uvicorn==0.34.0 httpx==0.28.1 prometheus-client==0.21.1 apscheduler==3.11.0
COPY app.py .
RUN mkdir -p /verify/staging
EXPOSE 8188
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8188"]
