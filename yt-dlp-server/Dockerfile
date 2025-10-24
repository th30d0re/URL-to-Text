# syntax=docker/dockerfile:1

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY yt-dlp-server/main.py /app/main.py

RUN pip install --no-cache-dir fastapi uvicorn[standard] yt-dlp

EXPOSE 8080

ENV PORT=8080 TIMEOUT_SEC=30 RATE_LIMIT_RPS=2 RATE_LIMIT_BURST=4

USER nobody

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]

