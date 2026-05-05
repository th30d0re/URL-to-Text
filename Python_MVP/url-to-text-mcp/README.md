# URL-to-Text MCP Server

## Purpose

This MCP server provides AI assistants with powerful video-to-text transcription capabilities from various platforms including YouTube, Vimeo, TikTok, Instagram, and more. It enables Claude Desktop and other MCP-compatible AI assistants to extract and transcribe audio content from video URLs using either cloud-based OpenAI Whisper API or local Whisper models for offline processing.

## Features

The URL-to-Text MCP server provides 5 powerful tools:

### 🎥 transcribe_video_url
Convert any supported video URL to text transcription with configurable quality settings and progress tracking.

### 📊 get_video_info
Retrieve comprehensive video metadata including title, duration, platform, and processing requirements without downloading or transcribing.

### ✅ validate_video_url
Check if a video URL is supported by the system and validate its accessibility before processing.

### ⏱️ estimate_processing_time
Calculate estimated transcription time based on video duration, selected model, and processing mode (online/offline).

### 🤖 list_available_models
Display all available Whisper models with their capabilities, size requirements, and performance characteristics.

## Prerequisites

- **Docker Desktop** with MCP Toolkit installed
- **OpenAI API Key** (optional, for online transcription mode)
- **Python 3.11+** (for local development)

**Note:** The Docker image includes ffmpeg for audio processing, so no additional system dependencies are required.

## Installation

### Step 1: Save Configuration Files
Create a project directory and save all MCP configuration files:
- `readme.txt` (this file)
- `CLAUDE.md` (implementation details)
- `custom.yaml` (catalog configuration)
- `registry_update.yaml` (registry configuration)
- `INSTALLATION.md` (detailed setup guide)

### Step 2: Build Docker Image
```bash
docker build -t url-to-text-mcp-server .
```

### Step 3: Set Up MCP Toolkit Secrets
Configure required secrets for the MCP server:

```bash
# Set secrets for MCP Toolkit
docker mcp secret set OPENAI_API_KEY="your-openai-api-key-here"
docker mcp secret set TRANSCRIPTION_MODE="online"
docker mcp secret set OFFLINE_MODEL_NAME="base"
docker mcp secret set WHISPER_DEVICE="auto"

# Verify secrets
docker mcp secret list
```

**Note:** The MCP Gateway will make these secrets available per the catalog config.

### Step 4: Create Custom Catalog
Create the custom catalog file at `~/.docker/mcp/catalogs/custom.yaml` with the provided content from `custom.yaml`.

### Step 5: Update Registry
Add the registry entry to `~/.docker/mcp/registry.yaml` under the `registry:` key using the content from `registry_update.yaml`.

### Step 6: Configure Claude Desktop
Update your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
**Linux**: `~/.config/Claude/claude_desktop_config.json`

Add the MCP Toolkit Gateway to your configuration:
```json
{
  "mcpServers": {
    "mcp-toolkit-gateway": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "/var/run/docker.sock:/var/run/docker.sock",
        "-v", "[YOUR_HOME]/.docker/mcp:/mcp",
        "docker/mcp-gateway",
        "--catalog=/mcp/catalogs/docker-mcp.yaml",
        "--catalog=/mcp/catalogs/custom.yaml",
        "--config=/mcp/config.yaml",
        "--registry=/mcp/registry.yaml",
        "--tools-config=/mcp/tools.yaml",
        "--transport=stdio"
      ]
    }
  }
}
```

**Platform-specific replacements:**
- **macOS**: Replace `[YOUR_HOME]` with `/Users/yourusername`
- **Windows**: Replace `[YOUR_HOME]` with `C:/Users/yourusername`
- **Linux**: Replace `[YOUR_HOME]` with `/home/yourusername`

### Step 7: Restart Claude Desktop
Completely restart Claude Desktop to load the new MCP server configuration.

### Step 8: Test Installation
Verify the installation by asking Claude to:
- "List available transcription models"
- "Validate this video URL: https://www.youtube.com/watch?v=example"
- "Get information about this video: [any video URL]"

## Usage Examples

### Natural Language Commands for Claude Desktop

**Basic Transcription:**
- "Transcribe this YouTube video: https://www.youtube.com/watch?v=example"
- "Convert this Vimeo video to text: https://vimeo.com/example"
- "Extract text from this TikTok video: https://tiktok.com/@user/video/example"

**Video Information:**
- "Get information about this video without transcribing it"
- "What's the duration and title of this video?"
- "Check if this video URL is supported"

**Processing Estimates:**
- "How long will it take to process this 30-minute video?"
- "Estimate transcription time for this 2-hour lecture"
- "What's the processing time for this short clip?"

**Model Management:**
- "What Whisper models are available?"
- "Show me the differences between Whisper models"
- "Which model should I use for best quality?"

**Advanced Usage:**
- "Transcribe this video using the large model for maximum accuracy"
- "Process this video offline using the base model"
- "Get video info and then transcribe if it's under 10 minutes"

## Architecture

```
Claude Desktop
    ↓
MCP Gateway
    ↓
URL-to-Text Server (Docker Container)
    ↓
VideoToTextConverter
    ├── VideoDownloader (yt-dlp)
    ├── AudioExtractor (ffmpeg)
    └── Transcriber
        ├── CloudTranscriber (OpenAI API)
        └── OfflineTranscriber (Local Whisper)
```

## Development

### Local Testing
```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run MCP server directly
python url_to_text_server.py

# Test with MCP client
mcp-client test-server
```

### Adding New Tools
1. Define tool function in `url_to_text_server.py`
2. Add tool to `@server.list_tools()` decorator
3. Update `custom.yaml` with new tool
4. Rebuild Docker image
5. Update documentation

## Troubleshooting

### Tools Not Appearing
- Verify Claude Desktop configuration includes custom catalog
- Check Docker image is built and tagged correctly
- Ensure registry.yaml has proper entry under `registry:` key
- Restart Claude Desktop completely

### Authentication Errors
- Verify OPENAI_API_KEY secret is set correctly
- Check API key has sufficient credits
- Ensure TRANSCRIPTION_MODE secret is set to "online"

### Docker Issues
- Verify Docker Desktop is running
- Check image exists: `docker images | grep url-to-text`
- Test container manually: `docker run --rm url-to-text-mcp-server:latest`

### ffmpeg Problems
- The Docker image includes ffmpeg, so this should not occur
- If you encounter ffmpeg errors, rebuild the Docker image
- Verify ffmpeg is working: `docker run --rm url-to-text-mcp-server:latest ffmpeg -version`

### Performance Issues
- Use smaller Whisper models for faster processing
- Enable GPU acceleration with CUDA
- Consider online mode for better performance
- Monitor system resources during processing

## Security

- **Docker Secrets**: API keys stored securely in Docker secrets
- **Non-root Execution**: Container runs as non-privileged user
- **No Credential Logging**: Sensitive data never logged
- **Temporary File Cleanup**: All temporary files automatically removed
- **Input Validation**: All URLs and parameters validated before processing
- **Network Isolation**: Container has minimal network access

## Support

For issues, feature requests, or contributions:
- Check the troubleshooting section above
- Review logs in Claude Desktop developer tools
- Test with simple video URLs first
- Verify all prerequisites are installed correctly

## License

MIT License - See LICENSE file for details.
