FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    httpx==0.27.0 \
    mattermostdriver==7.3.2

COPY app.py .

CMD ["python", "app.py"]
