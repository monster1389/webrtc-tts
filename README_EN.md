# WebRTC Real-time LLM + TTS System

A real-time conversational AI system based on WebRTC technology, integrating Large Language Models (LLM) with Text-to-Speech (TTS) for low-latency audio streaming and interactive conversations.

## Features

- **Real-time audio streaming**: Low-latency audio transmission via WebRTC
- **LLM Integration**: Support for multiple LLM providers (OpenAI, DashScope, Local Test)
- **Streaming TTS processing**: Real-time text-to-speech conversion using EdgeTTS
- **Multi-provider support**: Easily switch between different LLM providers via configuration
- **Environment-based configuration**: Secure API key management using environment variables
- **No audio files**: Process audio data directly in memory without generating temporary files
- **Smart audio queue**: Queue-based audio data management for continuous speech playback
- **Cross-platform compatibility**: Supports modern browsers without additional plugins
- **Streaming LLM responses**: Real-time processing of LLM responses with synchronized TTS output

## Technical Architecture

```
┌─────────────┐    WebRTC     ┌─────────────┐    HTTP/WebSocket    ┌─────────────┐
│   Browser   │───────────────▶│   FastAPI   │─────────────────────▶│   LLM       │
│  (client.js) │               │   Server    │                     │   Provider  │
│             ◀───────────────│ (server.py) │◀─────────────────────│  (OpenAI/   │
└─────────────┘  Audio Stream └─────────────┘   Text Stream        │  DashScope/ │
       │                              │                                    │ Local)
       │                              │                                    │
       │                ┌─────────────▼─────────────┐                     │
       │                │                           │                     │
       │                │     Audio Processing      │                     │
       │                │        Pipeline           │                     │
       │                │  ┌─────────────────────┐  │                     │
       └────────────────┼─▶│  SmartAudioTrack    │◀─┘                     │
                        │  │  • Audio Queue      │                       │
                        │  │    Management       │                       │
                        │  │  • Streaming Frame  │                       │
                        │  │    Generation       │                       │
                        │  └─────────────────────┘                       │
                        │            │                                   │
                        │            ▼                                   │
                        │  ┌─────────────────────┐                       │
                        │  │  AudioQueueManager  │                       │
                        │  │  • Queue Buffering  │                       │
                        │  │  • Data Slicing     │                       │
                        │  └─────────────────────┘                       │
                        │            │                                   │
                        │            ▼                                   │
                        │  ┌─────────────────────┐                       │
                        └─▶│  FFmpeg Audio       │◀──────────────────────┘
                           │    Conversion       │
                           │  • MP3 → PCM        │
                           │  • Resampling       │
                           └─────────────────────┘
```

## Installation and Running

### System Requirements

- Python 3.8+
- FFmpeg (for audio format conversion)
- Modern browser (Chrome 90+, Firefox 88+, Edge 90+)

### Installation Steps

1. Clone the project or download files
   ```bash
   git clone https://github.com/monster1389/webrtc-tts.git
   cd webrtc-tts
   ```

2. Install Python dependencies
   ```bash
   pip install -r requirements.txt
   ```

3. Install FFmpeg
   - **Windows**: Using Chocolatey `choco install ffmpeg`
   - **macOS**: Using Homebrew `brew install ffmpeg`
   - **Linux**: `sudo apt-get install ffmpeg` (Ubuntu/Debian)

4. Configure environment variables (for API keys)
   ```bash
   # For OpenAI/DeepSeek
   export OPENAI_API_KEY="your-api-key-here"
   # For AliCloud DashScope
   export DASHSCOPE_API_KEY="your-api-key-here"
   ```

### Run the Server

```bash
uvicorn server:app --reload
```

The server will start at `http://localhost:8000`.

## Configuration

The system uses `config.json` for configuration. By default, API keys are loaded from environment variables for security:

```json
{
  "llm_provider": "openai",
  "providers": {
    "openai": {
      "api_key": "${OPENAI_API_KEY}",
      "base_url": "https://api.openai.com/v1",
      "model": "gpt-3.5-turbo",
      "temperature": 0.7,
      "max_tokens": 1000
    },
    "dashscope": {
      "api_key": "${DASHSCOPE_API_KEY}",
      "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
      "model": "qwen-plus",
      "temperature": 0.7,
      "max_tokens": 1000
    },
    "local": {
      "model": "local-test-model",
      "temperature": 0.7,
      "max_tokens": 500,
      "responses": [
        "Hello! This is a test response.",
        "Glad to serve you.",
        "This is a demonstration of streaming response.",
        "WebRTC + LLM + TTS system is working properly.",
        "You can easily switch between different LLM providers."
      ]
    }
  }
}
```

### Supported LLM Providers

1. **OpenAI**: Compatible with OpenAI API and DeepSeek API
2. **DashScope**: AliCloud's Tongyi Qianwen models
3. **Local**: Test mode with predefined responses (no API key required)

## Usage

1. Open browser and visit `http://localhost:8000`
2. Click "Connect to Server" button to establish WebRTC connection
3. Enter your message in the text box
4. Click "Send Text" button
5. The system will:
   - Send your message to the configured LLM provider
   - Stream the LLM response in real-time
   - Convert text to speech using EdgeTTS
   - Play the audio response through your browser

## Project Structure

```
webrtc-tts/
├── server.py              # FastAPI server, handles WebRTC, LLM and TTS
├── client.js              # Frontend WebRTC client
├── index.html             # Frontend interface
├── requirements.txt       # Python dependencies
├── config.json           # Configuration file (API keys from env vars)
├── README_CN.md          # Chinese documentation
├── README.md             # English documentation (this file)
├── llm/                  # LLM integration module
│   ├── config.py         # Configuration loader
│   ├── factory.py        # LLM provider factory
│   └── provider.py       # Base provider interface
└── providers/            # LLM provider implementations
    ├── dashscope_provider.py  # AliCloud DashScope provider
    ├── local_provider.py      # Local test provider
    └── openai_provider.py     # OpenAI/DeepSeek provider
```

## Core Components

### server.py
- **FastAPI Application**: Provides web interface and WebRTC signaling
- **SmartAudioTrack**: Intelligent audio track, manages audio queue and frame generation
- **AudioQueueManager**: Audio queue manager, buffers and slices audio data
- **LLM Integration**: Stream processing of LLM responses with TTS synchronization
- **Task Management**: Proper cleanup of WebRTC connections and background tasks

### client.js
- **WebRTC Connection**: Establishes PeerConnection with server
- **Audio Playback**: Receives and plays audio stream from server
- **Text Sending**: Sends text to server via DataChannel
- **Real-time Updates**: Displays LLM response text as it's being generated

### LLM Module
- **Provider Pattern**: Abstract interface for different LLM providers
- **Streaming Support**: Real-time streaming of LLM responses
- **Configurable**: Easy switching between providers via configuration

## Technical Details

### Audio Processing Pipeline
1. User input text is sent to server via DataChannel
2. Server send the text to configured LLM provider
3. LLM response is streamed back in real-time
4. Each text chunk is sent to EdgeTTS for MP3 audio generation
5. FFmpeg converts MP3 to PCM format in real-time
6. PCM data is sliced and placed into audio queue
7. SmartAudioTrack reads data from queue and generates audio frames
8. Audio frames are transmitted to browser via WebRTC
9. Browser receives and plays audio while displaying text

### Performance Optimizations
- **Streaming Processing**: Avoids generating temporary files, reduces disk I/O
- **Queue Buffering**: Smooths audio playback, prevents stuttering
- **Silence Frame Generation**: Generates silence when queue is empty, keeps connection alive
- **Task Cancellation**: Proper cleanup of background tasks when connections close

## Security Notes

- **API Key Security**: API keys are loaded from environment variables, not stored in config.json
- **Environment Variables**: Use `OPENAI_API_KEY` and `DASHSCOPE_API_KEY` for respective providers
- **Local Test Mode**: Use "local" provider for testing without API keys

## Troubleshooting

### Common Issues

1. **Cannot Connect to Server**
   - Check if server is running `python server.py`
   - Check firewall settings, ensure port 8000 is open
   - Check browser console for WebRTC errors

2. **No Sound**
   - Check browser console for error messages
   - Confirm FFmpeg is correctly installed `ffmpeg -version`
   - Check if browser audio settings are muted
   - Verify environment variables are set correctly

3. **LLM Not Responding**
   - Check API keys are set in environment variables
   - Verify network connectivity to LLM provider APIs
   - Check server logs for authentication errors

4. **Audio Stuttering or Delay**
   - Check network connection quality
   - Reduce server load, close other resource-intensive programs
   - Check FFmpeg installation and performance

### Viewing Logs

Server logs show connection status, LLM processing, and TTS progress:

```bash
# Run server with verbose logging
uvicorn server:app --reload 2>&1 | tee server.log
```

## License

This project is open source under the MIT License.

## Contributing

Welcome to submit Issues and Pull Requests to improve this project.

## Contact

For questions or suggestions, please contact through the project repository's Issue page.
