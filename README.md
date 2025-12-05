# WebRTC 实时 LLM + TTS 系统

基于 WebRTC 技术的实时对话 AI 系统，集成大语言模型 (LLM) 和文字转语音 (TTS) 技术，实现低延迟音频流传输和交互式对话。

## 功能特点

- **实时音频流传输**：通过 WebRTC 实现低延迟的音频传输
- **LLM 集成**：支持多种 LLM 提供商（OpenAI、DashScope、本地测试）
- **流式 TTS 处理**：使用 EdgeTTS 进行文字到语音的实时转换
- **多提供商支持**：通过配置轻松切换不同的 LLM 提供商
- **环境变量配置**：使用环境变量安全管理 API 密钥
- **无需音频文件**：直接在内存中处理音频数据，不生成临时文件
- **智能音频队列**：基于队列的音频数据管理，支持连续语音播放
- **跨平台兼容**：支持现代浏览器，无需额外插件
- **流式 LLM 响应**：实时处理 LLM 响应并与 TTS 同步输出

## 技术架构

```
┌─────────────┐    WebRTC     ┌─────────────┐    HTTP/WebSocket    ┌─────────────┐
│   浏览器     │───────────────▶│   FastAPI   │─────────────────────▶│   LLM       │
│  (client.js) │               │  服务器     │                     │   提供商    │
│             ◀───────────────│ (server.py) │◀─────────────────────│  (OpenAI/   │
└─────────────┘  音频流       └─────────────┘   文本流             │  DashScope/ │
       │                              │                                    │ 本地)
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
   git clone https://github.com/monster1389/webrtc-tts.git
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

4. 配置环境变量（用于 API 密钥）
   ```bash
   # 对于 OpenAI/DeepSeek
   export OPENAI_API_KEY="your-api-key-here"
   # 对于阿里云 DashScope
   export DASHSCOPE_API_KEY="your-api-key-here"
   ```

### 运行服务器

```bash
uvicorn server:app --reload
```

服务器将在 `http://localhost:8000` 启动。

## 配置

系统使用 `config.json` 进行配置。默认情况下，API 密钥从环境变量加载以确保安全：

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
        "你好！这是一个测试响应。",
        "很高兴为您服务。",
        "这是一个流式响应的演示。",
        "WebRTC + LLM + TTS 系统正在正常工作。",
        "您可以轻松切换不同的LLM提供商。"
      ]
    }
  }
}
```

### 支持的 LLM 提供商

1. **OpenAI**: 兼容 OpenAI API 和 DeepSeek API
2. **DashScope**: 阿里云通义千问模型
3. **Local**: 测试模式，使用预定义响应（无需 API 密钥）

## 使用方法

1. 打开浏览器访问 `http://localhost:8000`
2. 点击"连接服务器"按钮建立 WebRTC 连接
3. 在文本框中输入您的消息
4. 点击"发送文字"按钮
5. 系统将：
   - 将您的消息发送到配置的 LLM 提供商
   - 实时流式接收 LLM 响应
   - 使用 EdgeTTS 将文本转换为语音
   - 通过浏览器播放音频响应

## 项目结构

```
webrtc-tts/
├── server.py              # FastAPI 服务器，处理 WebRTC、LLM 和 TTS
├── client.js              # 前端 WebRTC 客户端
├── index.html             # 前端界面
├── requirements.txt       # Python 依赖
├── config.json           # 配置文件（API 密钥从环境变量获取）
├── README_CN.md          # 中文说明文档
├── README.md             # 英文说明文档
├── llm/                  # LLM 集成模块
│   ├── config.py         # 配置加载器
│   ├── factory.py        # LLM 提供商工厂
│   └── provider.py       # 基础提供商接口
└── providers/            # LLM 提供商实现
    ├── dashscope_provider.py  # 阿里云 DashScope 提供商
    ├── local_provider.py      # 本地测试提供商
    └── openai_provider.py     # OpenAI/DeepSeek 提供商
```

## 核心组件说明

### server.py
- **FastAPI 应用**: 提供 Web 界面和 WebRTC 信令
- **SmartAudioTrack**: 智能音频轨道，管理音频队列和帧生成
- **AudioQueueManager**: 音频队列管理器，缓冲和切片音频数据
- **LLM 集成**: 流式处理 LLM 响应并与 TTS 同步
- **任务管理**: 正确清理 WebRTC 连接和后台任务

### client.js
- **WebRTC 连接**: 建立与服务器的 PeerConnection
- **音频播放**: 接收并播放服务器发送的音频流
- **文本发送**: 通过 DataChannel 发送文本到服务器
- **实时更新**: 在 LLM 响应生成时显示文本

### LLM 模块
- **提供商模式**: 不同 LLM 提供商的抽象接口
- **流式支持**: 实时流式传输 LLM 响应
- **可配置**: 通过配置轻松切换提供商

## 技术细节

### 音频处理流程
1. 用户输入文本通过 DataChannel 发送到服务器
2. 服务器将文本发送到配置的 LLM 提供商
3. LLM 响应实时流式返回
4. 每个文本块发送到 EdgeTTS 生成 MP3 音频
5. FFmpeg 将 MP3 实时转换为 PCM 格式
6. PCM 数据被切片并放入音频队列
7. SmartAudioTrack 从队列读取数据并生成音频帧
8. 音频帧通过 WebRTC 传输到浏览器
9. 浏览器接收并播放音频，同时显示文本

### 性能优化
- **流式处理**: 避免生成临时文件，减少磁盘 I/O
- **队列缓冲**: 平滑音频播放，避免卡顿
- **静音帧生成**: 队列为空时生成静音，保持连接活跃
- **任务取消**: 连接关闭时正确清理后台任务

## 安全注意事项

- **API 密钥安全**: API 密钥从环境变量加载，不存储在 config.json 中
- **环境变量**: 使用 `OPENAI_API_KEY` 和 `DASHSCOPE_API_KEY` 分别配置提供商
- **本地测试模式**: 使用 "local" 提供商进行测试，无需 API 密钥

## 故障排除

### 常见问题

1. **无法连接服务器**
   - 检查服务器是否正常运行 `python server.py`
   - 检查防火墙设置，确保 8000 端口开放
   - 检查浏览器控制台是否有 WebRTC 错误

2. **没有声音**
   - 检查浏览器控制台是否有错误信息
   - 确认 FFmpeg 已正确安装 `ffmpeg -version`
   - 检查浏览器音频设置是否静音
   - 验证环境变量是否正确设置

3. **LLM 无响应**
   - 检查 API 密钥是否在环境变量中设置
   - 验证网络连接到 LLM 提供商 API
   - 检查服务器日志中的认证错误

4. **音频卡顿或延迟**
   - 检查网络连接质量
   - 降低服务器负载，关闭其他占用资源的程序
   - 检查 FFmpeg 安装和性能

### 日志查看

服务器日志显示连接状态、LLM 处理和 TTS 进度：

```bash
# 运行服务器并启用详细日志
uvicorn server:app --reload 2>&1 | tee server.log
```

## 许可证

本项目基于 MIT 许可证开源。

## 贡献

欢迎提交 Issue 和 Pull Request 来改进本项目。

## 联系方式

如有问题或建议，请通过项目仓库的 Issue 页面联系。
