FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir \
    fastapi==0.115.6 \
    uvicorn==0.34.0 \
    httpx==0.28.1 \
    prometheus-client==0.21.1 \
    redis==5.2.1
COPY app.py .
EXPOSE 8184
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8184"]
