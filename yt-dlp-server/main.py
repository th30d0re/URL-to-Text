import asyncio
import os
import time
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, AnyHttpUrl
import yt_dlp


APP_NAME = "yt-dlp-server"
APP_VERSION = "0.1.0"


class ExtractRequest(BaseModel):
    url: AnyHttpUrl
    # Future: quality, cookies, headers, etc.


class ExtractResponse(BaseModel):
    video_url: Optional[str] = None
    metadata: Dict[str, Any] = {}
    error: Optional[str] = None
    code: Optional[str] = None


app = FastAPI(title=APP_NAME, version=APP_VERSION)


# Basic in-memory token bucket per IP for rate limiting
RATE_LIMIT_RPS = float(os.getenv("RATE_LIMIT_RPS", "2.0"))
RATE_LIMIT_BURST = float(os.getenv("RATE_LIMIT_BURST", "4.0"))
TIMEOUT_SEC = float(os.getenv("TIMEOUT_SEC", "30"))


class TokenBucket:
    def __init__(self, rate: float, burst: float):
        self.rate = rate
        self.capacity = burst
        self.tokens = burst
        self.timestamp = time.monotonic()

    def allow(self) -> bool:
        now = time.monotonic()
        elapsed = now - self.timestamp
        self.timestamp = now
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False


_buckets: Dict[str, TokenBucket] = {}


def _get_bucket(ip: str) -> TokenBucket:
    if ip not in _buckets:
        _buckets[ip] = TokenBucket(RATE_LIMIT_RPS, RATE_LIMIT_BURST)
    return _buckets[ip]


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/version")
async def version():
    return {
        "app": APP_NAME,
        "version": APP_VERSION,
        "yt_dlp_version": yt_dlp.version.__version__
    }


@app.post("/extract", response_model=ExtractResponse)
async def extract(req: Request, payload: ExtractRequest):
    # rate limit
    ip = req.client.host if req.client else "unknown"
    if not _get_bucket(ip).allow():
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        # Best format selection can be handled by client if needed; we surface direct URL
    }

    async def run() -> ExtractResponse:
        try:
            loop = asyncio.get_running_loop()
            info = await loop.run_in_executor(None, _extract_info, payload.url, ydl_opts)
        except Exception as e:  # noqa: BLE001
            error_str = str(e).lower()
            if "private" in error_str or "login" in error_str:
                raise HTTPException(status_code=403, detail="Content is private or requires authentication")
            elif "not found" in error_str or "does not exist" in error_str:
                raise HTTPException(status_code=404, detail="Video not found")
            elif "unavailable" in error_str or "not available" in error_str:
                raise HTTPException(status_code=422, detail="Video is not available")
            else:
                raise HTTPException(status_code=422, detail=f"Extraction failed: {str(e)}")

        # Map metadata
        md = {
            "title": info.get("title"),
            "duration": info.get("duration"),
            "thumbnail_url": info.get("thumbnail"),
            "uploader": info.get("uploader"),
            "view_count": info.get("view_count"),
            "description": info.get("description"),
            "file_size": info.get("filesize") or info.get("filesize_approx"),
            "format": info.get("ext"),
            "platform": info.get("extractor_key"),
        }

        # Direct URL: prefer info["url"], fallback to best format
        direct_url = info.get("url")
        if not direct_url:
            fmts = info.get("formats") or []
            # Prefer mp4 over m3u8 when possible
            preferred = None
            for f in reversed(fmts):  # assume later formats are better
                if f.get("protocol") == "m3u8":
                    preferred = preferred or f
                elif str(f.get("ext")) == "mp4":
                    preferred = f
                    break
                else:
                    preferred = preferred or f
            direct_url = preferred.get("url") if preferred else None

        return ExtractResponse(video_url=direct_url, metadata=md)

    try:
        return await asyncio.wait_for(run(), timeout=TIMEOUT_SEC)
    except asyncio.TimeoutError as _:
        raise HTTPException(status_code=504, detail="timeout")


def _extract_info(url: str, opts: Dict[str, Any]):
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8080"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)

