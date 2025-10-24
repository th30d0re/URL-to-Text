#!/usr/bin/env python3
"""Main CLI application for video-to-text conversion."""

import sys
from pathlib import Path
from typing import Optional

import click

from src.config import Config
from src.video_to_text import VideoToTextConverter


def progress_callback(message: str) -> None:
    """Default progress callback that prints to stdout."""
    click.echo(f"  {message}")


@click.command()
@click.argument('video_url', type=str)
@click.option('--output', '-o', type=click.Path(), help='Output file to save transcription')
@click.option('--language', '-l', type=str, help='Language code for transcription (e.g., en, es, fr)')
@click.option('--keep-files', '-k', is_flag=True, help='Keep intermediate video and audio files')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--info-only', is_flag=True, help='Show video information without processing')
@click.option('--estimate-time', is_flag=True, help='Estimate processing time without processing')
@click.option('--offline', is_flag=True, help='Use offline Whisper model instead of OpenAI API')
@click.option('--model', type=click.Choice(['tiny', 'base', 'small', 'medium', 'large', 'large-v2', 'large-v3']), 
              default='base', help='Whisper model size for offline mode (default: base)')
@click.option('--device', type=click.Choice(['cpu', 'cuda', 'auto']), 
              default='auto', help='Device for offline Whisper inference (default: auto)')
def main(
    video_url: str,
    output: Optional[str],
    language: Optional[str],
    keep_files: bool,
    verbose: bool,
    info_only: bool,
    estimate_time: bool,
    offline: bool,
    model: str,
    device: str
):
    """
    Convert video URL to text using OpenAI Whisper API or offline Whisper models.
    
    VIDEO_URL: URL of the video to convert (YouTube, Vimeo, etc.)
    
    Examples:
        # Online mode (OpenAI API)
        python main.py "https://www.youtube.com/watch?v=example"
        python main.py "https://vimeo.com/123456789" --output transcript.txt
        
        # Offline mode (local Whisper)
        python main.py "https://youtube.com/watch?v=example" --offline
        python main.py "https://youtube.com/watch?v=example" --offline --model large --device cuda
        python main.py "https://youtube.com/watch?v=example" --offline --model base --language en
    """
    try:
        # Apply offline overrides before constructing Config
        if offline:
            import os
            os.environ['TRANSCRIPTION_MODE'] = 'offline'
            os.environ['OFFLINE_MODEL_NAME'] = model
            os.environ['WHISPER_DEVICE'] = device
            if verbose:
                click.echo(f"Using offline mode with model '{model}' on device '{device}'")
        
        # Initialize configuration
        try:
            config = Config()
        except ValueError as e:
            click.echo(f"Configuration error: {e}", err=True)
            if not offline:
                click.echo("Please check your .env file and ensure OPENAI_API_KEY is set.", err=True)
            else:
                click.echo("Please check your .env file and ensure TRANSCRIPTION_MODE=offline is set.", err=True)
            sys.exit(1)
        
        # Apply additional CLI overrides if not offline
        if not offline:
            if config.transcription_mode == 'offline':
                click.echo("Warning: Configuration is set to offline mode, but --offline flag not used.")
                click.echo("Use --offline flag to confirm offline mode or set TRANSCRIPTION_MODE=online in .env")
        
        # Initialize converter
        try:
            converter = VideoToTextConverter(config)
        except ImportError as e:
            if offline:
                click.echo(f"Error: {e}", err=True)
                click.echo("Install offline dependencies with: pip install openai-whisper torch torchaudio", err=True)
            else:
                click.echo(f"Error: {e}", err=True)
            sys.exit(1)
        except Exception as e:
            click.echo(f"Error initializing converter: {e}", err=True)
            if offline:
                click.echo("This might be due to missing offline dependencies or configuration issues.", err=True)
            sys.exit(1)
        
        # Handle info-only mode
        if info_only:
            try:
                video_info = converter.get_video_info(video_url)
                click.echo("Video Information:")
                click.echo(f"  Title: {video_info.get('title', 'Unknown')}")
                click.echo(f"  Duration: {video_info.get('duration', 0)} seconds")
                click.echo(f"  Uploader: {video_info.get('uploader', 'Unknown')}")
                click.echo(f"  Views: {video_info.get('view_count', 0):,}")
                if video_info.get('description'):
                    click.echo(f"  Description: {video_info['description']}")
            except Exception as e:
                click.echo(f"Error getting video info: {e}", err=True)
                sys.exit(1)
            return
        
        # Handle time estimation mode
        if estimate_time:
            try:
                estimates = converter.estimate_processing_time(video_url)
                if 'error' in estimates:
                    click.echo(f"Error: {estimates['error']}", err=True)
                    sys.exit(1)
                
                click.echo("Processing Time Estimates:")
                click.echo(f"  Video Duration: {estimates['video_duration']} seconds")
                click.echo(f"  Download Time: ~{estimates['estimated_download_time']:.1f} seconds")
                click.echo(f"  Extraction Time: ~{estimates['estimated_extraction_time']:.1f} seconds")
                click.echo(f"  Transcription Time: ~{estimates['estimated_transcription_time']:.1f} seconds")
                click.echo(f"  Total Time: ~{estimates['estimated_total_time']:.1f} seconds")
                click.echo(f"\nNote: {estimates['note']}")
            except Exception as e:
                click.echo(f"Error estimating processing time: {e}", err=True)
                sys.exit(1)
            return
        
        # Main processing
        click.echo(f"Converting video to text: {video_url}")
        if language:
            click.echo(f"Language: {language}")
        if keep_files:
            click.echo("Keeping intermediate files")
        
        # Show mode information
        if config.transcription_mode == 'offline':
            click.echo(f"Mode: Offline (model: {config.offline_model_name}, device: {config.whisper_device})")
            if verbose:
                click.echo("Note: Model will be downloaded on first use if not already cached")
        else:
            click.echo("Mode: Online (OpenAI API)")
        
        try:
            # Convert video to text
            result = converter.convert(
                video_url=video_url,
                language=language,
                progress_callback=progress_callback if verbose else None,
                keep_intermediate=keep_files
            )
            
            if not result.get('success', False):
                click.echo("Error: Conversion failed", err=True)
                sys.exit(1)
            
            # Display results
            click.echo("\n" + "="*50)
            click.echo("TRANSCRIPTION RESULT")
            click.echo("="*50)
            
            if verbose and 'video_info' in result:
                video_info = result['video_info']
                click.echo(f"Video: {video_info.get('title', 'Unknown')}")
                click.echo(f"Duration: {video_info.get('duration', 0)} seconds")
                click.echo()
            
            if verbose and 'audio_info' in result:
                audio_info = result['audio_info']
                click.echo(f"Audio: {audio_info.get('codec', 'unknown')} codec, "
                          f"{audio_info.get('sample_rate', 0)} Hz, "
                          f"{audio_info.get('channels', 0)} channels")
                click.echo(f"File size: {audio_info.get('size_bytes', 0):,} bytes")
                click.echo()
            
            if 'detected_language' in result:
                click.echo(f"Detected language: {result['detected_language']}")
                click.echo()
            
            # Display or save transcription
            transcription_text = result.get('text', '')
            
            if output:
                output_path = Path(output)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(transcription_text, encoding='utf-8')
                click.echo(f"Transcription saved to: {output_path}")
            else:
                click.echo(transcription_text)
            
            # Cleanup message
            if not keep_files and verbose:
                click.echo("\nTemporary files cleaned up.")
            
        except KeyboardInterrupt:
            click.echo("\nOperation cancelled by user.", err=True)
            sys.exit(1)
        except Exception as e:
            error_msg = str(e)
            click.echo(f"Error during conversion: {error_msg}", err=True)
            
            # Provide specific guidance for offline mode errors
            if config.transcription_mode == 'offline':
                if "out of memory" in error_msg.lower():
                    click.echo("Try using a smaller model (tiny, base, small) or free up memory.", err=True)
                elif "cuda" in error_msg.lower():
                    click.echo("Try using CPU mode by setting --device cpu", err=True)
                elif "model" in error_msg.lower() and "load" in error_msg.lower():
                    click.echo("Model download may have failed. Check your internet connection.", err=True)
            
            if verbose:
                import traceback
                click.echo("Full error details:", err=True)
                click.echo(traceback.format_exc(), err=True)
            sys.exit(1)
    
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
