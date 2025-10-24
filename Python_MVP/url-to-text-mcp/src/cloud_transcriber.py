"""Cloud transcription module using OpenAI Whisper API."""

import time
from pathlib import Path
from typing import Optional, Dict, Any, List

from openai import OpenAI
from openai.types.audio import Transcription

from .config import Config


class CloudTranscriber:
    """Handles audio transcription using OpenAI Whisper API."""
    
    def __init__(self, config: Config):
        """Initialize transcriber with configuration."""
        self.config = config
        self.client = OpenAI(api_key=config.openai_api_key)
        self._validate_api_key()
    
    def _validate_api_key(self) -> None:
        """Validate that OpenAI API key is working."""
        try:
            # Test the API key by making a simple request
            self.client.models.list()
        except Exception as e:
            raise ValueError(f"Invalid OpenAI API key or API access issue: {e}")
    
    def validate_audio_file(self, audio_path: Path) -> bool:
        """
        Validate audio file for Whisper API requirements.
        
        Args:
            audio_path: Path to audio file to validate
            
        Returns:
            True if file is valid for Whisper API, False otherwise
        """
        if not audio_path.exists():
            return False
        
        # Check file size (Whisper API limit is 25MB)
        file_size = audio_path.stat().st_size
        if file_size > self.config.max_file_size_bytes:
            return False
        
        # Check if file is not empty
        if file_size == 0:
            return False
        
        # Check file extension
        if audio_path.suffix.lower() not in self.config.supported_audio_formats:
            return False
        
        return True
    
    def transcribe(
        self, 
        audio_path: Path, 
        language: Optional[str] = None,
        response_format: str = "text",
        temperature: float = 0.0,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Transcribe audio file using OpenAI Whisper API.
        
        Args:
            audio_path: Path to audio file to transcribe
            language: Language code (e.g., 'en', 'es', 'fr') or None for auto-detection
            response_format: Response format ('text', 'json', 'verbose_json', 'vtt', 'srt')
            temperature: Temperature for transcription (0.0 to 1.0)
            progress_callback: Optional callback function for progress updates
            
        Returns:
            Dictionary containing transcription result and metadata
            
        Raises:
            FileNotFoundError: If audio file doesn't exist
            ValueError: If audio file is invalid for Whisper API
            RuntimeError: If transcription fails
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        if not self.validate_audio_file(audio_path):
            raise ValueError(
                f"Audio file is invalid for Whisper API. "
                f"File size must be <= {self.config.max_file_size_mb}MB and "
                f"format must be one of: {', '.join(self.config.supported_audio_formats)}"
            )
        
        try:
            if progress_callback:
                progress_callback("Uploading audio file to OpenAI...")
            
            # Upload the audio file
            with open(audio_path, 'rb') as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=language,
                    response_format=response_format,
                    temperature=temperature
                )
            
            if progress_callback:
                progress_callback("Transcription completed")
            
            # Prepare result
            result = {
                'text': transcript.text if hasattr(transcript, 'text') else str(transcript),
                'language': language,
                'response_format': response_format,
                'temperature': temperature,
                'file_size': audio_path.stat().st_size,
                'file_name': audio_path.name,
            }
            
            # Add additional metadata if available
            if hasattr(transcript, 'language') and transcript.language:
                result['detected_language'] = transcript.language
            
            if hasattr(transcript, 'duration') and transcript.duration:
                result['duration'] = transcript.duration
            
            return result
            
        except Exception as e:
            error_msg = str(e)
            if "file size" in error_msg.lower():
                raise ValueError(f"File too large for Whisper API: {error_msg}")
            elif "rate limit" in error_msg.lower():
                raise RuntimeError(f"OpenAI API rate limit exceeded: {error_msg}")
            elif "quota" in error_msg.lower():
                raise RuntimeError(f"OpenAI API quota exceeded: {error_msg}")
            else:
                raise RuntimeError(f"Transcription failed: {error_msg}")
    
    def transcribe_with_retry(
        self, 
        audio_path: Path, 
        max_retries: int = 3,
        retry_delay: float = 1.0,
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
                if any(keyword in str(e).lower() for keyword in ['file size', 'quota', 'invalid', 'not found']):
                    raise e
                
                if attempt < max_retries:
                    if 'progress_callback' in kwargs and kwargs['progress_callback']:
                        kwargs['progress_callback'](f"Transcription attempt {attempt + 1} failed, retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
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
                
            except Exception as e:
                if progress_callback:
                    progress_callback(f"Warning: Failed to transcribe segment {i+1}: {e}")
                continue
        
        if not all_texts:
            raise RuntimeError("Failed to transcribe any audio segments")
        
        # Combine all transcriptions
        combined_text = '\n\n'.join(all_texts)
        
        return {
            'text': combined_text,
            'language': language,
            'file_size': total_size,
            'duration': total_duration,
            'segments_processed': len(all_texts),
            'total_segments': len(audio_paths),
            'success': True
        }
    
    def get_available_models(self) -> list:
        """Get list of available Whisper models."""
        try:
            models = self.client.models.list()
            whisper_models = [model for model in models.data if 'whisper' in model.id.lower()]
            return [model.id for model in whisper_models]
        except Exception:
            return ['whisper-1']  # Default fallback