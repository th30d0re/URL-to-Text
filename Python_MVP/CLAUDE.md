# URL-to-Text MCP Server - Implementation Guide

## Implementation Overview

The URL-to-Text MCP server is built using FastMCP framework and provides a Docker-containerized interface to the existing VideoToTextConverter architecture. The server acts as a bridge between Claude Desktop and the comprehensive video transcription system, enabling AI assistants to process video content from multiple platforms.

### Architecture Components

- **FastMCP Server**: Handles MCP protocol communication and tool registration
- **Docker Containerization**: Ensures consistent deployment and dependency management
- **VideoToTextConverter Integration**: Leverages existing robust video processing pipeline
- **Dual Transcription Modes**: Supports both OpenAI API and local Whisper processing
- **Multi-platform Support**: Handles YouTube, Vimeo, TikTok, Instagram, and other platforms

## Tool Specifications

### transcribe_video_url

**Purpose**: Convert video URLs to text transcriptions with configurable quality settings.

**Parameters**:
- `url` (string, required): Video URL to transcribe
- `model` (string, optional): Whisper model name (default: "base")
- `language` (string, optional): Target language code (default: "auto")
- `translation` (boolean, optional): Enable translation to English (default: false)

**Return Format**:
```
✅ Transcription complete
Title: Video Title
Duration: 5:00 (300s)
Language: en
Model: base (online)
⏱️ Processing time: 45.2s

--- Transcript ---
Full transcribed text...
```

**Error Handling**:
- Invalid URL format: Returns validation error with supported platforms
- Network errors: Provides retry suggestions and timeout information
- API errors: Shows specific error messages and troubleshooting steps
- File system errors: Indicates disk space or permission issues

### get_video_info

**Purpose**: Retrieve video metadata without downloading or transcribing.

**Parameters**:
- `url` (string, required): Video URL to analyze

**Return Format**:
```
📊 Video Information
Title: Video Title
Duration: 5:00 (300s)
Platform: youtube
Uploader: Channel Name
Views: 1,000,000
Upload Date: 2024-01-01
Thumbnail: https://...

Description:
Video description...
```

**Error Handling**:
- Unsupported platform: Lists supported platforms
- Private/restricted content: Explains access limitations
- Network timeouts: Provides retry suggestions

### validate_video_url

**Purpose**: Check if a video URL is supported and accessible.

**Parameters**:
- `url` (string, required): URL to validate

**Return Format**:
```
✅ URL Validation Results
Valid: Yes
Supported: Yes
Platform: youtube
Accessible: Yes
Estimated Duration: 5:00 (300s)
```

**Error Handling**:
- Malformed URLs: Returns specific format requirements
- Unsupported platforms: Lists supported platforms
- Access issues: Explains authentication or region restrictions

### estimate_processing_time

**Purpose**: Calculate estimated transcription time based on video characteristics.

**Parameters**:
- `url` (string, required): Video URL to analyze
- `model` (string, optional): Whisper model name (default: "base")
- `mode` (string, optional): Processing mode - "online" or "offline" (default: "online")

**Return Format**:
```
⏱️ Processing Time Estimate
Video Duration: 5:00 (300s)
Model: base
Mode: online
Total Estimated Time: 2:00 (120s)

Breakdown:
- Download: 0:30 (30s)
- Transcription: 1:30 (90s)
```

**Error Handling**:
- Invalid model: Lists available models
- Network issues: Provides offline mode suggestions
- Duration estimation errors: Uses fallback calculations

### list_available_models

**Purpose**: Display all available Whisper models with their capabilities.

**Parameters**: None

**Return Format**:
```
🤖 Available Whisper Models

tiny (39 MB)
- Speed: Fastest
- Accuracy: Lowest
- Languages: Multilingual
- Best for: Quick processing

base (74 MB)
- Speed: Fast
- Accuracy: Good
- Languages: Multilingual
- Best for: Balanced performance

Current Mode: online
Default Model: base
```

**Error Handling**:
- Model loading errors: Provides fallback model information
- System resource issues: Suggests appropriate model selection

## Configuration Management

### MCP Toolkit Secret Integration

The MCP server uses MCP Toolkit secrets for secure configuration management. Secrets are injected by the MCP Gateway based on the catalog and registry configuration:

```python
# Secret loading pattern for MCP Toolkit
def load_secret(secret_name: str, default_value: str = None) -> str:
    try:
        with open(f'/run/secrets/{secret_name}', 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        return default_value

# Configuration loading
OPENAI_API_KEY = load_secret('OPENAI_API_KEY')
TRANSCRIPTION_MODE = load_secret('TRANSCRIPTION_MODE', 'online')
OFFLINE_MODEL_NAME = load_secret('OFFLINE_MODEL_NAME', 'base')
WHISPER_DEVICE = load_secret('WHISPER_DEVICE', 'auto')
```

**Note:** Secrets are managed through `docker mcp secret set` commands and injected by the MCP Gateway, not via Docker Swarm-style `--secret` flags.

### Environment Variables

- `OPENAI_API_KEY`: Required for online transcription mode
- `TRANSCRIPTION_MODE`: "online" or "offline" processing mode
- `OFFLINE_MODEL_NAME`: Whisper model for offline processing
- `WHISPER_DEVICE`: Processing device ("cpu", "cuda", "auto")

## Error Handling Patterns

### Validation Errors
```python
if not url or not isinstance(url, str):
    return "❌ Error: Invalid URL format\nURL must be a non-empty string"
```

### Network Errors
```python
try:
    result = await process_video(url)
except httpx.TimeoutException:
    return "⏱️ Error: Request timeout\nTry again or check your internet connection"
```

### API Errors
```python
except openai.APIError as e:
    return f"🔑 Error: API Error: {str(e)}\nCheck your OpenAI API key and credits"
```

### File System Errors
```python
except OSError as e:
    return f"💾 Error: Storage Error: {str(e)}\nCheck disk space and permissions"
```

## Response Formatting

### Success Responses
- ✅ Success indicators for completed operations
- 📊 Data responses for information retrieval
- ⏱️ Time estimates and processing information
- 🤖 Model information and capabilities

### Error Responses
- ❌ Clear error indicators
- 🔍 Specific error messages
- 💡 Helpful suggestions and troubleshooting
- 🔧 Technical details for debugging

### Structured Output
All responses follow consistent string formatting:
- ✅ Success indicators for completed operations
- ❌ Clear error indicators with specific messages
- 📊 Data responses with formatted information
- ⏱️ Time estimates and processing information
- 🤖 Model information and capabilities

## Development Guidelines

### Adding New Tools

1. **Define Tool Function**:
```python
@mcp.tool()
async def new_tool_name(param1: str = "", param2: str = "") -> str:
    """Tool description for Claude."""
    if not param1.strip():
        return "❌ Error: param1 is required"
    
    try:
        # Implementation
        return (
            "✅ Operation complete\n"
            "Result: ...\n"
            "Details: ..."
        )
    except Exception as e:
        return f"❌ Error: {str(e)}"
```

2. **Register Tool**:
```python
@mcp.tool()
async def list_tools() -> str:
    """List all available tools."""
    return (
        "Available tools:\n"
        "- new_tool_name: Tool description\n"
        "- existing_tool: Another tool description"
    )
```

3. **Update Configuration**:
- Add tool to `custom.yaml` tools list
- Update documentation
- Rebuild Docker image

### Async/Await Usage
All tool functions use async/await for non-blocking operations:
```python
async def process_video(url: str) -> dict:
    # Async video processing
    result = await video_converter.convert(url)
    return result
```

### Logging Practices
```python
import logging

logger = logging.getLogger(__name__)

# Log important events
logger.info(f"Processing video: {url}")
logger.warning(f"Using fallback model: {model}")
logger.error(f"Transcription failed: {error}")
```

### Parameter Validation
```python
def validate_url(url: str) -> bool:
    """Validate video URL format and platform support."""
    if not url or not isinstance(url, str):
        return False
    
    supported_domains = ['youtube.com', 'vimeo.com', 'tiktok.com']
    return any(domain in url.lower() for domain in supported_domains)
```

## Integration Points

### VideoDownloader Integration
```python
from src.video_downloader import VideoDownloader

video_downloader = VideoDownloader()
video_path = await video_downloader.download(url)
```

### AudioExtractor Integration
```python
from src.audio_extractor import AudioExtractor

audio_extractor = AudioExtractor()
audio_path = await audio_extractor.extract_audio(video_path)
```

### CloudTranscriber Integration
```python
from src.cloud_transcriber import CloudTranscriber

cloud_transcriber = CloudTranscriber(api_key=OPENAI_API_KEY)
transcription = await cloud_transcriber.transcribe(audio_path)
```

### OfflineTranscriber Integration
```python
from src.offline_transcriber import OfflineTranscriber

offline_transcriber = OfflineTranscriber(model_name=OFFLINE_MODEL_NAME)
transcription = await offline_transcriber.transcribe(audio_path)
```

## Security Considerations

### MCP Toolkit Secret Handling
- Secrets are managed through `docker mcp secret set` commands
- Secrets are injected by the MCP Gateway as read-only files in `/run/secrets/`
- No secrets are logged or exposed in error messages
- Fallback values are used when secrets are not available
- Gateway-based injection ensures secrets are only available when properly configured

### Input Sanitization
```python
def sanitize_url(url: str) -> str:
    """Sanitize and validate URL input."""
    # Remove dangerous characters
    url = url.strip()
    # Validate URL format
    if not url.startswith(('http://', 'https://')):
        raise ValueError("Invalid URL format")
    return url
```

### Temporary File Cleanup
```python
import tempfile
import os

async def process_with_cleanup(url: str):
    temp_file = None
    try:
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        # Process file
        return result
    finally:
        if temp_file and os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
```

### Non-root Execution
Docker container runs as non-privileged user:
```dockerfile
RUN adduser --disabled-password --gecos '' mcpuser
USER mcpuser
```

## Performance Notes

### Caching Strategies
- Video metadata is cached to avoid repeated API calls
- Model loading is cached for offline processing
- Temporary files are reused when possible

### Progress Callbacks
```python
def progress_callback(progress: float, message: str):
    """Report processing progress to MCP client."""
    logger.info(f"Progress: {progress:.1%} - {message}")
```

### Memory Management
- Large videos are processed in chunks
- Temporary files are cleaned up immediately
- Model memory is released after processing

## Testing Strategies

### Local Testing
```bash
# Test MCP server directly
python main.py

# Test with MCP client
mcp-client test-server --tool transcribe_video_url --args '{"url": "https://youtube.com/watch?v=test"}'
```

### MCP Toolkit Secret Setup
```bash
# Set secrets for MCP Toolkit
docker mcp secret set OPENAI_API_KEY="your-openai-api-key-here"
docker mcp secret set TRANSCRIPTION_MODE="online"
docker mcp secret set OFFLINE_MODEL_NAME="base"
docker mcp secret set WHISPER_DEVICE="auto"

# Verify secrets
docker mcp secret list
```

**Note:** Secrets are injected by the MCP Gateway based on `~/.docker/mcp/catalogs/custom.yaml` and `~/.docker/mcp/registry.yaml`, not via `docker run --secret`.

### Docker Container Validation
```bash
# Build and test container
docker build -t url-to-text-mcp-server .

# Pure smoke test (secrets not available in this mode)
docker run --rm url-to-text-mcp-server:latest
```

### MCP Protocol Testing
- Use MCP client tools for protocol validation
- Test all tool functions with various inputs
- Verify error handling and response formats
- Test with Claude Desktop integration

## Troubleshooting

### Common Issues
1. **Tools not appearing**: Check Claude Desktop configuration and MCP Gateway setup
2. **Authentication errors**: Verify MCP Toolkit secrets setup with `docker mcp secret list`
3. **Docker build failures**: Check Dockerfile and dependencies
4. **ffmpeg issues**: Install system ffmpeg dependency
5. **Memory errors**: Use smaller Whisper models
6. **Secret injection issues**: Verify catalog and registry configuration files

### Debug Mode
Enable debug logging for detailed troubleshooting:
```python
logging.basicConfig(level=logging.DEBUG)
```

### Health Checks
Implement health check endpoint for container monitoring:
```python
@mcp.tool()
async def health_check() -> str:
    """Check server health and dependencies."""
    return (
        "🏥 Health Check Results\n"
        "Status: healthy\n\n"
        "Dependencies:\n"
        f"- ffmpeg: {check_ffmpeg()}\n"
        f"- whisper: {check_whisper()}\n"
        f"- openai: {check_openai_key()}"
    )
```
