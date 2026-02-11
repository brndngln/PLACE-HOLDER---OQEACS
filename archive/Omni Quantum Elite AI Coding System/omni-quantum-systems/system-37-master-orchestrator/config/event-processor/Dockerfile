FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    redis==5.0.0 \
    httpx==0.27.0

COPY app.py .

CMD ["python", "app.py"]
