# WebRTC Real-time Text-to-Speech (TTS)

A real-time text-to-speech system based on WebRTC technology, using FastAPI + aiortc + EdgeTTS for low-latency audio streaming.

## Features

- **Real-time audio streaming**: Low-latency audio transmission via WebRTC
- **Streaming TTS processing**: Real-time text-to-speech conversion using EdgeTTS
- **No audio files**: Process audio data directly in memory without generating temporary files
- **Smart audio queue**: Queue-based audio data management for continuous speech playback
- **Cross-platform compatibility**: Supports modern browsers without additional plugins

## Technical Architecture

```
┌─────────────┐    WebRTC     ┌─────────────┐    HTTP/WebSocket    ┌─────────────┐
│   Browser   │───────────────▶│   FastAPI   │─────────────────────▶│  EdgeTTS    │
│  (client.js) │               │   Server    │                     │   Service   │
│             ◀───────────────│ (server.py) │◀─────────────────────│             │
└─────────────┘  Audio Stream └─────────────┘   Audio Data         └─────────────┘
       │                              │                                    │
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
   git clone <repository-url>
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

### Run the Server

```bash
python server.py
```

The server will start at `http://localhost:8000`.

## Usage

1. Open browser and visit `http://localhost:8000`
2. Click "Connect to Server" button to establish WebRTC connection
3. Enter text to convert in the text box
4. Click "Send Text" button
5. The system will play the converted speech in real-time

## Project Structure

```
webrtc-tts/
├── server.py              # FastAPI server, handles WebRTC and TTS
├── client.js              # Frontend WebRTC client
├── index.html             # Frontend interface
├── requirements.txt       # Python dependencies
├── README_CN.md          # Chinese documentation
└── README.md             # English documentation (this file)
```

## Core Components

### server.py
- **FastAPI Application**: Provides web interface and WebRTC signaling
- **SmartAudioTrack**: Intelligent audio track, manages audio queue and frame generation
- **AudioQueueManager**: Audio queue manager, buffers and slices audio data
- **stream_edge_tts_to_audio_queue**: Streaming EdgeTTS processing function

### client.js
- **WebRTC Connection**: Establishes PeerConnection with server
- **Audio Playback**: Receives and plays audio stream from server
- **Text Sending**: Sends text to server via DataChannel

## Technical Details

### Audio Processing Pipeline
1. User input text is sent to server via DataChannel
2. Server calls EdgeTTS to generate MP3 audio stream
3. FFmpeg converts MP3 to PCM format in real-time
4. PCM data is sliced and placed into audio queue
5. SmartAudioTrack reads data from queue and generates audio frames
6. Audio frames are transmitted to browser via WebRTC
7. Browser receives and plays audio

### Performance Optimizations
- **Streaming Processing**: Avoids generating temporary files, reduces disk I/O
- **Queue Buffering**: Smooths audio playback, prevents stuttering
- **Silence Frame Generation**: Generates silence when queue is empty, keeps connection alive

## Notes

1. **First Connection Latency**: Due to WebRTC connection establishment and TTS model loading, first use may have a few seconds delay
2. **Browser Permissions**: Browser may request microphone permission (for WebRTC), need to allow
3. **Network Requirements**: Stable network connection is required for audio stream quality
4. **FFmpeg Dependency**: Must have FFmpeg correctly installed and added to system PATH

## Troubleshooting

### Common Issues

1. **Cannot Connect to Server**
   - Check if server is running `python server.py`
   - Check firewall settings, ensure port 8000 is open

2. **No Sound**
   - Check browser console for error messages
   - Confirm FFmpeg is correctly installed `ffmpeg -version`
   - Check if browser audio settings are muted

3. **Audio Stuttering or Delay**
   - Check network connection quality
   - Reduce server load, close other resource-intensive programs

### Viewing Logs

Server logs show connection status and TTS processing progress, can be viewed with:
