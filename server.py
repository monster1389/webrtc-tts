# server.py（流式EdgeTTS版本）
import os
import logging
import asyncio
import tempfile
import numpy as np
import time
from fractions import Fraction
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
from edge_tts import Communicate
from av import AudioFrame

logging.basicConfig(level=logging.INFO)
app = FastAPI()
pcs = set()
ROOT = os.path.dirname(__file__)
TEMP_DIR = tempfile.gettempdir()

# ------------ 流式音频队列管理 ------------
class AudioQueueManager:
    """基于LiveTalking的音频队列管理器"""
    def __init__(self, sample_rate=48000, frame_ms=20):
        self.sample_rate = sample_rate
        self.chunk_size = int(sample_rate * frame_ms / 1000)  # 每帧样本数
        self.audio_queue = asyncio.Queue()
        self.is_playing = False
        self.current_audio_data = None
        self.current_index = 0

    async def put_audio_data(self, audio_data):
        """将音频数据放入队列"""
        await self.audio_queue.put(audio_data)

    async def get_next_frame(self):
        """获取下一帧音频数据"""
        if self.current_audio_data is None or self.current_index >= len(self.current_audio_data):
            # 获取新的音频数据
            try:
                self.current_audio_data = await asyncio.wait_for(self.audio_queue.get(), timeout=0.1)
                self.current_index = 0
                self.is_playing = True
            except asyncio.TimeoutError:
                # 队列为空，返回静音
                self.is_playing = False
                return None

        if self.current_audio_data is None:
            return None

        # 提取当前帧
        end_index = self.current_index + self.chunk_size
        if end_index > len(self.current_audio_data):
            # 音频数据不足，填充静音
            frame = np.concatenate([
                self.current_audio_data[self.current_index:],
                np.zeros(end_index - len(self.current_audio_data), dtype=np.float32)
            ])
            self.current_audio_data = None
            self.current_index = 0
        else:
            frame = self.current_audio_data[self.current_index:end_index]
            self.current_index = end_index

        return frame

# ------------ 智能音频轨道管理 ------------
class SmartAudioTrack(MediaStreamTrack):
    """
    智能音频轨道，支持动态切换音频源，播放结束后自动返回静音
    基于 LiveTalking 项目的 PlayerStreamTrack 设计模式
    """
    kind = "audio"

    def __init__(self, sample_rate=48000, frame_ms=20):
        super().__init__()
        self.sample_rate = sample_rate
        self.samples = int(self.sample_rate * frame_ms / 1000)
        self._current_player = None
        self._silence_mode = True
        self._frame_count = 0
        self._start_time = time.time()
        self.audio_queue = AudioQueueManager(sample_rate, frame_ms)
        self.task_queue = asyncio.Queue()
        self.worker = asyncio.create_task(self._worker_loop())


    async def recv(self):
        """接收音频帧 - 基于LiveTalking的流式设计"""
        # 检查音频队列是否有数据
        frame_data = await self.audio_queue.get_next_frame()
        
        if frame_data is None:
            # 队列为空，生成静音帧
            return await self._generate_silence_frame()
        
        # 将音频数据转换为AudioFrame
        frame = AudioFrame(format="s16", layout="mono", samples=self.samples)
        frame.pts = self._frame_count * self.samples
        frame.time_base = Fraction(1, self.sample_rate)
        frame.sample_rate = self.sample_rate
        
        # 将float32音频数据转换为int16
        audio_int16 = (frame_data * 32767).astype(np.int16).tobytes()
        frame.planes[0].update(audio_int16)
        self._frame_count += 1
        
        # 保持节奏
        await asyncio.sleep(self.samples / self.sample_rate)
        return frame

    async def _generate_silence_frame(self):
        """生成静音音频帧"""
        frame = AudioFrame(format="s16", layout="mono", samples=self.samples)
        frame.pts = self._frame_count * self.samples
        frame.time_base = Fraction(1, self.sample_rate)
        frame.sample_rate = self.sample_rate
        
        silence = np.zeros(self.samples, dtype=np.int16).tobytes()
        frame.planes[0].update(silence)
        self._frame_count += 1
        
        # 保持节奏
        await asyncio.sleep(self.samples / self.sample_rate)
        return frame
    
    async def _worker_loop(self):
        """串行执行每个 TTS 任务"""
        while True:
            text = await self.task_queue.get()
            try:
                logging.info(f"TTS worker 开始处理: {text}")
                await stream_edge_tts_to_audio_queue(text, self.audio_queue)
                logging.info("TTS worker 完成播放")
            except Exception as e:
                logging.exception("TTS worker 发生异常: %s", e)
            finally:
                self.task_queue.task_done()

# ------------ 流式 EdgeTTS 处理 ------------
async def stream_edge_tts_to_audio_queue(text, audio_queue_manager):
    try:
        logging.info("开始流式EdgeTTS处理")

        communicate = Communicate(text, voice="zh-CN-XiaoyiNeural")

        # 启动 ffmpeg
        ffmpeg = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-loglevel", "quiet",
            "-f", "mp3",
            "-i", "pipe:0",
            "-f", "f32le",
            "-ac", "1",
            "-ar", str(audio_queue_manager.sample_rate),
            "pipe:1",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
        )

        # ring buffer
        pcm_buffer = bytearray()
        bytes_per_chunk = audio_queue_manager.chunk_size * 4  # float32

        # PCM 输入协程
        async def read_pcm():
            while True:
                # 一次读大一点，避免频繁切换
                data = await ffmpeg.stdout.read(4096)
                if not data:
                    break

                pcm_buffer.extend(data)

                # 按 chunk_size 切片
                while len(pcm_buffer) >= bytes_per_chunk:
                    raw = pcm_buffer[:bytes_per_chunk]
                    del pcm_buffer[:bytes_per_chunk]

                    samples = np.frombuffer(raw, dtype=np.float32)
                    await audio_queue_manager.put_audio_data(samples)

        read_task = asyncio.create_task(read_pcm())

        # 写入 MP3 到 ffmpeg
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                ffmpeg.stdin.write(chunk["data"])
                await ffmpeg.stdin.drain()

        ffmpeg.stdin.close()
        await ffmpeg.stdin.wait_closed()

        await read_task
        await ffmpeg.wait()

        logging.info("EdgeTTS 流式处理完成")

    except Exception as e:
        logging.exception("流式EdgeTTS处理失败: %s", e)

# ------------ 路由 ------------
@app.get("/", response_class=HTMLResponse)
async def index():
    with open(os.path.join(ROOT, "index.html"), "r", encoding="utf-8") as f:
        return f.read()

@app.get("/client.js", response_class=HTMLResponse)
async def js():
    with open(os.path.join(ROOT, "client.js"), "r", encoding="utf-8") as f:
        return HTMLResponse(f.read(), media_type="application/javascript")

@app.post("/offer")
async def offer(request: Request):
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    pc = RTCPeerConnection()
    pcs.add(pc)
    logging.info("新连接来自: %s", request.client.host)

    # 创建智能音频轨道
    smart_audio_track = SmartAudioTrack()
    
    # 添加智能音频轨道
    audio_sender = pc.addTrack(smart_audio_track)

    @pc.on("datachannel")
    def on_datachannel(channel):
        logging.info("DataChannel 创建: %s", channel.label)

        @channel.on("message")
        async def on_message(message):
            logging.info("收到文本: %s", message)

            # 使用流式EdgeTTS处理，不产生文件
            try:
                await smart_audio_track.task_queue.put(message)
                logging.info("流式EdgeTTS处理完成，音频数据已放入队列")
            except Exception as e:
                logging.exception("流式TTS处理失败: %s", e)

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        logging.info("连接状态: %s", pc.connectionState)
        if pc.connectionState == "failed":
            await pc.close()
            pcs.discard(pc)

    # 设置远端 SDP 并返回 answer（与浏览器协商）
    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}

@app.on_event("shutdown")
async def on_shutdown():
    logging.info("关闭所有 PeerConnections")
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()
