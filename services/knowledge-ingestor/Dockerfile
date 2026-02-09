FROM python:3.12-slim

LABEL omni.quantum.component="knowledge-ingestor" \
      omni.quantum.tier="HIGH"

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN python -c "\
from tree_sitter_languages import get_language; \
[get_language(l) for l in ['python','javascript','typescript','go','rust','c','cpp','java']]"

COPY . .

EXPOSE 9420

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9420", "--workers", "2"]
