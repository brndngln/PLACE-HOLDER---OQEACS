FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir \
    fastapi==0.115.6 \
    uvicorn==0.34.0 \
    httpx==0.28.1 \
    hvac==2.3.0 \
    apscheduler==3.11.0 \
    prometheus-client==0.21.1
COPY app.py .
EXPOSE 8189
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8189"]
