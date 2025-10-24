"""Main orchestrator class for video-to-text conversion pipeline."""

import sys
from pathlib import Path
from typing import Optional, Dict, Any, Callable

from .config import Config
from .video_downloader import VideoDownloader
from .audio_extractor import AudioExtractor
from .transcriber_factory import create_transcriber


class VideoToTextConverter:
    """Main class that orchestrates the video-to-text conversion pipeline."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize converter with configuration and components."""
        self.config = config or Config()
        self.downloader = VideoDownloader(self.config)
        self.extractor = AudioExtractor(self.config)
        self.transcriber = create_transcriber(self.config)
        self.temp_files = []  # Track temporary files for cleanup
    
    def convert(
        self, 
        video_url: str, 
        language: Optional[str] = None,
        progress_callback: Optional[Callable] = None,
        keep_intermediate: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Convert video URL to text through the complete pipeline.
        
        Args:
            video_url: URL of the video to convert
            language: Language code for transcription (None for auto-detection)
            progress_callback: Optional callback function for progress updates
            keep_intermediate: Whether to keep intermediate files (overrides config)
            
        Returns:
            Dictionary containing transcription result and metadata
        """
        video_path = None
        audio_path = None
        
        try:
            # Step 1: Download video
            if progress_callback:
                progress_callback("Starting video download...")
            
            video_path = self.downloader.download_video(video_url, progress_callback)
            self.temp_files.append(video_path)
            
            if progress_callback:
                progress_callback("Video download completed")
            
            # Step 2: Extract audio
            if progress_callback:
                progress_callback("Starting audio extraction...")
            
            audio_path = self.extractor.extract_audio(video_path, progress_callback)
            self.temp_files.append(audio_path)
            
            if progress_callback:
                progress_callback("Audio extraction completed")
            
            # Step 3: Transcribe audio
            if progress_callback:
                progress_callback("Starting transcription...")
            
            # Check if audio file is too large and needs chunking (only for online mode)
            if self.config.transcription_mode == 'online' and audio_path.stat().st_size > self.config.max_file_size_bytes:
                if progress_callback:
                    progress_callback(f"Audio file is large ({audio_path.stat().st_size / (1024*1024):.1f}MB), segmenting...")
                
                # Segment the audio file
                segment_paths = self.extractor.segment_audio(audio_path, progress_callback)
                self.temp_files.extend(segment_paths)
                
                # Transcribe all segments
                transcription_result = self.transcriber.transcribe_many(
                    segment_paths,
                    language=language,
                    progress_callback=progress_callback
                )
            else:
                # Transcribe normally for smaller files
                try:
                    transcription_result = self.transcriber.transcribe_with_retry(
                        audio_path, 
                        language=language,
                        progress_callback=progress_callback
                    )
                except Exception as e:
                    # Check if this is an OOM error and we're in offline mode
                    if (self.config.transcription_mode == 'offline' and 
                        any(keyword in str(e).lower() for keyword in ['out of memory', 'oom', 'memory', 'cuda out of memory'])):
                        
                        if progress_callback:
                            progress_callback("Out of memory error detected, falling back to segmentation...")
                        
                        # Segment the audio file as fallback
                        segment_paths = self.extractor.segment_audio(audio_path, progress_callback)
                        self.temp_files.extend(segment_paths)
                        
                        # Transcribe all segments
                        transcription_result = self.transcriber.transcribe_many(
                            segment_paths,
                            language=language,
                            progress_callback=progress_callback
                        )
                    else:
                        # Re-raise the exception if it's not an OOM error or not offline mode
                        raise e
            
            if progress_callback:
                progress_callback("Transcription completed")
            
            # Add metadata about the process
            result = {
                **transcription_result,
                'video_url': video_url,
                'video_file': str(video_path),
                'audio_file': str(audio_path),
                'success': True,
            }
            
            # Add video info if available
            try:
                video_info = self.downloader.get_video_info(video_url)
                result['video_info'] = video_info
            except Exception:
                pass  # Video info is optional
            
            # Add audio info if available
            try:
                audio_info = self.extractor.get_audio_info(audio_path)
                result['audio_info'] = audio_info
            except Exception:
                pass  # Audio info is optional
            
            return result
            
        except Exception as e:
            # Clean up on error
            self._cleanup_temp_files()
            raise e
        
        finally:
            # Clean up intermediate files if not keeping them
            if keep_intermediate is None:
                keep_intermediate = self.config.keep_intermediate_files
            
            if not keep_intermediate:
                self._cleanup_temp_files()
    
    def _cleanup_temp_files(self) -> None:
        """Clean up temporary files."""
        self.config.cleanup_temp_files(self.temp_files)
        self.temp_files.clear()
    
    def get_video_info(self, video_url: str) -> Dict[str, Any]:
        """
        Get information about a video without downloading it.
        
        Args:
            video_url: URL of the video to get info for
            
        Returns:
            Dictionary containing video information
        """
        return self.downloader.get_video_info(video_url)
    
    def validate_url(self, video_url: str) -> bool:
        """
        Validate if a video URL is supported.
        
        Args:
            video_url: URL to validate
            
        Returns:
            True if URL is supported, False otherwise
        """
        return self.downloader.validate_url(video_url)
    
    def estimate_processing_time(self, video_url: str) -> Dict[str, Any]:
        """
        Estimate processing time for a video URL.
        
        Args:
            video_url: URL of the video to estimate for
            
        Returns:
            Dictionary containing time estimates
        """
        try:
            video_info = self.get_video_info(video_url)
            duration = video_info.get('duration', 0)
            
            # Rough estimates based on typical processing speeds
            download_time = max(10, duration * 0.1)  # 10% of video duration, minimum 10s
            extraction_time = max(5, duration * 0.05)  # 5% of video duration, minimum 5s
            transcription_time = max(30, duration * 0.5)  # 50% of video duration, minimum 30s
            
            total_time = download_time + extraction_time + transcription_time
            
            return {
                'video_duration': duration,
                'estimated_download_time': download_time,
                'estimated_extraction_time': extraction_time,
                'estimated_transcription_time': transcription_time,
                'estimated_total_time': total_time,
                'note': 'Estimates are approximate and may vary based on network speed and system performance'
            }
        except Exception as e:
            return {
                'error': f'Could not estimate processing time: {e}',
                'note': 'Unable to get video information'
            }
