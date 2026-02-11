FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends curl gnupg && \
    curl -fsSL https://github.com/getsops/sops/releases/download/v3.9.2/sops-v3.9.2.linux.amd64 -o /usr/local/bin/sops && \
    chmod +x /usr/local/bin/sops && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /app
RUN pip install --no-cache-dir fastapi==0.115.6 uvicorn==0.34.0 httpx==0.28.1 prometheus-client==0.21.1 apscheduler==3.11.0 hvac==2.3.0
COPY app.py .
EXPOSE 8189
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8189"]
