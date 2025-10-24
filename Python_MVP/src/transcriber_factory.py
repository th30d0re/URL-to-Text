"""Factory for creating transcriber instances based on configuration."""

from typing import Union
from .config import Config
from .cloud_transcriber import CloudTranscriber
from .offline_transcriber import OfflineTranscriber


def create_transcriber(config: Config) -> Union[CloudTranscriber, OfflineTranscriber]:
    """
    Create a transcriber instance based on the configuration.
    
    Args:
        config: Configuration object containing transcription mode settings
        
    Returns:
        Transcriber instance (CloudTranscriber or OfflineTranscriber)
        
    Raises:
        ImportError: If required dependencies for the selected mode are not available
        ValueError: If configuration is invalid
    """
    if config.transcription_mode == 'online':
        try:
            return CloudTranscriber(config)
        except ImportError as e:
            raise ImportError(
                f"Cloud transcriber dependencies not available: {e}\n"
                "Install with: pip install openai"
            )
    
    elif config.transcription_mode == 'offline':
        try:
            return OfflineTranscriber(config)
        except ImportError as e:
            raise ImportError(
                f"Offline transcriber dependencies not available: {e}\n"
                "Install with: pip install openai-whisper torch torchaudio"
            )
    
    else:
        raise ValueError(f"Invalid transcription mode: {config.transcription_mode}")