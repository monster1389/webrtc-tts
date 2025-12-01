# WebRTC 实时文字转语音 (TTS)

基于 WebRTC 技术的实时文字转语音系统，使用 FastAPI + aiortc + EdgeTTS 实现低延迟音频流传输。

## 功能特点

- **实时音频流传输**：通过 WebRTC 实现低延迟的音频传输
- **流式 TTS 处理**：使用 EdgeTTS 进行文字到语音的实时转换
- **无需音频文件**：直接在内存中处理音频数据，不生成临时文件
- **智能音频队列**：基于队列的音频数据管理，支持连续语音播放
- **跨平台兼容**：支持现代浏览器，无需额外插件

## 技术架构

```
┌─────────────┐    WebRTC     ┌─────────────┐    HTTP/WebSocket    ┌─────────────┐
│   浏览器     │───────────────▶│   FastAPI   │─────────────────────▶│  EdgeTTS    │
│  (client.js) │               │  服务器     │                     │  服务       │
│             ◀───────────────│ (server.py) │◀─────────────────────│             │
└─────────────┘  音频流       └─────────────┘   音频数据           └─────────────┘
       │                              │                                    │
       │                              │                                    │
       │                ┌─────────────▼─────────────┐                     │
       │                │                           │                     │
       │                │     音频处理管道          │                     │
       │                │  ┌─────────────────────┐  │                     │
       └────────────────┼─▶│  SmartAudioTrack    │◀─┘                     │
                        │  │  • 音频队列管理     │                       │
                        │  │  • 流式帧生成       │                       │
                        │  └─────────────────────┘                       │
                        │            │                                   │
                        │            ▼                                   │
                        │  ┌─────────────────────┐                       │
                        │  │  AudioQueueManager  │                       │
                        │  │  • 队列缓冲         │                       │
                        │  │  • 数据切片         │                       │
                        │  └─────────────────────┘                       │
                        │            │                                   │
                        │            ▼                                   │
                        │  ┌─────────────────────┐                       │
                        └─▶│  FFmpeg 音频转换    │◀──────────────────────┘
                           │  • MP3 → PCM        │
                           │  • 重采样           │
                           └─────────────────────┘
```

## 安装和运行

### 系统要求

- Python 3.8+
- FFmpeg (用于音频格式转换)
- 现代浏览器 (Chrome 90+, Firefox 88+, Edge 90+)

### 安装步骤

1. 克隆项目或下载文件
   ```bash
   git clone <repository-url>
   cd webrtc-tts
   ```

2. 安装 Python 依赖
   ```bash
   pip install -r requirements.txt
   ```

3. 安装 FFmpeg
   - **Windows**: 使用 Chocolatey `choco install ffmpeg`
   - **macOS**: 使用 Homebrew `brew install ffmpeg`
   - **Linux**: `sudo apt-get install ffmpeg` (Ubuntu/Debian)

### 运行服务器

```bash
python server.py
```

服务器将在 `http://localhost:8000` 启动。

## 使用方法

1. 打开浏览器访问 `http://localhost:8000`
2. 点击"连接服务器"按钮建立 WebRTC 连接
3. 在文本框中输入要转换的文字
4. 点击"发送文字"按钮
5. 系统将实时播放转换后的语音

## 项目结构

```
webrtc-tts/
├── server.py              # FastAPI 服务器，处理 WebRTC 和 TTS
├── client.js              # 前端 WebRTC 客户端
├── index.html             # 前端界面
├── requirements.txt       # Python 依赖
├── README_CN.md          # 中文说明文档
└── README.md             # 英文说明文档
```

## 核心组件说明

### server.py
- **FastAPI 应用**: 提供 Web 界面和 WebRTC 信令
- **SmartAudioTrack**: 智能音频轨道，管理音频队列和帧生成
- **AudioQueueManager**: 音频队列管理器，缓冲和切片音频数据
- **stream_edge_tts_to_audio_queue**: 流式 EdgeTTS 处理函数

### client.js
- **WebRTC 连接**: 建立与服务器的 PeerConnection
- **音频播放**: 接收并播放服务器发送的音频流
- **文本发送**: 通过 DataChannel 发送文本到服务器

## 技术细节

### 音频处理流程
1. 用户输入文本通过 DataChannel 发送到服务器
2. 服务器调用 EdgeTTS 生成 MP3 音频流
3. FFmpeg 将 MP3 实时转换为 PCM 格式
4. PCM 数据被切片并放入音频队列
5. SmartAudioTrack 从队列读取数据并生成音频帧
6. 音频帧通过 WebRTC 传输到浏览器
7. 浏览器接收并播放音频

### 性能优化
- **流式处理**: 避免生成临时文件，减少磁盘 I/O
- **队列缓冲**: 平滑音频播放，避免卡顿
- **静音帧生成**: 队列为空时生成静音，保持连接活跃

## 注意事项

1. **首次连接延迟**: 由于需要建立 WebRTC 连接和加载 TTS 模型，首次使用可能有几秒延迟
2. **浏览器权限**: 浏览器可能会请求麦克风权限（用于 WebRTC），需要允许
3. **网络要求**: 需要稳定的网络连接以保证音频流质量
4. **FFmpeg 依赖**: 必须正确安装 FFmpeg 并添加到系统 PATH

## 故障排除

### 常见问题

1. **无法连接服务器**
   - 检查服务器是否正常运行 `python server.py`
   - 检查防火墙设置，确保 8000 端口开放

2. **没有声音**
   - 检查浏览器控制台是否有错误信息
   - 确认 FFmpeg 已正确安装 `ffmpeg -version`
   - 检查浏览器音频设置是否静音

3. **音频卡顿或延迟**
   - 检查网络连接质量
   - 降低服务器负载，关闭其他占用资源的程序

### 日志查看

服务器日志会显示连接状态和 TTS 处理进度，可以通过以下方式查看：
```bash
python server.py 2>&1 | tee server.log
```

## 许可证

本项目基于 MIT 许可证开源。

## 贡献

欢迎提交 Issue 和 Pull Request 来改进本项目。

## 联系方式

如有问题或建议，请通过项目仓库的 Issue 页面联系。
