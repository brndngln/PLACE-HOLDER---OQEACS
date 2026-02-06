FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir \
    httpx==0.28.1 redis==5.2.1
COPY app.py .
CMD ["python", "app.py"]
