# yt-dlp Metadata Server

A lightweight HTTP service that wraps `yt-dlp` to provide a clean JSON API for extracting direct video URLs and metadata. This service is optimized for use as a backend fallback for mobile applications (like the iOS Transcribe app) where local extraction might be restricted or slow.

## ✨ Features

- **Direct URL Extraction**: Resolves complex platform links to direct streamable URLs.
- **Metadata Parsing**: Returns title, duration, thumbnail, uploader, and more.
- **In-Memory Rate Limiting**: Token bucket implementation to prevent service abuse.
- **Dockerized**: Easy to deploy on any cloud provider or home server.
- **FastAPI Powered**: High-performance, asynchronous processing.

## 🚀 Quick Start (Docker)

The recommended way to run the server is using Docker:

```bash
# Build the image
docker build -t yt-dlp-server .

# Run the container
docker run -p 8080:8080 --rm yt-dlp-server
```

Alternatively, use **Docker Compose**:
```bash
docker-compose up --build
```

## 📡 API Endpoints

### `POST /extract`
Extracts information from a video URL.

**Body:**
```json
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
}
```

**Response:**
```json
{
  "video_url": "https://...",
  "metadata": {
    "title": "Never Gonna Give You Up",
    "duration": 212,
    "thumbnail_url": "https://...",
    "uploader": "Rick Astley",
    "view_count": 1000000000,
    "platform": "youtube"
  }
}
```

### `GET /health`
Returns `{"status": "ok"}` if the server is running.

### `GET /version`
Returns the version of the server and the underlying `yt-dlp` library.

## ⚙️ Configuration

Environment variables can be used to tune the server:

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8080` | The port the server listens on. |
| `TIMEOUT_SEC` | `30` | Max time allowed for extraction. |
| `RATE_LIMIT_RPS` | `2.0` | Requests per second allowed per IP. |
| `RATE_LIMIT_BURST`| `4.0` | Maximum burst size for rate limiting. |

## 📱 Integration Example (iOS)

To use this server as a fallback in the Transcribe app:
1. Enable fallback: `ytDlpFallbackEnabled = true`
2. Set server URL: `ytDlpServerURL = "https://your-service-url.com"`
3. Adjust timeouts as needed.

## 🛡️ Security Notes

- The server includes basic IP-based rate limiting.
- For production use, it is highly recommended to deploy this behind a reverse proxy (like Nginx or Caddy) with TLS/HTTPS enabled.
- Add an authentication layer if the service is exposed publicly.
