yt-dlp Server
================

Purpose: A small HTTP service wrapping yt-dlp to extract direct video URLs and metadata as a fallback for the iOS Transcribe app.

Endpoints:
- POST /extract: body {"url": "https://..."}; returns { video_url, metadata, error, code }
- GET /health: health check
- GET /version: server and yt-dlp version

Run (Docker):
- Build: docker build -t yt-dlp-server ./yt-dlp-server
- Run: docker run -p 8080:8080 --rm yt-dlp-server

Env vars:
- PORT (default 8080)
- TIMEOUT_SEC (default 30)
- RATE_LIMIT_RPS (default 2)
- RATE_LIMIT_BURST (default 4)

Integration (iOS):
- Set ytDlpFallbackEnabled = true
- Set ytDlpServerURL to your server (e.g., https://yt-proxy.example.com)
- Adjust ytDlpTimeout, fallbackRetryCount, fallbackRetryDelay

Notes:
- Includes in-memory rate limiting to prevent abuse
- For production deploy behind a reverse proxy with TLS and optional auth

