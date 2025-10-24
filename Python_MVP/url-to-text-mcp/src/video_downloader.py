"""Video downloader module using yt-dlp."""

import re
import subprocess
import sys
from pathlib import Path
from typing import Optional, Callable
from urllib.parse import urlparse

import yt_dlp
from yt_dlp.utils import DownloadError

from .config import Config


class VideoDownloader:
    """Handles video downloading from various platforms using yt-dlp."""
    
    def __init__(self, config: Config):
        """Initialize video downloader with configuration."""
        self.config = config
        self._validate_yt_dlp()
    
    def _validate_yt_dlp(self) -> None:
        """Validate that yt-dlp is properly installed."""
        try:
            yt_dlp.version.__version__
        except AttributeError:
            raise ImportError("yt-dlp is not properly installed. Please install it with: pip install yt-dlp")
    
    def validate_url(self, url: str) -> bool:
        """Validate if the URL is a supported video platform."""
        if not url or not isinstance(url, str):
            return False
        
        # Basic URL format validation
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return False
        except Exception:
            return False
        
        # Check if it's a supported platform by testing with yt-dlp
        try:
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                ydl.extract_info(url, download=False)
            return True
        except DownloadError:
            return False
        except Exception:
            return False
    
    def download_video(self, url: str, progress_callback: Optional[Callable] = None) -> Path:
        """
        Download video from URL to temporary directory.
        
        Args:
            url: Video URL to download
            progress_callback: Optional callback function for progress updates
            
        Returns:
            Path to downloaded video file
            
        Raises:
            ValueError: If URL is invalid or unsupported
            DownloadError: If download fails
        """
        if not self.validate_url(url):
            raise ValueError(f"Invalid or unsupported video URL: {url}")
        
        # Generate output file path
        output_path = self.config.get_temp_file_path(prefix='video', suffix='.%(ext)s')
        
        # Configure yt-dlp options
        ydl_opts = {
            'outtmpl': str(output_path),
            'format': 'best[height<=720]/best',  # More flexible format selection
            'merge_output_format': 'mp4',  # Ensure consistent output format
            'quiet': False if progress_callback else True,
            'no_warnings': False,
        }
        
        # Track downloaded file path
        downloaded_path: Path | None = None
        
        # Add progress hook if callback provided
        if progress_callback:
            def progress_hook(d):
                nonlocal downloaded_path
                if d['status'] == 'downloading':
                    progress_callback(f"Downloading: {d.get('_percent_str', 'Unknown')} of {d.get('_total_bytes_str', 'Unknown')}")
                elif d['status'] == 'finished':
                    downloaded_path = Path(d['filename'])
                    progress_callback("Download completed")
            
            ydl_opts['progress_hooks'] = [progress_hook]
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract video info and download in one call
                info = ydl.extract_info(url, download=True)
                if not info:
                    raise DownloadError("Could not extract video information")
                
                # Return the exact downloaded file path
                if downloaded_path and downloaded_path.exists():
                    return downloaded_path
                else:
                    # Fallback to prepared filename
                    prepared_filename = ydl.prepare_filename(info)
                    if prepared_filename and Path(prepared_filename).exists():
                        return Path(prepared_filename)
                    else:
                        raise DownloadError("Downloaded file not found")
                
        except DownloadError as e:
            raise DownloadError(f"Failed to download video: {e}")
        except Exception as e:
            raise DownloadError(f"Unexpected error during download: {e}")
    
    def get_video_info(self, url: str) -> dict:
        """
        Get information about the video without downloading.
        
        Args:
            url: Video URL to get info for
            
        Returns:
            Dictionary containing video information
        """
        if not self.validate_url(url):
            raise ValueError(f"Invalid or unsupported video URL: {url}")
        
        try:
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'uploader': info.get('uploader', 'Unknown'),
                    'view_count': info.get('view_count', 0),
                    'description': info.get('description', '')[:200] + '...' if info.get('description') else '',
                }
        except Exception as e:
            raise DownloadError(f"Failed to get video info: {e}")
