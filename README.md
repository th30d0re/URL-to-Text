# URL-to-Text Project Suite

A comprehensive collection of tools and services designed to convert video and audio URLs into text transcriptions. This project supports multiple platforms (YouTube, Vimeo, TikTok, Instagram, etc.) and offers both cloud-based and local transcription options.

## 🚀 Project Components

The workspace is organized into several specialized components:

### 1. [Python_MVP](./Python_MVP) - Core Transcription Engine
The heart of the project, providing the logic for downloading media and transcribing it using Whisper.
- **CLI Tool**: A standalone command-line interface for transcribing videos locally or via OpenAI API.
- **MCP Server**: A Model Context Protocol server that integrates transcription capabilities directly into AI assistants like Claude Desktop.
- **Dual Modes**: Supports **Online** (OpenAI Whisper API) and **Offline** (Local Whisper models with GPU acceleration).

### 2. [yt-dlp-server](./yt-dlp-server) - Metadata Extraction Service
A lightweight FastAPI wrapper around `yt-dlp` designed to:
- Extract direct video/audio URLs and metadata from links.
- Serve as a high-performance backend fallback for mobile applications.
- Handle rate limiting and provides a simple JSON API.

### 3. [Transcribe](./Transcribe) - iOS Application
(Details coming soon) The mobile client for the URL-to-Text ecosystem, designed for on-the-go transcription.

---

## 🛠 Quick Start

### Standalone CLI (Python_MVP)
Convert a video to text immediately from your terminal:
```bash
cd Python_MVP
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python main.py "https://www.youtube.com/watch?v=example"
```
*See [Python_MVP/README.md](./Python_MVP/README.md) for full details.*

### Claude Desktop Integration (MCP)
Give Claude the ability to "watch" and transcribe videos for you:
1. Build the Docker image: `cd Python_MVP && docker build -t url-to-text-mcp-server .`
2. Configure your `claude_desktop_config.json`.
*See [MCP Installation Guide](./Python_MVP/INSTALLATION.md) for step-by-step instructions.*

### yt-dlp Server
Run the metadata extraction service:
```bash
cd yt-dlp-server
docker-compose up --build
```
*See [yt-dlp-server/README.md](./yt-dlp-server/README.md) for API documentation.*

---

## 🏗 Key Features

- **Multi-Platform**: Robust support for any platform supported by `yt-dlp`.
- **Privacy Focused**: Local transcription mode ensures your data never leaves your machine.
- **AI Ready**: MCP integration allows seamless use within AI-driven workflows.
- **Scalable**: Dockerized services for easy deployment and isolation.

## 📜 Licenses & Contributions
Please refer to individual component directories for specific licensing and contribution guidelines.
