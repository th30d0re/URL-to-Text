FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir "mcp[cli]>=1.2.0" "httpx>=0.27.0"

COPY . .

RUN useradd -m -u 1000 mcpuser \
    && chown -R mcpuser:mcpuser /app

USER mcpuser

CMD ["python", "url_to_text_server.py"]
