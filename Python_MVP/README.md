# Video to Text Converter

A Python application that converts video URLs to text using either OpenAI's Whisper API or local Whisper models. This tool downloads videos from various platforms, extracts audio, and transcribes the content using state-of-the-art speech recognition.

## Features

- **Multi-platform Support**: Works with YouTube, Vimeo, and many other video platforms
- **Dual Transcription Modes**: 
  - **Online Mode**: Uses OpenAI's Whisper API for cloud-based transcription
  - **Offline Mode**: Uses local Whisper models for private, cost-free transcription
- **Flexible Output**: Save transcriptions to files or display in terminal
- **Language Support**: Auto-detect language or specify target language
- **Progress Tracking**: Real-time progress updates during processing
- **Temporary File Management**: Automatic cleanup of intermediate files
- **Error Handling**: Comprehensive error handling and user-friendly messages
- **GPU Acceleration**: Support for CUDA and Apple Silicon GPU acceleration in offline mode

## Prerequisites

### System Dependencies

- **Python 3.8+**
- **ffmpeg**: Required for audio extraction

#### Installing ffmpeg

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**Windows:**
Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH

### API Requirements

#### Online Mode (OpenAI API)
- **OpenAI API Key**: Required for cloud-based transcription
  - Get your API key from [OpenAI Platform](https://platform.openai.com/api-keys)
  - Add credits to your OpenAI account for API usage

#### Offline Mode (Local Whisper)
- **No API Key Required**: Completely private and cost-free
- **System Requirements**: See offline mode requirements below

### Offline Mode System Requirements

#### RAM Requirements by Model
- **tiny**: ~1 GB RAM (fastest, lowest accuracy)
- **base**: ~1 GB RAM (recommended balance)
- **small**: ~2 GB RAM (better accuracy)
- **medium**: ~5 GB RAM (high accuracy)
- **large**: ~10 GB RAM (highest accuracy)
- **large-v2**: ~10 GB RAM (improved large model)
- **large-v3**: ~10 GB RAM (latest large model)

#### GPU Requirements (Optional but Recommended)
- **CUDA**: NVIDIA GPU with 4GB+ VRAM (8GB+ for large models)
- **Apple Silicon**: M1/M2/M3 Macs with Metal Performance Shaders
- **CPU Fallback**: Available if GPU is insufficient

#### Storage Requirements
- **Model Download**: 2-3 GB total for all models
- **Individual Models**: 39MB (tiny) to 1.5GB (large models)
- **Caching**: Models are downloaded once and cached locally

## Installation

1. **Clone or download this repository:**
   ```bash
   git clone <repository-url>
   cd video-to-text-converter
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   
   **Note**: For offline mode, this installs PyTorch and Whisper models (~2-3 GB download)

4. **Set up environment variables:**
   ```bash
   cp env.example .env
   ```
   
   Edit `.env` and configure your preferred mode:
   
   **For Online Mode (OpenAI API):**
   ```
   TRANSCRIPTION_MODE=online
   OPENAI_API_KEY=your_actual_api_key_here
   ```
   
   **For Offline Mode (Local Whisper):**
   ```
   TRANSCRIPTION_MODE=offline
   OFFLINE_MODEL_NAME=base
   WHISPER_DEVICE=auto
   ```

## Usage

### Online Mode (OpenAI API)

**Basic transcription:**
```bash
python main.py "https://www.youtube.com/watch?v=example"
```

**Save to file with language detection:**
```bash
python main.py "https://youtube.com/watch?v=example" --output transcript.txt --verbose
```

### Offline Mode (Local Whisper)

**Basic offline transcription:**
```bash
python main.py "https://www.youtube.com/watch?v=example" --offline
```

**Use specific model and device:**
```bash
python main.py "https://youtube.com/watch?v=example" --offline --model large --device cuda
```

**CPU-only mode (if no GPU available):**
```bash
python main.py "https://youtube.com/watch?v=example" --offline --model base --device cpu
```

**High accuracy mode:**
```bash
python main.py "https://youtube.com/watch?v=example" --offline --model large-v3 --language en
```

### Advanced Usage

**Save transcription to file:**
```bash
python main.py "https://youtube.com/watch?v=example" --output transcript.txt
```

**Specify language:**
```bash
python main.py "https://youtube.com/watch?v=example" --language en
```

**Enable verbose output:**
```bash
python main.py "https://youtube.com/watch?v=example" --verbose
```

**Keep intermediate files:**
```bash
python main.py "https://youtube.com/watch?v=example" --keep-files
```

**Get video information only:**
```bash
python main.py "https://youtube.com/watch?v=example" --info-only
```

**Estimate processing time:**
```bash
python main.py "https://youtube.com/watch?v=example" --estimate-time
```

### Command Line Options

- `VIDEO_URL`: URL of the video to convert (required)
- `--output, -o`: Output file to save transcription
- `--language, -l`: Language code for transcription (e.g., en, es, fr)
- `--keep-files, -k`: Keep intermediate video and audio files
- `--verbose, -v`: Enable verbose output with progress updates
- `--info-only`: Show video information without processing
- `--estimate-time`: Estimate processing time without processing
- `--offline`: Use offline Whisper model instead of OpenAI API
- `--model`: Whisper model size for offline mode (tiny, base, small, medium, large, large-v2, large-v3)
- `--device`: Device for offline Whisper inference (cpu, cuda, auto)

## Supported Platforms

This tool supports video downloads from:
- YouTube
- Vimeo
- Twitter/X
- TikTok
- Facebook
- Instagram
- And many more platforms supported by yt-dlp

## Supported Audio Formats

The Whisper API supports these audio formats:
- MP3
- MP4
- MPEG
- MPGA
- M4A
- WAV
- WEBM

## Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# Transcription Mode (online/offline)
TRANSCRIPTION_MODE=online

# Online Mode (OpenAI API)
OPENAI_API_KEY=your_openai_api_key_here

# Offline Mode (Local Whisper)
OFFLINE_MODEL_NAME=base
WHISPER_DEVICE=auto
# WHISPER_MODELS_DIR=/path/to/whisper/models  # Optional

# General Settings
TEMP_DIR=/tmp/video_to_text
KEEP_INTERMEDIATE_FILES=false
MAX_FILE_SIZE_MB=25
SEGMENT_DURATION_SECONDS=600
TRANSCODE_BITRATE_KBPS=64
```

### File Size Limits

- **Online Mode (OpenAI API)**: Maximum 25MB per audio file
- **Offline Mode (Local Whisper)**: No practical limit, can handle very large files
- **Automatic handling**: Large videos are automatically segmented for online mode
- **Configuration**: Adjust `SEGMENT_DURATION_SECONDS` (default: 600s) and `TRANSCODE_BITRATE_KBPS` (default: 64k) in your `.env` file

## Examples

### Online Mode Examples

**Example 1: Basic Online Transcription**
```bash
python main.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

**Example 2: Save to File with Language Detection**
```bash
python main.py "https://vimeo.com/123456789" --output meeting_notes.txt --verbose
```

**Example 3: Spanish Transcription**
```bash
python main.py "https://youtube.com/watch?v=example" --language es --output spanish_transcript.txt
```

### Offline Mode Examples

**Example 4: Basic Offline Transcription**
```bash
python main.py "https://www.youtube.com/watch?v=example" --offline
```

**Example 5: High Accuracy Offline Mode**
```bash
python main.py "https://youtube.com/watch?v=example" --offline --model large-v3 --device cuda
```

**Example 6: CPU-Only Offline Mode**
```bash
python main.py "https://youtube.com/watch?v=example" --offline --model base --device cpu
```

**Example 7: Offline with Language Specification**
```bash
python main.py "https://youtube.com/watch?v=example" --offline --model small --language en --output transcript.txt
```

### General Examples

**Example 8: Get Video Information**
```bash
python main.py "https://youtube.com/watch?v=example" --info-only
```

**Example 9: Estimate Processing Time**
```bash
python main.py "https://youtube.com/watch?v=example" --estimate-time
```

## Troubleshooting

### Common Issues

**1. "ffmpeg is not installed"**
- Install ffmpeg using the instructions above
- Ensure ffmpeg is in your system PATH

**2. "Invalid OpenAI API key" (Online Mode)**
- Verify your API key in the `.env` file
- Ensure you have credits in your OpenAI account
- Check that the API key has the correct permissions

**3. "File too large for Whisper API" (Online Mode)**
- The video is too long or high quality
- Try using a shorter video or lower quality source
- The tool automatically handles this in most cases
- Consider switching to offline mode for large files

**4. "Invalid or unsupported video URL"**
- Check that the URL is correct and accessible
- Ensure the video is not private or region-locked
- Try a different video platform

**5. "Rate limit exceeded" (Online Mode)**
- You've hit OpenAI's API rate limits
- Wait a few minutes and try again
- Consider upgrading your OpenAI plan
- Switch to offline mode to avoid rate limits

### Offline Mode Issues

**6. "openai-whisper package is required"**
- Install offline dependencies: `pip install openai-whisper torch torchaudio`
- Ensure you're using the correct Python environment

**7. "Insufficient memory to load model"**
- Try using a smaller model (tiny, base, small)
- Close other applications to free up RAM
- For large models, ensure you have 10GB+ RAM available

**8. "CUDA error" or "CUDA not available"**
- Install CUDA toolkit if you want GPU acceleration
- Use `--device cpu` to force CPU-only mode
- Check that your GPU is CUDA-compatible

**9. "Model download failed"**
- Check your internet connection
- Ensure you have sufficient disk space (2-3 GB)
- Try downloading the model manually or use a different model

**10. "Out of memory during transcription"**
- Use a smaller model (tiny, base, small)
- Process shorter audio segments
- Close other memory-intensive applications

### Debug Mode

Run with verbose output to see detailed progress:
```bash
python main.py "https://youtube.com/watch?v=example" --verbose
```

### Check Dependencies

Verify all dependencies are installed:
```bash
pip list
```

## Project Structure

```
Python_MVP/
├── main.py                 # CLI entry point
├── requirements.txt        # Python dependencies
├── env.example            # Environment variables template
├── .gitignore            # Git ignore rules
├── README.md             # This file
└── src/                  # Source code
    ├── __init__.py
    ├── config.py         # Configuration management
    ├── video_downloader.py  # Video downloading with yt-dlp
    ├── audio_extractor.py   # Audio extraction with ffmpeg
    ├── cloud_transcriber.py # OpenAI Whisper API integration
    ├── offline_transcriber.py # Local Whisper model integration
    ├── transcriber_factory.py # Factory for creating transcribers
    └── video_to_text.py     # Main orchestrator class
```

## Cost Comparison

### Online Mode (OpenAI API)
- **$0.006 per minute** of audio processed
- Example: 10-minute video = ~$0.06
- Requires internet connection and API key

### Offline Mode (Local Whisper)
- **$0.00** - Completely free after initial setup
- No internet required after model download
- No API key required
- One-time model download (~2-3 GB)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is open source. Please check the license file for details.

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Search existing issues
3. Create a new issue with detailed information

## Changelog

### Version 2.0.0
- **NEW**: Offline Whisper support with local models
- **NEW**: Dual transcription modes (online/offline)
- **NEW**: GPU acceleration support (CUDA, Apple Silicon)
- **NEW**: Flexible model selection (tiny to large-v3)
- **NEW**: Factory pattern for transcriber instantiation
- **IMPROVED**: Enhanced CLI with offline-specific options
- **IMPROVED**: Comprehensive offline mode documentation
- **IMPROVED**: Better error handling for offline mode issues
- **IMPROVED**: Cost-free transcription option

### Version 1.0.0
- Initial release
- Support for multiple video platforms
- OpenAI Whisper API integration
- CLI interface with multiple options
- Comprehensive error handling
- Temporary file management
