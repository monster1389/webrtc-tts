# server.py（整合版：带 PeerConnection 任务管理与可取消的 TTS/ffmpeg 清理）
import os
import logging
import asyncio
import tempfile
import json
import numpy as np
import time
from fractions import Fraction
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
from edge_tts import Communicate
from av import AudioFrame

# LLM 模块导入（保留你原来的 LLM 接口）
from llm.config import load_config
from llm.factory import create_llm_provider

logging.basicConfig(level=logging.INFO)
app = FastAPI()
pcs = set()
ROOT = os.path.dirname(__file__)
TEMP_DIR = tempfile.gettempdir()

# ------------ LLM 初始化 ------------
try:
    llm_config = load_config()
    logging.info(f"加载配置成功: {llm_config.get('llm_provider', 'unknown')}")
    llm_provider = create_llm_provider(llm_config)
    logging.info(f"LLM 提供者初始化成功: {llm_provider.get_name()}")
except Exception as e:
    logging.error(f"LLM 提供者初始化失败: {e}", exc_info=True)
    llm_provider = None

# ------------ 辅助：为每个 pc 管理任务的工具函数 ------------
def create_pc_task(pc: RTCPeerConnection, coro):
    """创建任务并绑定到 PeerConnection，方便统一取消与跟踪"""
    task = asyncio.create_task(coro)
    if not hasattr(pc, "_tasks"):
        pc._tasks = []
    pc._tasks.append(task)
    return task

async def cancel_pc_tasks(pc: RTCPeerConnection):
    """取消并等待 pc 的所有后台任务（安全清理）"""
    if not hasattr(pc, "_tasks"):
        return
    tasks = list(pc._tasks)
    if not tasks:
        return

    logging.info(f"取消 {len(tasks)} 个与此 PeerConnection 关联的后台任务...")
    for t in tasks:
        if not t.done():
            t.cancel()

    # 等待所有任务结束（忽略异常）
    try:
        await asyncio.gather(*tasks, return_exceptions=True)
    except Exception:
        logging.exception("等待 pc 任务退出时发生异常（已忽略）")

    # 清理列表
    pc._tasks.clear()
    logging.info("后台任务已全部取消并清理完毕。")

# ------------ 流式音频队列管理（保留原实现，略作小改动） ------------
class AudioQueueManager:
    def __init__(self, sample_rate=48000, frame_ms=20):
        self.sample_rate = sample_rate
        self.chunk_size = int(sample_rate * frame_ms / 1000)
        self.audio_queue = asyncio.Queue()
        self.is_playing = False
        self.current_audio_data = None
        self.current_tag = None
        self.current_index = 0
        self.tag_sequence = []
        self.tag_data_map = {}
        self.active_tag = None

    async def put_audio_data(self, audio_data, tag=None):
        if tag and tag not in self.tag_sequence:
            self.tag_sequence.append(tag)
        if tag not in self.tag_data_map:
            self.tag_data_map[tag] = []
        self.tag_data_map[tag].append(audio_data)
        if self.active_tag is None and tag:
            self.active_tag = tag
        await self.audio_queue.put((audio_data, tag))

    async def get_next_frame(self):
        if self.current_audio_data is None or self.current_index >= len(self.current_audio_data):
            try:
                self.current_audio_data, self.current_tag = await asyncio.wait_for(self.audio_queue.get(), timeout=0.1)
                self.current_index = 0
                self.is_playing = True
                if self.current_tag and self.current_tag != self.active_tag:
                    self.active_tag = self.current_tag
            except asyncio.TimeoutError:
                self.is_playing = False
                return None, self.active_tag

        if self.current_audio_data is None:
            return None, self.active_tag

        end_index = self.current_index + self.chunk_size
        if end_index > len(self.current_audio_data):
            frame = np.concatenate([
                self.current_audio_data[self.current_index:],
                np.zeros(end_index - len(self.current_audio_data), dtype=np.float32)
            ])
            self.current_audio_data = None
            self.current_index = 0
        else:
            frame = self.current_audio_data[self.current_index:end_index]
            self.current_index = end_index

        return frame, self.current_tag

    def get_active_tag(self):
        return self.active_tag

    def has_tag_data(self, tag):
        return tag in self.tag_data_map and len(self.tag_data_map[tag]) > 0

    def clear_tag_data(self, tag):
        if tag in self.tag_data_map:
            del self.tag_data_map[tag]
        if tag in self.tag_sequence:
            self.tag_sequence.remove(tag)

# ------------ 智能音频轨道（不在 __init__ 中创建后台任务） ------------
class SmartAudioTrack(MediaStreamTrack):
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
        self.text_buffer = ""
        self.buffer_lock = asyncio.Lock()
        self.min_buffer_size = 20
        self.sentence_endings = {'.', '。', '!', '！', '?', '？', ';', '；', ',', '，', ':', '：', '\n'}
        # 不在 __init__ 创建 worker；由 offer() 创建并将任务归属于 pc
        # 标签相关属性
        self.tag_text_map = {}
        self.channel = None
        self.message_counter = 0
        self.message_lock = asyncio.Lock()
        # 标志位，用于外部通知关闭（可选）
        self._closing = False

    async def recv(self):
        frame_data, tag = await self.audio_queue.get_next_frame()
        if tag and tag in self.tag_text_map and self.tag_text_map[tag]:
            await self._send_text_for_tag(tag)

        if frame_data is None:
            return await self._generate_silence_frame()

        frame = AudioFrame(format="s16", layout="mono", samples=self.samples)
        frame.pts = self._frame_count * self.samples
        frame.time_base = Fraction(1, self.sample_rate)
        frame.sample_rate = self.sample_rate

        # float32 -> int16
        audio_int16 = (frame_data * 32767).astype(np.int16).tobytes()
        frame.planes[0].update(audio_int16)
        self._frame_count += 1

        await asyncio.sleep(self.samples / self.sample_rate)
        return frame

    async def _generate_silence_frame(self):
        frame = AudioFrame(format="s16", layout="mono", samples=self.samples)
        frame.pts = self._frame_count * self.samples
        frame.time_base = Fraction(1, self.sample_rate)
        frame.sample_rate = self.sample_rate
        silence = np.zeros(self.samples, dtype=np.int16).tobytes()
        frame.planes[0].update(silence)
        self._frame_count += 1
        await asyncio.sleep(self.samples / self.sample_rate)
        return frame

    async def add_text_to_buffer(self, text: str, tag: str = None):
        async with self.buffer_lock:
            if tag:
                if tag not in self.tag_text_map:
                    self.tag_text_map[tag] = []
                self.tag_text_map[tag].append(text)
                logging.debug(f"已将chunk添加到tag_text_map队列 (标签: {tag}): {text[:50]}...")
            self.text_buffer += text
            should_flush = False
            if len(self.text_buffer) >= self.min_buffer_size * 3:
                should_flush = True
            elif self.text_buffer and self.text_buffer[-1] in self.sentence_endings:
                should_flush = True
            if should_flush and self.text_buffer.strip():
                text_to_process = self.text_buffer
                self.text_buffer = ""
                await self.task_queue.put((text_to_process, tag))
                logging.debug(f"缓冲区已刷新并发送到TTS (标签: {tag}): {text_to_process[:50]}...")

    async def _send_text_for_tag(self, tag: str):
        if not self.channel or self.channel.readyState != "open":
            logging.warning(f"无法发送标签 {tag} 的文本: DataChannel 不可用")
            return
        if tag not in self.tag_text_map:
            logging.warning(f"标签 {tag} 没有对应的文本映射")
            return
        text_queue = self.tag_text_map[tag]
        if not text_queue:
            logging.warning(f"标签 {tag} 的文本队列为空")
            return
        text_chunk = text_queue.pop(0)
        if not text_queue:
            del self.tag_text_map[tag]
            logging.debug(f"标签 {tag} 的文本队列已清空")
        try:
            self.channel.send(json.dumps({
                "type": "text_chunk",
                "content": text_chunk,
                "tag": tag
            }))
            logging.info(f"已发送标签 {tag} 的文本chunk到前端: {text_chunk[:50]}...")
        except Exception as e:
            logging.exception(f"发送标签 {tag} 的文本chunk失败: {e}")

    async def flush_buffer(self, tag: str = None):
        async with self.buffer_lock:
            if self.text_buffer.strip():
                text_to_process = self.text_buffer
                self.text_buffer = ""
                await self.task_queue.put((text_to_process, tag))
                logging.debug(f"缓冲区强制刷新 (标签: {tag}): {text_to_process[:50]}...")

    async def _worker_loop(self):
        """串行执行每个 TTS 任务，支持标签；会响应取消"""
        logging.info("SmartAudioTrack worker 启动")
        try:
            while True:
                try:
                    task = await self.task_queue.get()
                except asyncio.CancelledError:
                    logging.info("SmartAudioTrack worker 捕获到取消信号，退出循环")
                    break

                try:
                    if isinstance(task, tuple) and len(task) == 2:
                        text, tag = task
                        logging.info(f"TTS worker 开始处理 (标签: {tag}): {text[:100]}...")
                        await stream_edge_tts_to_audio_queue(text, self.audio_queue, tag, max_retries=3)
                    else:
                        text = task
                        logging.info(f"TTS worker 开始处理 (无标签): {text[:100]}...")
                        await stream_edge_tts_to_audio_queue(text, self.audio_queue, None, max_retries=3)
                    logging.info("TTS worker 本次任务完成")
                except asyncio.CancelledError:
                    logging.info("TTS worker 在处理任务时被取消")
                    break
                except Exception as e:
                    logging.exception("TTS worker 发生异常: %s", e)
                finally:
                    try:
                        self.task_queue.task_done()
                    except Exception:
                        pass
        finally:
            logging.info("SmartAudioTrack worker 已退出")

    async def close(self):
        """外部可调用的关闭方法，标记关闭并清理"""
        self._closing = True
        # 清空 text queues
        self.tag_text_map.clear()
        # 清空 audio queue
        try:
            while not self.task_queue.empty():
                self.task_queue.get_nowait()
                self.task_queue.task_done()
        except Exception:
            pass

# ------------ 流式 EdgeTTS 处理（增加取消/清理逻辑） ------------
async def stream_edge_tts_to_audio_queue(text, audio_queue_manager, tag=None, max_retries=3):
    if not text or not text.strip():
        logging.warning("EdgeTTS接收到空文本，跳过处理")
        return

    text = text.strip()
    logging.info(f"开始流式EdgeTTS处理 (标签: {tag}): '{text[:50]}...'")

    for attempt in range(max_retries):
        ffmpeg = None
        read_task = None
        communicate = None
        pcm_buffer = bytearray()
        bytes_per_chunk = audio_queue_manager.chunk_size * 4  # float32
        audio_received = False

        try:
            logging.info(f"EdgeTTS尝试 {attempt + 1}/{max_retries}")
            communicate = Communicate(text, voice="zh-CN-XiaoyiNeural")

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
                stderr=asyncio.subprocess.PIPE,
            )

            async def read_pcm():
                nonlocal audio_received, pcm_buffer
                try:
                    while True:
                        data = await ffmpeg.stdout.read(4096)
                        if not data:
                            break
                        pcm_buffer.extend(data)
                        audio_received = True
                        while len(pcm_buffer) >= bytes_per_chunk:
                            raw = pcm_buffer[:bytes_per_chunk]
                            del pcm_buffer[:bytes_per_chunk]
                            samples = np.frombuffer(raw, dtype=np.float32)
                            await audio_queue_manager.put_audio_data(samples, tag)
                except asyncio.CancelledError:
                    logging.info("read_pcm 被取消")
                    raise
                except Exception as e:
                    logging.exception(f"read_pcm 异常: {e}")
                    raise

            read_task = asyncio.create_task(read_pcm())

            try:
                async for chunk in communicate.stream():
                    # 在取消点检查
                    await asyncio.sleep(0)
                    if chunk["type"] == "audio":
                        if ffmpeg.stdin is not None:
                            try:
                                ffmpeg.stdin.write(chunk["data"])
                                await ffmpeg.stdin.drain()
                            except Exception as e:
                                logging.warning(f"写入 ffmpeg.stdin 失败: {e}")
            except asyncio.CancelledError:
                logging.info("EdgeTTS 的 communicate.stream 正在被取消")
                # propagate cancellation
                raise
            except Exception as e:
                logging.warning(f"EdgeTTS 流式读取异常: {e}")
                # 尝试读取 stderr
                try:
                    if ffmpeg and ffmpeg.stderr:
                        stderr_data = await ffmpeg.stderr.read()
                        if stderr_data:
                            logging.error(f"ffmpeg stderr: {stderr_data.decode('utf-8', errors='ignore')}")
                except Exception:
                    pass

            if ffmpeg.stdin is not None:
                try:
                    ffmpeg.stdin.close()
                    await ffmpeg.stdin.wait_closed()
                except Exception:
                    pass

            # 等待读取任务完成或取消
            try:
                await read_task
            except asyncio.CancelledError:
                logging.info("read_task 被取消，继续清理")
                raise

            return_code = await ffmpeg.wait()
            if return_code != 0:
                logging.warning(f"ffmpeg 非零退出: {return_code}")
                try:
                    stderr_data = await ffmpeg.stderr.read()
                    if stderr_data:
                        logging.error(f"ffmpeg stderr: {stderr_data.decode('utf-8', errors='ignore')}")
                except Exception:
                    pass

            if not audio_received:
                raise Exception("未接收到音频数据")

            logging.info(f"EdgeTTS 流式处理完成 (标签: {tag}): '{text[:30]}...'")
            return

        except asyncio.CancelledError:
            logging.info("EdgeTTS 任务被取消，进行清理")
            # 取消 read_task
            if read_task and not read_task.done():
                read_task.cancel()
                try:
                    await read_task
                except Exception:
                    pass
            # 关闭 stdin
            try:
                if ffmpeg and ffmpeg.stdin:
                    ffmpeg.stdin.close()
                    await ffmpeg.stdin.wait_closed()
            except Exception:
                pass
            # kill ffmpeg
            try:
                if ffmpeg and ffmpeg.returncode is None:
                    ffmpeg.kill()
                    await ffmpeg.wait()
            except Exception:
                pass
            raise
        except Exception as e:
            logging.exception(f"EdgeTTS 尝试 {attempt + 1} 失败: {e}")
            # 清理子任务/子进程
            if read_task and not read_task.done():
                read_task.cancel()
                try:
                    await read_task
                except Exception:
                    pass
            try:
                if ffmpeg and ffmpeg.returncode is None:
                    ffmpeg.kill()
                    await ffmpeg.wait()
            except Exception:
                pass
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                logging.info(f"等待 {wait_time} 秒后重试...")
                await asyncio.sleep(wait_time)
            else:
                logging.error(f"EdgeTTS 处理失败，重试 {max_retries} 次后放弃 (标签: {tag}): '{text[:30]}...'")
                raise

# ------------ 路由和 WebRTC 逻辑（主逻辑在这里） ------------
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
    # 初始化任务列表与标志
    pc._tasks = []
    pc._cancelled = False

    pcs.add(pc)
    logging.info("新连接来自: %s", request.client.host)

    # 创建智能音频轨道（注意：不在内部创建 worker）
    smart_audio_track = SmartAudioTrack()

    # 将轨道加入到 PeerConnection
    audio_sender = pc.addTrack(smart_audio_track)

    # 启动 SmartAudioTrack worker 并把任务关联到 pc
    create_pc_task(pc, smart_audio_track._worker_loop())

    @pc.on("datachannel")
    def on_datachannel(channel):
        logging.info("DataChannel 创建: %s", channel.label)
        smart_audio_track.channel = channel

        @channel.on("message")
        def on_message_local(message):
            # datachannel 的回调不能直接 await，所以把实际处理放到 handle_message 协程并注册为 pc 任务
            create_pc_task(pc, handle_message(pc, smart_audio_track, channel, message))

    async def handle_message(pc: RTCPeerConnection, smart_audio_track: SmartAudioTrack, channel, message: str):
        """把原 on_message 的逻辑抽成协程，便于用 create_pc_task 追踪与取消"""
        logging.info("收到文本: %s", message)

        if llm_provider is None:
            error_msg = "LLM 提供者未初始化，请检查配置"
            logging.error(error_msg)
            try:
                if channel.readyState == "open":
                    channel.send(json.dumps({"type": "error", "error": error_msg}))
            except Exception:
                pass
            return

        async with smart_audio_track.message_lock:
            tts_started = False
            tag = None
            try:
                smart_audio_track.message_counter += 1
                tag = f"msg_{smart_audio_track.message_counter}"
                logging.info(f"为本次LLM响应生成标签: {tag}")
                smart_audio_track.tag_text_map[tag] = []

                if channel.readyState == "open":
                    try:
                        channel.send(json.dumps({"type": "tts_start", "text": "正在处理LLM响应..."}))
                    except Exception:
                        pass

                logging.info("开始流式 LLM 处理")
                # 开始流式 LLM
                async for chunk in llm_provider.generate_response_stream(message):
                    # 如果此任务被取消，会在 await 时抛出 CancelledError
                    if chunk.strip():
                        await smart_audio_track.add_text_to_buffer(chunk, tag)
                        logging.debug(f"TTS chunk已添加到缓冲区 (标签: {tag}): {chunk[:50]}...")
                        if not tts_started:
                            tts_started = True
                            if channel.readyState == "open":
                                try:
                                    channel.send(json.dumps({"type": "tts_start", "text": "开始生成语音..."}))
                                except Exception:
                                    pass

                # 强制刷新剩余缓冲区
                await smart_audio_track.flush_buffer(tag)

                if channel.readyState == "open":
                    try:
                        channel.send(json.dumps({"type": "tts_complete"}))
                    except Exception:
                        pass

                logging.info(f"TTS 流式处理完成 (标签: {tag})")

            except asyncio.CancelledError:
                logging.info(f"handle_message for {tag} 被取消（连接可能断开）")
                # 可能希望通知前端，但连接已经断开或正在断开，忽略
                try:
                    await smart_audio_track.flush_buffer(tag)
                except Exception:
                    pass
                raise
            except Exception as e:
                error_msg = f"LLM 处理失败: {str(e)}"
                logging.exception(error_msg)
                try:
                    if channel.readyState == "open":
                        channel.send(json.dumps({"type": "error", "error": error_msg}))
                except Exception:
                    pass

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        logging.info("连接状态: %s", pc.connectionState)
        # 在失败 / 断开 / 关闭 时统一取消任务并关闭 PC
        if pc.connectionState in ("failed", "closed", "disconnected"):
            if getattr(pc, "_cancelled", False):
                # 已经开始取消流程，避免重复
                return
            pc._cancelled = True

            # 标记并取消 SmartAudioTrack（触发 task_queue 退出）
            try:
                await smart_audio_track.close()
            except Exception:
                pass

            # 取消并等待 pc 上挂载的所有任务
            try:
                await cancel_pc_tasks(pc)
            except Exception:
                logging.exception("取消 pc 任务时出现异常")

            # 最后关闭 PeerConnection
            try:
                await pc.close()
            except Exception:
                logging.exception("关闭 pc 时出错")
            pcs.discard(pc)
            logging.info("PeerConnection 已关闭并从集合中移除")

    # 设置远端 SDP 并返回 answer（与浏览器协商）
    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}

@app.on_event("shutdown")
async def on_shutdown():
    logging.info("服务关闭：开始关闭所有 PeerConnections")
    coros = []
    for pc in list(pcs):
        try:
            # 标记取消并尝试取消所有任务
            pc._cancelled = True
            coros.append(cancel_pc_tasks(pc))
            coros.append(pc.close())
        except Exception:
            logging.exception("关闭 pc 时发生异常")
    if coros:
        await asyncio.gather(*coros, return_exceptions=True)
    pcs.clear()
    logging.info("所有 PeerConnections 已清理完成")
