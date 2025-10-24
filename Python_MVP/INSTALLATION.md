# URL-to-Text MCP Server - Installation Guide

## Prerequisites

Before installing the URL-to-Text MCP server, ensure you have the following:

- **Docker Desktop** installed and running
- **MCP Toolkit** installed (part of Docker Desktop)
- **OpenAI API Key** (optional, for online transcription mode)
- **Claude Desktop** application installed

**Note:** The Docker image includes ffmpeg for audio processing, so no additional system dependencies are required.

## Step-by-Step Installation

### Step 1: Save Configuration Files

Create a project directory and save all MCP configuration files:

```bash
# Create project directory
mkdir url-to-text-mcp
cd url-to-text-mcp

# Save all configuration files
# - readme.txt
# - CLAUDE.md
# - custom.yaml
# - registry_update.yaml
# - INSTALLATION.md (this file)
```

Ensure all files are saved in the same directory for proper organization.

### Step 2: Build Docker Image

Build the Docker image for the URL-to-Text MCP server:

```bash
# Navigate to your project directory
cd url-to-text-mcp

# Build the Docker image
docker build -t url-to-text-mcp-server .

# Verify the image was created
docker images | grep url-to-text-mcp-server
```

**Expected Output:**
```
url-to-text-mcp-server   latest    [image-id]   [size]   [time]
```

### Step 3: Set Up MCP Toolkit Secrets

Configure the required secrets for the MCP server. Choose the appropriate mode:

#### For Online Mode (OpenAI API)
```bash
# Set secrets for MCP Toolkit
docker mcp secret set OPENAI_API_KEY="your-openai-api-key-here"
docker mcp secret set TRANSCRIPTION_MODE="online"
docker mcp secret set OFFLINE_MODEL_NAME="base"
docker mcp secret set WHISPER_DEVICE="auto"

# Verify secrets
docker mcp secret list
```

#### For Offline Mode (Local Whisper)
```bash
# Set secrets for MCP Toolkit
docker mcp secret set OPENAI_API_KEY=""
docker mcp secret set TRANSCRIPTION_MODE="offline"
docker mcp secret set OFFLINE_MODEL_NAME="base"
docker mcp secret set WHISPER_DEVICE="cpu"

# Verify secrets
docker mcp secret list
```

**Note:** The MCP Gateway will make these secrets available per the catalog config.

### Step 4: Create Custom Catalog

Create the custom catalog file in the MCP catalogs directory:

```bash
# Create catalogs directory if it doesn't exist
mkdir -p ~/.docker/mcp/catalogs

# Copy the custom.yaml content to the catalogs directory
cp custom.yaml ~/.docker/mcp/catalogs/custom.yaml

# Verify the file was created
ls -la ~/.docker/mcp/catalogs/
```

**File Location:**
- **macOS/Linux**: `~/.docker/mcp/catalogs/custom.yaml`
- **Windows**: `%USERPROFILE%\.docker\mcp\catalogs\custom.yaml`

### Step 5: Update Registry

Add the URL-to-Text server to your MCP registry:

```bash
# Create registry directory if it doesn't exist
mkdir -p ~/.docker/mcp

# If registry.yaml doesn't exist, create it
if [ ! -f ~/.docker/mcp/registry.yaml ]; then
    echo "registry:" > ~/.docker/mcp/registry.yaml
fi

# Add the URL-to-Text entry to your existing registry.yaml
# Open the file and add the entry under the "registry:" key
```

**Manual Edit Required:**
1. Open `~/.docker/mcp/registry.yaml` in your text editor
2. Find the `registry:` key
3. Add the following entry under it:
```yaml
registry:
  # ... your existing servers ...
  
  url-to-text:
    ref: ""
```

**Important:** The entry must be under the existing `registry:` key, not at the root level.

### Step 6: Configure Claude Desktop

Update your Claude Desktop configuration to use the MCP Toolkit Gateway:

#### macOS Configuration
```bash
# Open Claude Desktop config file
open ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

#### Windows Configuration
```bash
# Open Claude Desktop config file
notepad %APPDATA%\Claude\claude_desktop_config.json
```

#### Linux Configuration
```bash
# Open Claude Desktop config file
nano ~/.config/Claude/claude_desktop_config.json
```

#### Configuration Content
Add the following to your Claude Desktop configuration:

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

**Note:** If you already have other MCP servers configured, add the MCP Toolkit Gateway to the existing `mcpServers` object.

### Step 7: Restart Claude Desktop

Completely restart Claude Desktop to load the new MCP server configuration:

1. **Quit Claude Desktop** completely
2. **Wait 5-10 seconds** for all processes to terminate
3. **Launch Claude Desktop** again
4. **Wait for initialization** to complete

### Step 8: Test Installation

Verify the installation by testing the MCP server functionality:

#### Test 1: List Available Models
Ask Claude: "List available transcription models"

**Expected Response:** List of Whisper models with their capabilities

#### Test 2: Validate Video URL
Ask Claude: "Validate this video URL: https://www.youtube.com/watch?v=dQw4w9WgXcQ"

**Expected Response:** Validation result with video information

#### Test 3: Get Video Information
Ask Claude: "Get information about this video: https://www.youtube.com/watch?v=dQw4w9WgXcQ"

**Expected Response:** Video metadata including title, duration, platform

#### Test 4: Estimate Processing Time
Ask Claude: "How long will it take to process a 5-minute video?"

**Expected Response:** Time estimate based on model and mode

## Platform-Specific Notes

### macOS
- **Docker Desktop**: Install from Docker website or Homebrew
- **ffmpeg**: Install via Homebrew: `brew install ffmpeg`
- **File Paths**: Use `~` for home directory in all paths
- **Permissions**: May need to grant Docker Desktop full disk access

### Windows
- **Docker Desktop**: Install from Docker website
- **ffmpeg**: Download from ffmpeg.org or use Chocolatey: `choco install ffmpeg`
- **File Paths**: Use `%USERPROFILE%` for home directory
- **WSL2**: Ensure WSL2 is enabled for Docker Desktop

### Linux
- **Docker**: Install Docker Engine and Docker Compose
- **ffmpeg**: Install via package manager: `sudo apt install ffmpeg` (Ubuntu/Debian)
- **File Paths**: Use `~` for home directory
- **Permissions**: Add user to docker group: `sudo usermod -aG docker $USER`

## Troubleshooting

### Docker Build Failures

**Problem**: Docker build fails with dependency errors
**Solution**:
```bash
# Clean Docker cache
docker system prune -a

# Rebuild with no cache
docker build --no-cache -t url-to-text-mcp-server .

# Check Docker logs
docker logs [container-id]
```

### Catalog Not Loading

**Problem**: Custom catalog not appearing in Claude Desktop
**Solution**:
1. Verify catalog file exists: `ls -la ~/.docker/mcp/catalogs/custom.yaml`
2. Check YAML syntax: `python -c "import yaml; yaml.safe_load(open('~/.docker/mcp/catalogs/custom.yaml'))"`
3. Ensure proper file permissions: `chmod 644 ~/.docker/mcp/catalogs/custom.yaml`

### Secrets Not Working

**Problem**: MCP server can't access MCP Toolkit secrets
**Solution**:
```bash
# Verify secrets exist
docker mcp secret list

# Recreate secrets if needed
docker mcp secret set OPENAI_API_KEY="your-key-here"
docker mcp secret set TRANSCRIPTION_MODE="online"
```

### Claude Desktop Configuration Issues

**Problem**: Claude Desktop not recognizing MCP server
**Solution**:
1. Verify JSON syntax in config file
2. Check file location is correct for your platform
3. Ensure proper indentation and formatting
4. Restart Claude Desktop completely

### ffmpeg Dependency Problems

**Problem**: Audio processing fails with ffmpeg errors
**Solution**: The Docker image includes ffmpeg, so this should not occur. If you encounter ffmpeg errors:

```bash
# Verify the Docker image includes ffmpeg
docker run --rm url-to-text-mcp-server:latest ffmpeg -version

# If ffmpeg is missing, rebuild the image
docker build --no-cache -t url-to-text-mcp-server .
```

**Note:** The Dockerfile includes `apt-get install -y ffmpeg` to ensure ffmpeg is available in the container.

### Tools Not Appearing

**Problem**: MCP tools not visible in Claude Desktop
**Solution**:
1. Check Claude Desktop logs for errors
2. Verify Docker image is running: `docker ps`
3. Test MCP server manually: `docker run --rm url-to-text-mcp-server:latest`
4. Ensure all secrets are properly configured

### Memory Issues

**Problem**: Out of memory errors during processing
**Solution**:
1. Use smaller Whisper models (tiny, base instead of large)
2. Enable swap space on your system
3. Close other applications to free memory
4. Use online mode instead of offline processing

## Usage Examples

### Basic Transcription
```
User: "Transcribe this YouTube video: https://www.youtube.com/watch?v=example"
Claude: I'll transcribe that video for you using the URL-to-Text MCP server...
```

### Video Information
```
User: "Get information about this video without transcribing it"
Claude: Let me retrieve the video metadata for you...
```

### Processing Estimates
```
User: "How long will it take to process this 30-minute video?"
Claude: Based on the video duration and selected model, I estimate...
```

### Model Selection
```
User: "What Whisper models are available?"
Claude: Here are the available Whisper models with their characteristics...
```

## Support

If you encounter issues not covered in this guide:

1. **Check Logs**: Review Claude Desktop and Docker logs for error messages
2. **Verify Configuration**: Ensure all files are in correct locations with proper syntax
3. **Test Components**: Verify Docker, ffmpeg, and Claude Desktop are working independently
4. **Community Support**: Check MCP documentation and community forums
5. **File Issues**: Report bugs with detailed error messages and system information

## Next Steps

After successful installation:

1. **Test with Various URLs**: Try different video platforms and formats
2. **Experiment with Models**: Test different Whisper models for quality vs. speed
3. **Configure Preferences**: Set up your preferred transcription settings
4. **Explore Features**: Try all available MCP tools and their capabilities
5. **Optimize Performance**: Adjust settings based on your hardware and needs

## Uninstallation

To remove the URL-to-Text MCP server:

```bash
# Remove Docker image
docker rmi url-to-text-mcp-server:latest

# Remove MCP Toolkit secrets
docker mcp secret rm OPENAI_API_KEY
docker mcp secret rm TRANSCRIPTION_MODE
docker mcp secret rm OFFLINE_MODEL_NAME
docker mcp secret rm WHISPER_DEVICE

# Remove configuration files
rm ~/.docker/mcp/catalogs/custom.yaml
# Edit ~/.docker/mcp/registry.yaml to remove url-to-text entry
# Edit Claude Desktop config to remove url-to-text server
```
