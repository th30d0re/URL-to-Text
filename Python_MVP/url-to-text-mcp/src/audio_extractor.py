"""Audio extraction module using ffmpeg."""

import subprocess
import sys
from pathlib import Path
from typing import Optional, Callable

from .config import Config


class AudioExtractor:
    """Handles audio extraction from video files using ffmpeg."""
    
    def __init__(self, config: Config):
        """Initialize audio extractor with configuration."""
        self.config = config
        self._validate_ffmpeg()
    
    def _validate_ffmpeg(self) -> None:
        """Validate that ffmpeg and ffprobe are installed and accessible."""
        # Validate ffmpeg
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                raise RuntimeError("ffmpeg is not working properly")
        except FileNotFoundError:
            raise RuntimeError(
                "ffmpeg is not installed. Please install ffmpeg:\n"
                "  - macOS: brew install ffmpeg\n"
                "  - Ubuntu/Debian: sudo apt install ffmpeg\n"
                "  - Windows: Download from https://ffmpeg.org/download.html"
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("ffmpeg command timed out")
        except Exception as e:
            raise RuntimeError(f"Error validating ffmpeg: {e}")
        
        # Validate ffprobe
        try:
            result = subprocess.run(
                ['ffprobe', '-version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                raise RuntimeError("ffprobe is not working properly")
        except FileNotFoundError:
            raise RuntimeError(
                "ffprobe is not installed. Please install ffmpeg (which includes ffprobe):\n"
                "  - macOS: brew install ffmpeg\n"
                "  - Ubuntu/Debian: sudo apt install ffmpeg\n"
                "  - Windows: Download from https://ffmpeg.org/download.html"
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("ffprobe command timed out")
        except Exception as e:
            raise RuntimeError(f"Error validating ffprobe: {e}")
    
    def extract_audio(self, video_path: Path, progress_callback: Optional[Callable] = None) -> Path:
        """
        Extract audio from video file to MP3 format.
        
        Args:
            video_path: Path to input video file
            progress_callback: Optional callback function for progress updates
            
        Returns:
            Path to extracted audio file
            
        Raises:
            FileNotFoundError: If video file doesn't exist
            RuntimeError: If ffmpeg extraction fails
        """
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        # Generate output audio file path
        audio_path = self.config.get_temp_file_path(prefix='audio', suffix='.mp3')
        
        # Build ffmpeg command
        cmd = [
            'ffmpeg',
            '-i', str(video_path),
            '-vn',  # No video
            '-acodec', 'mp3',  # MP3 codec
            '-ar', str(self.config.audio_sample_rate),  # Sample rate
            '-ac', '1',  # Mono audio (better for speech recognition)
            '-ab', '128k',  # Audio bitrate
            '-y',  # Overwrite output file
            str(audio_path)
        ]
        
        try:
            if progress_callback:
                progress_callback("Extracting audio from video...")
            
            # Run ffmpeg command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode != 0:
                error_msg = result.stderr or "Unknown ffmpeg error"
                raise RuntimeError(f"ffmpeg extraction failed: {error_msg}")
            
            if not audio_path.exists():
                raise RuntimeError("Audio extraction completed but output file not found")
            
            if progress_callback:
                progress_callback("Audio extraction completed")
            
            return audio_path
            
        except subprocess.TimeoutExpired:
            raise RuntimeError("Audio extraction timed out (5 minutes)")
        except Exception as e:
            if isinstance(e, RuntimeError):
                raise
            raise RuntimeError(f"Unexpected error during audio extraction: {e}")
    
    def validate_audio_file(self, audio_path: Path) -> bool:
        """
        Validate that the extracted audio file is valid and within size limits.
        
        Args:
            audio_path: Path to audio file to validate
            
        Returns:
            True if file is valid, False otherwise
        """
        if not audio_path.exists():
            return False
        
        # Check file size
        file_size = audio_path.stat().st_size
        if file_size > self.config.max_file_size_bytes:
            return False
        
        # Check if file is not empty
        if file_size == 0:
            return False
        
        # Use ffprobe to validate audio file
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-show_entries', 'format=duration',
                '-of', 'csv=p=0',
                str(audio_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                return False
            
            # Check if duration is valid (not empty or zero)
            duration = result.stdout.strip()
            if not duration or duration == '0' or duration == 'N/A':
                return False
            
            return True
            
        except Exception:
            return False
    
    def get_audio_info(self, audio_path: Path) -> dict:
        """
        Get information about the audio file.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Dictionary containing audio information
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-show_entries', 'format=duration,size,bit_rate:stream=codec_name,sample_rate,channels',
                '-of', 'json',
                str(audio_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                return {'error': 'Could not get audio info'}
            
            import json
            info = json.loads(result.stdout)
            
            format_info = info.get('format', {})
            stream_info = info.get('streams', [{}])[0] if info.get('streams') else {}
            
            return {
                'duration': float(format_info.get('duration', 0)),
                'size_bytes': int(format_info.get('size', 0)),
                'bit_rate': int(format_info.get('bit_rate', 0)),
                'codec': stream_info.get('codec_name', 'unknown'),
                'sample_rate': int(stream_info.get('sample_rate', 0)),
                'channels': int(stream_info.get('channels', 0)),
            }
            
        except Exception as e:
            return {'error': f'Could not get audio info: {e}'}
    
    def segment_audio(self, audio_path: Path, progress_callback: Optional[Callable] = None) -> list[Path]:
        """
        Segment large audio file into smaller chunks for processing.
        
        Args:
            audio_path: Path to input audio file
            progress_callback: Optional callback function for progress updates
            
        Returns:
            List of paths to segmented audio files
            
        Raises:
            FileNotFoundError: If audio file doesn't exist
            RuntimeError: If ffmpeg segmentation fails
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        if progress_callback:
            progress_callback("Segmenting large audio file...")
        
        # Create temporary directory for segments
        temp_dir = self.config.temp_dir / f"segments_{audio_path.stem}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Build ffmpeg command for segmentation
        cmd = [
            'ffmpeg',
            '-i', str(audio_path),
            '-f', 'segment',
            '-segment_time', str(self.config.segment_duration_seconds),
            '-ar', str(self.config.audio_sample_rate),
            '-ac', '1',  # Mono audio
            '-acodec', 'mp3',
            '-ab', f'{self.config.transcode_bitrate_kbps}k',
            '-reset_timestamps', '1',
            '-y',  # Overwrite output files
            str(temp_dir / 'audio_seg_%03d.mp3')
        ]
        
        try:
            # Run ffmpeg command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            if result.returncode != 0:
                error_msg = result.stderr or "Unknown ffmpeg error"
                raise RuntimeError(f"ffmpeg segmentation failed: {error_msg}")
            
            # Find all generated segment files
            segment_files = sorted(temp_dir.glob('audio_seg_*.mp3'))
            
            if not segment_files:
                raise RuntimeError("No audio segments were created")
            
            if progress_callback:
                progress_callback(f"Created {len(segment_files)} audio segments")
            
            return segment_files
            
        except subprocess.TimeoutExpired:
            raise RuntimeError("Audio segmentation timed out (10 minutes)")
        except Exception as e:
            if isinstance(e, RuntimeError):
                raise
            raise RuntimeError(f"Unexpected error during audio segmentation: {e}")