"""Offline transcription module using local Whisper models."""

import time
from pathlib import Path
from typing import Optional, Dict, Any, List

try:
    import whisper
    import torch
    import ssl
    # Fix SSL certificate verification issue
    ssl._create_default_https_context = ssl._create_unverified_context
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

from .config import Config


class OfflineTranscriber:
    """Handles audio transcription using local Whisper models."""
    
    def __init__(self, config: Config):
        """Initialize transcriber with configuration."""
        if not WHISPER_AVAILABLE:
            raise ImportError(
                "openai-whisper package is required for offline transcription. "
                "Install with: pip install openai-whisper torch torchaudio"
            )
        
        self.config = config
        self.model = None
        self._resolved_device = None
        self._load_model()
    
    def _load_model(self) -> None:
        """Load the Whisper model based on configuration."""
        try:
            if self.config.whisper_device == 'auto':
                device = 'cuda' if torch.cuda.is_available() else 'cpu'
            else:
                device = self.config.whisper_device
            
            # Set device for Whisper
            if device == 'cuda' and not torch.cuda.is_available():
                device = 'cpu'
                import logging
                logging.getLogger(__name__).warning("CUDA not available, falling back to CPU")
            
            # Store the resolved device
            self._resolved_device = device
            
            # Load model
            self.model = whisper.load_model(
                self.config.offline_model_name,
                device=device,
                download_root=self.config.whisper_models_dir
            )
            
            import logging
            logging.getLogger(__name__).info(f"Loaded Whisper model '{self.config.offline_model_name}' on {device}")
            
        except Exception as e:
            raise RuntimeError(f"Failed to load Whisper model: {e}")
    
    def validate_audio_file(self, audio_path: Path) -> bool:
        """
        Validate audio file for Whisper processing.
        
        Args:
            audio_path: Path to audio file to validate
            
        Returns:
            True if file is valid for Whisper, False otherwise
        """
        if not audio_path.exists():
            return False
        
        # Check if file is not empty
        if audio_path.stat().st_size == 0:
            return False
        
        # Check file extension (Whisper supports many formats)
        supported_extensions = ['.mp3', '.mp4', '.mpeg', '.mpga', '.m4a', '.wav', '.webm', '.flac', '.ogg']
        if audio_path.suffix.lower() not in supported_extensions:
            return False
        
        return True
    
    def transcribe(
        self, 
        audio_path: Path, 
        language: Optional[str] = None,
        temperature: float = 0.0,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Transcribe audio file using local Whisper model.
        
        Args:
            audio_path: Path to audio file to transcribe
            language: Language code (e.g., 'en', 'es', 'fr') or None for auto-detection
            temperature: Temperature for transcription (0.0 to 1.0)
            progress_callback: Optional callback function for progress updates
            
        Returns:
            Dictionary containing transcription result and metadata
            
        Raises:
            FileNotFoundError: If audio file doesn't exist
            ValueError: If audio file is invalid
            RuntimeError: If transcription fails
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        if not self.validate_audio_file(audio_path):
            raise ValueError(f"Audio file is invalid: {audio_path}")
        
        try:
            if progress_callback:
                progress_callback("Loading audio file...")
            
            # Load audio
            audio = whisper.load_audio(str(audio_path))
            
            if progress_callback:
                progress_callback("Transcribing audio...")
            
            # Transcribe
            result = self.model.transcribe(
                audio,
                language=language,
                temperature=temperature,
                verbose=False
            )
            
            if progress_callback:
                progress_callback("Transcription completed")
            
            # Prepare result
            transcription_result = {
                'text': result['text'],
                'language': result.get('language', language),
                'temperature': temperature,
                'file_size': audio_path.stat().st_size,
                'file_name': audio_path.name,
                'detected_language': result.get('language'),
                'duration': len(audio) / whisper.audio.SAMPLE_RATE,  # Approximate duration
            }
            
            # Add segments if available
            if 'segments' in result:
                transcription_result['segments'] = result['segments']
            
            return transcription_result
            
        except Exception as e:
            error_msg = str(e)
            if "out of memory" in error_msg.lower() or "oom" in error_msg.lower():
                raise RuntimeError(f"Out of memory during transcription: {error_msg}")
            elif "cuda" in error_msg.lower():
                raise RuntimeError(f"CUDA error during transcription: {error_msg}")
            else:
                raise RuntimeError(f"Transcription failed: {error_msg}")
    
    def transcribe_with_retry(
        self, 
        audio_path: Path, 
        max_retries: int = 2,
        retry_delay: float = 2.0,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Transcribe audio file with retry logic for transient failures.
        
        Args:
            audio_path: Path to audio file to transcribe
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            **kwargs: Additional arguments passed to transcribe method
            
        Returns:
            Dictionary containing transcription result and metadata
        """
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                return self.transcribe(audio_path, **kwargs)
            except Exception as e:
                last_exception = e
                
                # Don't retry for certain types of errors
                if any(keyword in str(e).lower() for keyword in ['not found', 'invalid', 'unsupported']):
                    raise e
                
                if attempt < max_retries:
                    if 'progress_callback' in kwargs and kwargs['progress_callback']:
                        kwargs['progress_callback'](f"Transcription attempt {attempt + 1} failed, retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    retry_delay *= 1.5  # Gradual backoff
                else:
                    break
        
        raise last_exception
    
    def transcribe_many(
        self,
        audio_paths: List[Path],
        language: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Transcribe multiple audio files and combine results.
        
        Args:
            audio_paths: List of paths to audio files to transcribe
            language: Language code for transcription
            progress_callback: Optional callback function for progress updates
            
        Returns:
            Dictionary containing combined transcription result and metadata
        """
        if not audio_paths:
            raise ValueError("No audio files provided")
        
        all_texts = []
        all_segments = []
        total_duration = 0
        total_size = 0
        
        for i, audio_path in enumerate(audio_paths):
            if progress_callback:
                progress_callback(f"Transcribing segment {i+1}/{len(audio_paths)}...")
            
            try:
                result = self.transcribe_with_retry(
                    audio_path,
                    language=language,
                    progress_callback=None  # Don't show individual progress for segments
                )
                
                all_texts.append(result['text'])
                total_duration += result.get('duration', 0)
                total_size += result.get('file_size', 0)
                
                # Collect segments if available
                if 'segments' in result:
                    all_segments.extend(result['segments'])
                
            except Exception as e:
                if progress_callback:
                    progress_callback(f"Warning: Failed to transcribe segment {i+1}: {e}")
                continue
        
        if not all_texts:
            raise RuntimeError("Failed to transcribe any audio segments")
        
        # Combine all transcriptions
        combined_text = '\n\n'.join(all_texts)
        
        result = {
            'text': combined_text,
            'language': language,
            'file_size': total_size,
            'duration': total_duration,
            'segments_processed': len(all_texts),
            'total_segments': len(audio_paths),
            'success': True
        }
        
        # Add combined segments if available
        if all_segments:
            result['segments'] = all_segments
        
        return result
    
    def get_available_models(self) -> List[str]:
        """Get list of available Whisper models."""
        return ['tiny', 'base', 'small', 'medium', 'large', 'large-v2', 'large-v3']
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the currently loaded model."""
        if not self.model:
            return {'error': 'No model loaded'}
        
        return {
            'model_name': self.config.offline_model_name,
            'device': self._resolved_device if self._resolved_device else self.config.whisper_device,
            'model_size': self.config.offline_model_name,
            'is_multilingual': True,  # All Whisper models are multilingual
        }