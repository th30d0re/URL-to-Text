"""Configuration module for video-to-text application."""

import os
import tempfile
from pathlib import Path
from typing import Optional, List

from dotenv import load_dotenv


class Config:
    """
    Configuration class for managing application settings.
    
    Supports both online (OpenAI API) and offline (local Whisper) transcription modes.
    Online mode requires OPENAI_API_KEY, while offline mode uses local Whisper models.
    """
    
    def __init__(self):
        """Initialize configuration by loading environment variables."""
        load_dotenv()
        
        # Transcription mode configuration
        self.transcription_mode = os.getenv('TRANSCRIPTION_MODE', 'online').lower()
        if self.transcription_mode not in ['online', 'offline']:
            raise ValueError("TRANSCRIPTION_MODE must be 'online' or 'offline'")
        
        # OpenAI API configuration (only required for online mode)
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        if self.transcription_mode == 'online' and not self.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable is required for online mode. "
                "Please set it in your .env file or environment, or switch to offline mode."
            )
        
        # Offline Whisper configuration
        self.offline_model_name = os.getenv('OFFLINE_MODEL_NAME', 'base')
        self.whisper_device = os.getenv('WHISPER_DEVICE', 'auto')
        self.whisper_models_dir = os.getenv('WHISPER_MODELS_DIR')
        
        # Validate offline mode settings
        if self.transcription_mode == 'offline':
            self._validate_offline_settings()
        
        # Temporary directory configuration
        self.temp_dir = os.getenv('TEMP_DIR', tempfile.gettempdir())
        self.temp_dir = Path(self.temp_dir) / 'video_to_text'
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # File handling configuration
        self.keep_intermediate_files = os.getenv('KEEP_INTERMEDIATE_FILES', 'false').lower() == 'true'
        
        # OpenAI Whisper API limits
        self.max_file_size_mb = int(os.getenv('MAX_FILE_SIZE_MB', '25'))
        self.max_file_size_bytes = self.max_file_size_mb * 1024 * 1024
        
        # Supported audio formats for Whisper API
        self.supported_audio_formats = ['.mp3', '.mp4', '.mpeg', '.mpga', '.m4a', '.wav', '.webm']
        
        # Audio quality settings for extraction
        self.audio_quality = 'best'
        self.audio_format = 'mp3'
        self.audio_sample_rate = 16000  # Optimal for speech recognition
        
        # Audio chunking settings for large files
        self.segment_duration_seconds = int(os.getenv('SEGMENT_DURATION_SECONDS', '600'))  # 10 minutes
        self.transcode_bitrate_kbps = int(os.getenv('TRANSCODE_BITRATE_KBPS', '64'))
    
    def _validate_offline_settings(self) -> None:
        """Validate offline Whisper configuration settings."""
        # Validate model name
        valid_models = ['tiny', 'base', 'small', 'medium', 'large', 'large-v2', 'large-v3']
        if self.offline_model_name not in valid_models:
            raise ValueError(f"OFFLINE_MODEL_NAME must be one of: {', '.join(valid_models)}")
        
        # Validate device selection
        valid_devices = ['cpu', 'cuda', 'auto']
        if self.whisper_device not in valid_devices:
            raise ValueError(f"WHISPER_DEVICE must be one of: {', '.join(valid_devices)}")
        
        # Validate models directory if provided
        if self.whisper_models_dir:
            models_path = Path(self.whisper_models_dir)
            if not models_path.exists():
                raise ValueError(f"WHISPER_MODELS_DIR path does not exist: {models_path}")
            if not models_path.is_dir():
                raise ValueError(f"WHISPER_MODELS_DIR must be a directory: {models_path}")
    
    def validate_api_key(self) -> bool:
        """Validate that OpenAI API key is properly configured."""
        return bool(self.openai_api_key and len(self.openai_api_key.strip()) > 0)
    
    def get_temp_file_path(self, prefix: str = 'video', suffix: str = '.mp4') -> Path:
        """Generate a unique temporary file path."""
        import uuid
        filename = f"{prefix}_{uuid.uuid4().hex[:8]}{suffix}"
        return self.temp_dir / filename
    
    def cleanup_temp_files(self, file_paths: List[Path]) -> None:
        """Clean up temporary files if configured to do so."""
        if not self.keep_intermediate_files:
            for file_path in file_paths:
                try:
                    if file_path.exists():
                        file_path.unlink()
                except OSError as e:
                    import logging
                    logging.getLogger(__name__).warning(f"Could not delete temporary file {file_path}: {e}")
