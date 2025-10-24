"""MCP server entrypoint for the URL-to-Text application."""

import asyncio
import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

from src.config import Config
from src.video_to_text import VideoToTextConverter
from src.video_downloader import VideoDownloader
from yt_dlp.utils import DownloadError


LOGGER_NAME = "url_to_text_mcp"
SERVER_NAME = "url-to-text"


def configure_logging():
    """Configure application logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )
    return logging.getLogger(LOGGER_NAME)


def read_secret(source):
    """Read a secret value from a Docker secret file path."""
    path = Path(source)
    try:
        return path.read_text(encoding="utf-8").strip()
    except Exception as exc:
        raise RuntimeError(f"Unable to read secret from {path}") from exc


def load_env_from_secrets():
    """Populate environment variables from Docker secret files when present."""
    mappings = {
        "OPENAI_API_KEY": "OPENAI_API_KEY_FILE",
        "TRANSCRIPTION_MODE": "TRANSCRIPTION_MODE_FILE",
        "OFFLINE_MODEL_NAME": "OFFLINE_MODEL_NAME_FILE",
        "WHISPER_DEVICE": "WHISPER_DEVICE_FILE",
    }

    for target, file_key in mappings.items():
        file_path = os.environ.get(file_key, "")
        if not file_path:
            continue

        try:
            secret_value = read_secret(file_path)
        except Exception as exc:  # pragma: no cover - best effort logging
            LOGGER.warning(
                "Failed to load Docker secret for %s from %s: %s",
                target,
                file_path,
                exc,
            )
            continue

        if secret_value:
            os.environ[target] = secret_value
            LOGGER.info("Loaded %s from Docker secret", target)


LOGGER = configure_logging()
MCP_SERVER = FastMCP(SERVER_NAME)
SERVER_STATE = {
    "config": None,
    "converter": None,
    "config_error": None,
    "converter_error": None,
}


def get_converter(force_refresh: bool = False) -> Optional[VideoToTextConverter]:
    """Return a cached VideoToTextConverter, creating it on demand."""
    if not force_refresh and SERVER_STATE.get("converter") is not None:
        return SERVER_STATE["converter"]

    config = SERVER_STATE.get("config")
    if config is None:
        if SERVER_STATE.get("config_error") is None:
            LOGGER.warning(
                "Configuration not available; converter cannot be created yet",
            )
        return None

    try:
        converter = VideoToTextConverter(config)
    except Exception as exc:  # pragma: no cover - defensive guard
        SERVER_STATE["converter"] = None
        SERVER_STATE["converter_error"] = str(exc)
        LOGGER.error("Failed to initialize converter: %s", exc, exc_info=True)
        return None

    SERVER_STATE["converter"] = converter
    SERVER_STATE["converter_error"] = None
    LOGGER.info("Initialized converter in %s mode", config.transcription_mode)
    return converter


@MCP_SERVER.tool()
async def transcribe_video_url(video_url: str = "", language: str = "", transcription_mode: str = "", model_size: str = "") -> str:
    """Transcribe video from URL to text using online or offline transcription."""
    if not video_url.strip():
        return "❌ Error: video_url is required"
    
    LOGGER.info(f"Starting transcription for URL: {video_url}")
    
    # Start timing
    start_time = time.time()
    
    try:
        # Determine if we need to create a fresh converter for overrides
        has_overrides = bool(transcription_mode.strip() or model_size.strip())
        used_mode = None
        
        if has_overrides:
            # Create a fresh config for this request with overrides
            base_config = SERVER_STATE.get("config")
            if base_config is None:
                error_msg = SERVER_STATE.get("config_error", "configuration not available")
                return f"❌ Error: Configuration unavailable - {error_msg}"
            
            # Clone the config and apply overrides
            from copy import deepcopy
            request_config = deepcopy(base_config)
            
            # Handle transcription mode override
            if transcription_mode.strip():
                if transcription_mode.strip().lower() not in ['online', 'offline']:
                    return "❌ Error: transcription_mode must be 'online' or 'offline'"
                
                request_config.transcription_mode = transcription_mode.strip().lower()
                used_mode = request_config.transcription_mode
                LOGGER.info(f"Using override transcription mode: {request_config.transcription_mode}")
            
            # Handle model size override (forces offline mode)
            if model_size.strip():
                valid_models = ['tiny', 'base', 'small', 'medium', 'large', 'large-v2', 'large-v3']
                if model_size.strip().lower() not in valid_models:
                    return f"❌ Error: model_size must be one of: {', '.join(valid_models)}"
                
                request_config.transcription_mode = 'offline'
                request_config.offline_model_name = model_size.strip().lower()
                used_mode = 'offline'
                LOGGER.info(f"Using override model size: {model_size} (forced offline mode)")
            
            # Create fresh converter for this request
            try:
                converter = VideoToTextConverter(request_config)
            except Exception as exc:
                LOGGER.error("Failed to create converter with overrides: %s", exc, exc_info=True)
                return f"❌ Error: Failed to create converter with overrides - {str(exc)}"
        else:
            # Use cached converter when no overrides
            converter = get_converter()
            if converter is None:
                error_msg = SERVER_STATE.get("converter_error", "converter not available")
                return f"❌ Error: Converter unavailable - {error_msg}"
            used_mode = converter.config.transcription_mode
        
        # Progress callback for logging
        def progress_callback(message: str) -> None:
            LOGGER.info(f"Progress: {message}")
        
        # Perform transcription using asyncio.to_thread to avoid blocking
        result = await asyncio.to_thread(
            converter.convert,
            video_url=video_url.strip(),
            language=language.strip() if language.strip() else None,
            progress_callback=progress_callback
        )
        
        # Calculate processing time
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Format response
        if result.get('success', False):
            transcription_text = result.get('text', '')
            video_info = result.get('video_info', {})
            audio_info = result.get('audio_info', {})
            
            response_parts = [
                "✅ Transcription completed successfully!",
                "",
                "📝 Transcription:",
                transcription_text,
                "",
                "📊 Metadata:"
            ]
            
            if video_info:
                response_parts.extend([
                    f"- Video Title: {video_info.get('title', 'Unknown')}",
                    f"- Duration: {video_info.get('duration', 'Unknown')} seconds",
                    f"- Uploader: {video_info.get('uploader', 'Unknown')}"
                ])
            
            if audio_info:
                response_parts.extend([
                    f"- Audio Duration: {audio_info.get('duration', 'Unknown')} seconds",
                    f"- Sample Rate: {audio_info.get('sample_rate', 'Unknown')} Hz"
                ])
            
            response_parts.extend([
                f"- Processing Mode: {used_mode}",
                f"- Language: {result.get('language', 'Auto-detected')}",
                f"- Video URL: {video_url}",
                f"- ⏱️ Total Time: {processing_time:.1f}s"
            ])
            
            return "\n".join(response_parts)
        else:
            return f"❌ Error: Transcription failed - {result.get('error', 'Unknown error')}"
            
    except Exception as e:
        LOGGER.error(f"Transcription error: {e}", exc_info=True)
        return f"❌ Error: {str(e)}"


@MCP_SERVER.tool()
async def get_video_info(video_url: str = "") -> str:
    """Get video information without downloading the video."""
    if not video_url.strip():
        return "❌ Error: video_url is required"
    
    LOGGER.info(f"Getting video info for URL: {video_url}")
    
    try:
        converter = get_converter()
        if converter is None:
            error_msg = SERVER_STATE.get("converter_error", "converter not available")
            return f"❌ Error: Converter unavailable - {error_msg}"
        
        video_info = await asyncio.to_thread(converter.get_video_info, video_url.strip())
        
        if not video_info:
            return "❌ Error: Could not retrieve video information"
        
        desc = video_info.get('description') or 'No description available'
        
        response_parts = [
            "📊 Video Information:",
            "",
            f"Title: {video_info.get('title', 'Unknown')}",
            f"Duration: {video_info.get('duration', 'Unknown')} seconds",
            f"Uploader: {video_info.get('uploader', 'Unknown')}",
            f"View Count: {video_info.get('view_count', 'Unknown')}",
            f"Description: {desc}",
            f"URL: {video_url}"
        ]
        
        return "\n".join(response_parts)
        
    except DownloadError as e:
        LOGGER.error(f"Download error getting video info: {e}", exc_info=True)
        return f"❌ Error: Failed to access video - {str(e)}"
    except Exception as e:
        LOGGER.error(f"Error getting video info: {e}", exc_info=True)
        return f"❌ Error: {str(e)}"


@MCP_SERVER.tool()
async def validate_video_url(video_url: str = "") -> str:
    """Check if a video URL is supported by the platform."""
    if not video_url.strip():
        return "❌ Error: video_url is required"
    
    LOGGER.info(f"Validating video URL: {video_url}")
    
    try:
        converter = get_converter()
        if converter is None:
            error_msg = SERVER_STATE.get("converter_error", "converter not available")
            return f"❌ Error: Converter unavailable - {error_msg}"
        
        is_valid = await asyncio.to_thread(converter.validate_url, video_url.strip())
        
        if is_valid:
            return f"""## Video URL Validation

**Input URL:** {video_url}

**Status:** ✅ URL is valid and supported by the platform"""
        else:
            return f"""## Video URL Validation

**Input URL:** {video_url}

**Status:** ❌ URL is not supported. Supported platforms include YouTube, Vimeo, and other major video platforms."""
        
    except Exception as e:
        LOGGER.error(f"Error validating video URL: {e}", exc_info=True)
        return f"❌ Error: {str(e)}"


@MCP_SERVER.tool()
async def estimate_processing_time(video_url: str = "") -> str:
    """Estimate processing time for video transcription."""
    if not video_url.strip():
        return "❌ Error: video_url is required"
    
    LOGGER.info(f"Estimating processing time for URL: {video_url}")
    
    try:
        converter = get_converter()
        if converter is None:
            error_msg = SERVER_STATE.get("converter_error", "converter not available")
            return f"❌ Error: Converter unavailable - {error_msg}"
        
        estimates = await asyncio.to_thread(converter.estimate_processing_time, video_url.strip())
        
        if not estimates:
            return "❌ Error: Could not estimate processing time for this video"
        
        # Handle error dicts from converter explicitly
        if isinstance(estimates, dict) and estimates.get('error'):
            return f"❌ Error: {estimates['error']}"
        
        response_parts = [
            "⏱️ Processing Time Estimates:",
            "",
            f"Video Duration: {estimates.get('video_duration', 'Unknown')} seconds",
            f"Download Time: {estimates.get('estimated_download_time', 'Unknown')} seconds",
            f"Audio Extraction: {estimates.get('estimated_extraction_time', 'Unknown')} seconds",
            f"Transcription: {estimates.get('estimated_transcription_time', 'Unknown')} seconds",
            f"Total Estimated Time: {estimates.get('estimated_total_time', 'Unknown')} seconds",
            "",
            "Note: These are rough estimates based on video duration and system performance. Actual times may vary depending on network speed and system load."
        ]
        
        return "\n".join(response_parts)
        
    except DownloadError as e:
        LOGGER.error(f"Download error estimating processing time: {e}", exc_info=True)
        return f"❌ Error: Failed to access video for estimation - {str(e)}"
    except Exception as e:
        LOGGER.error(f"Error estimating processing time: {e}", exc_info=True)
        return f"❌ Error: {str(e)}"


@MCP_SERVER.tool()
async def list_available_models() -> str:
    """List available Whisper models with capabilities and system requirements."""
    LOGGER.info("Listing available Whisper models")
    
    try:
        converter = get_converter()
        
        # If converter is unavailable, return static info instead of error
        if converter is None:
            LOGGER.warning("Converter unavailable, returning static model information")
            return _get_static_model_info()
        
        # Get current configuration
        config = converter.config
        current_mode = config.transcription_mode
        current_model = config.offline_model_name if current_mode == 'offline' else 'whisper-1'
        current_device = config.whisper_device if current_mode == 'offline' else 'cloud'
        
        response_parts = ["🤖 Available Whisper Models", ""]
        
        # Online section - always show
        response_parts.extend(await _get_online_models_section(converter, current_mode, current_model, current_device))
        
        response_parts.append("")  # Add spacing between sections
        
        # Offline section - always show
        response_parts.extend(await _get_offline_models_section(converter, current_mode, current_model, current_device))
        
        return "\n".join(response_parts)
        
    except Exception as e:
        LOGGER.error(f"Error listing available models: {e}", exc_info=True)
        return f"❌ Error: {str(e)}"


def _get_static_model_info() -> str:
    """Return static model information when converter is unavailable."""
    response_parts = [
        "🤖 Available Whisper Models (Static Information)",
        "",
        "**Note:** Converter unavailable - showing static model information",
        "",
        "## 🌐 Online Models",
        "",
        "**Available Models:**",
        "• **whisper-1** - OpenAI Whisper API model",
        "",
        "**Capabilities:**",
        "• High accuracy transcription",
        "• Multilingual support (99+ languages)",
        "• Automatic language detection",
        "• No local storage required",
        "• Handles files up to 25MB",
        "",
        "**Requirements:**",
        "• Valid OpenAI API key",
        "• Internet connection",
        "• No local GPU/CPU requirements",
        "",
        "**Performance:**",
        "• Fast processing (typically 1-2x real-time)",
        "• Consistent quality across all models",
        "• No local resource usage",
        "",
        "## 🏠 Offline Models",
        "",
        "**Available Models:**",
        ""
    ]
    
    # Model specifications
    model_specs = {
        'tiny': {'size': '39 MB', 'memory': '~1 GB', 'speed': '~32x', 'accuracy': 'Low'},
        'base': {'size': '74 MB', 'memory': '~1 GB', 'speed': '~16x', 'accuracy': 'Low-Medium'},
        'small': {'size': '244 MB', 'memory': '~2 GB', 'speed': '~6x', 'accuracy': 'Medium'},
        'medium': {'size': '769 MB', 'memory': '~5 GB', 'speed': '~2x', 'accuracy': 'High'},
        'large': {'size': '1550 MB', 'memory': '~10 GB', 'speed': '~1x', 'accuracy': 'Very High'},
        'large-v2': {'size': '1550 MB', 'memory': '~10 GB', 'speed': '~1x', 'accuracy': 'Very High'},
        'large-v3': {'size': '1550 MB', 'memory': '~10 GB', 'speed': '~1x', 'accuracy': 'Very High'}
    }
    
    for model in ['tiny', 'base', 'small', 'medium', 'large', 'large-v2', 'large-v3']:
        specs = model_specs.get(model, {})
        size = specs.get('size', 'Unknown')
        memory = specs.get('memory', 'Unknown')
        speed = specs.get('speed', 'Unknown')
        accuracy = specs.get('accuracy', 'Unknown')
        
        response_parts.append(f"• **{model}**")
        response_parts.append(f"  - Size: {size}")
        response_parts.append(f"  - Memory: {memory}")
        response_parts.append(f"  - Speed: {speed} real-time")
        response_parts.append(f"  - Accuracy: {accuracy}")
        response_parts.append("")
    
    response_parts.extend([
        "**Device Compatibility:**",
        "• **CPU**: All models supported",
        "• **CUDA**: Recommended for medium/large models",
        "• **Apple Silicon**: Optimized performance",
        "• **Memory**: Varies by model (see above)",
        "",
        "**Performance Recommendations:**",
        "• **tiny/base**: Fast processing, good for testing",
        "• **small**: Balanced speed/accuracy for most use cases",
        "• **medium**: High accuracy, requires more resources",
        "• **large/large-v2/large-v3**: Best accuracy, needs significant resources",
        "",
        "**System Requirements:**",
        "• Python 3.8+",
        "• PyTorch (CPU or CUDA)",
        "• FFmpeg for audio processing",
        "• Sufficient disk space for model downloads",
        "• Adequate RAM for model loading"
    ])
    
    return "\n".join(response_parts)


async def _get_online_models_section(converter, current_mode, current_model, current_device) -> list:
    """Get online models section."""
    response_parts = [
        "## 🌐 Online Models",
        "",
        f"**Current Mode:** {current_mode}",
        f"**Active Model:** {current_model}",
        f"**Device:** {current_device}",
        ""
    ]
    
    # Get online models
    if current_mode == 'online':
        try:
            available_models = await asyncio.to_thread(converter.transcriber.get_available_models)
        except Exception as e:
            LOGGER.warning(f"Could not fetch online models: {e}")
            available_models = ['whisper-1']  # Fallback
    else:
        # Not in online mode, try to get models from CloudTranscriber
        try:
            from src.cloud_transcriber import CloudTranscriber
            from src.config import Config
            temp_config = Config()
            temp_transcriber = CloudTranscriber(temp_config)
            available_models = temp_transcriber.get_available_models()
        except Exception as e:
            LOGGER.warning(f"Could not instantiate CloudTranscriber: {e}")
            available_models = ['whisper-1']  # Fallback
    
    response_parts.extend([
        "**Available Models:**",
        ""
    ])
    
    for model in available_models:
        response_parts.append(f"• **{model}** - OpenAI Whisper API model")
    
    response_parts.extend([
        "",
        "**Capabilities:**",
        "• High accuracy transcription",
        "• Multilingual support (99+ languages)",
        "• Automatic language detection",
        "• No local storage required",
        "• Handles files up to 25MB",
        "",
        "**Requirements:**",
        "• Valid OpenAI API key",
        "• Internet connection",
        "• No local GPU/CPU requirements",
        "",
        "**Performance:**",
        "• Fast processing (typically 1-2x real-time)",
        "• Consistent quality across all models",
        "• No local resource usage"
    ])
    
    return response_parts


async def _get_offline_models_section(converter, current_mode, current_model, current_device) -> list:
    """Get offline models section."""
    response_parts = [
        "## 🏠 Offline Models",
        "",
        f"**Current Mode:** {current_mode}",
        f"**Active Model:** {current_model}",
        f"**Device:** {current_device}",
        ""
    ]
    
    # Get offline models
    if current_mode == 'offline':
        try:
            available_models = await asyncio.to_thread(converter.transcriber.get_available_models)
            model_info = await asyncio.to_thread(converter.transcriber.get_model_info)
        except Exception as e:
            LOGGER.warning(f"Could not fetch offline models: {e}")
            available_models = ['tiny', 'base', 'small', 'medium', 'large', 'large-v2', 'large-v3']
            model_info = {'error': 'Could not get model info'}
    else:
        # Not in offline mode, try to get models from OfflineTranscriber
        try:
            from src.offline_transcriber import OfflineTranscriber
            from src.config import Config
            temp_config = Config()
            temp_transcriber = OfflineTranscriber(temp_config)
            available_models = temp_transcriber.get_available_models()
            model_info = temp_transcriber.get_model_info()
        except Exception as e:
            LOGGER.warning(f"Could not instantiate OfflineTranscriber: {e}")
            available_models = ['tiny', 'base', 'small', 'medium', 'large', 'large-v2', 'large-v3']
            model_info = {'error': 'Could not get model info'}
    
    response_parts.extend([
        "**Available Models:**",
        ""
    ])
    
    # Model specifications
    model_specs = {
        'tiny': {'size': '39 MB', 'memory': '~1 GB', 'speed': '~32x', 'accuracy': 'Low'},
        'base': {'size': '74 MB', 'memory': '~1 GB', 'speed': '~16x', 'accuracy': 'Low-Medium'},
        'small': {'size': '244 MB', 'memory': '~2 GB', 'speed': '~6x', 'accuracy': 'Medium'},
        'medium': {'size': '769 MB', 'memory': '~5 GB', 'speed': '~2x', 'accuracy': 'High'},
        'large': {'size': '1550 MB', 'memory': '~10 GB', 'speed': '~1x', 'accuracy': 'Very High'},
        'large-v2': {'size': '1550 MB', 'memory': '~10 GB', 'speed': '~1x', 'accuracy': 'Very High'},
        'large-v3': {'size': '1550 MB', 'memory': '~10 GB', 'speed': '~1x', 'accuracy': 'Very High'}
    }
    
    for model in available_models:
        specs = model_specs.get(model, {})
        size = specs.get('size', 'Unknown')
        memory = specs.get('memory', 'Unknown')
        speed = specs.get('speed', 'Unknown')
        accuracy = specs.get('accuracy', 'Unknown')
        
        current_indicator = " (Current)" if model == current_model else ""
        response_parts.append(f"• **{model}**{current_indicator}")
        response_parts.append(f"  - Size: {size}")
        response_parts.append(f"  - Memory: {memory}")
        response_parts.append(f"  - Speed: {speed} real-time")
        response_parts.append(f"  - Accuracy: {accuracy}")
        response_parts.append("")
    
    # Add Current Model Details subsection if model_info is available
    if model_info and not model_info.get('error'):
        response_parts.extend([
            "**Current Model Details:**",
            ""
        ])
        
        if model_info.get('model_name'):
            response_parts.append(f"• **Model Name:** {model_info.get('model_name')}")
        
        # Use resolved device if available, otherwise fall back to config
        device_info = model_info.get('device', current_device)
        response_parts.append(f"• **Device:** {device_info}")
        
        # Add any other available keys
        for key, value in model_info.items():
            if key not in ['model_name', 'device', 'error']:
                response_parts.append(f"• **{key.replace('_', ' ').title()}:** {value}")
        
        response_parts.append("")
    
    response_parts.extend([
        "**Device Compatibility:**",
        "• **CPU**: All models supported",
        "• **CUDA**: Recommended for medium/large models",
        "• **Apple Silicon**: Optimized performance",
        "• **Memory**: Varies by model (see above)",
        "",
        "**Performance Recommendations:**",
        "• **tiny/base**: Fast processing, good for testing",
        "• **small**: Balanced speed/accuracy for most use cases",
        "• **medium**: High accuracy, requires more resources",
        "• **large/large-v2/large-v3**: Best accuracy, needs significant resources",
        "",
        "**System Requirements:**",
        "• Python 3.8+",
        "• PyTorch (CPU or CUDA)",
        "• FFmpeg for audio processing",
        "• Sufficient disk space for model downloads",
        "• Adequate RAM for model loading"
    ])
    
    return response_parts


@MCP_SERVER.tool()
async def health_check() -> str:
    """Return server health information."""
    config = SERVER_STATE.get("config")
    config_error = SERVER_STATE.get("config_error")
    converter_error = SERVER_STATE.get("converter_error")
    status = "ready"
    reasons = []

    if config is None:
        status = "degraded"
        reasons.append(
            f"configuration unavailable: {config_error or 'not initialized'}"
        )
    else:
        if not config.validate_api_key():
            status = "degraded"
            reasons.append("OpenAI API key missing or invalid")

        converter = SERVER_STATE.get("converter")
        if converter is None and converter_error is None:
            converter = get_converter()
            converter_error = SERVER_STATE.get("converter_error")

        if converter is None:
            status = "degraded"
            reasons.append(
                f"converter unavailable: {converter_error or 'not yet initialized'}"
            )

    details = [
        f"status: {status}",
        f"mode: {config.transcription_mode if config else 'unknown'}",
    ]

    if reasons:
        details.append("issues:")
        details.extend(f"- {reason}" for reason in reasons)
    else:
        details.append("issues: none detected")

    return "\n".join(details)


def main():
    """Entry point for the MCP server."""
    LOGGER.info("Starting %s server initialization", SERVER_NAME)

    load_env_from_secrets()
    try:
        config = Config()
    except Exception as exc:  # pragma: no cover - configuration errors at startup
        SERVER_STATE["config"] = None
        SERVER_STATE["config_error"] = str(exc)
        LOGGER.error("Configuration error: %s", exc, exc_info=True)
    else:
        SERVER_STATE["config"] = config
        SERVER_STATE["config_error"] = None
        SERVER_STATE["converter"] = None
        SERVER_STATE["converter_error"] = None
        LOGGER.info("Loaded configuration for %s mode", config.transcription_mode)

    try:
        MCP_SERVER.run(transport="stdio")
    except Exception as exc:
        LOGGER.error("Server runtime error: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
