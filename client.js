let pc = null;
let dc = null;
let currentResponse = ""; // 当前响应的完整文本
let userInputQueue = []; // 存储用户输入的队列（数组作为队列）
let currentTag = null; // 当前响应的标签

async function start() {
    const audio = document.getElementById("audio");
    const connectionStatus = document.getElementById("connectionStatus");
    const audioStatus = document.getElementById("audioStatus");

    // 更新状态
    connectionStatus.textContent = "正在连接...";
    connectionStatus.className = "status streaming";
    
    pc = new RTCPeerConnection();

    // 浏览器希望接收音频
    pc.addTransceiver("audio", { direction: "recvonly" });

    pc.ontrack = (event) => {
        console.log("🎵 ontrack 事件触发 -", new Date().toLocaleTimeString());
        console.log("📡 收到音频流，流数量:", event.streams.length);
        
        if (event.streams[0]) {
            const stream = event.streams[0];
            console.log("🎧 音频流信息:", {
                id: stream.id,
                活跃: stream.active,
                轨道数量: stream.getAudioTracks().length
            });
            
            const tracks = stream.getAudioTracks();
            tracks.forEach((track, index) => {
                console.log(`🎤 音频轨道 ${index + 1}:`, {
                    id: track.id,
                    启用: track.enabled,
                    静音: track.muted,
                    状态: track.readyState,
                    类型: track.kind
                });
            });
        }
        
        console.log("🔗 设置音频源并播放");
        audio.srcObject = event.streams[0];
        audio.play().catch(e => {
            console.warn("播放失败:", e);
            audioStatus.textContent = "播放失败: " + e.message;
            audioStatus.className = "status error";
        });
        
        audioStatus.textContent = "正在播放音频...";
        audioStatus.className = "status streaming";
    };

    // 创建DataChannel
    dc = pc.createDataChannel("chat");
    
    // DataChannel事件处理
    dc.onopen = () => {
        console.log("DataChannel opened");
        connectionStatus.textContent = "已连接";
        connectionStatus.className = "status";
    };
    
    dc.onclose = () => {
        console.log("DataChannel closed");
        connectionStatus.textContent = "连接已关闭";
        connectionStatus.className = "status";
    };
    
    dc.onerror = (error) => {
        console.error("DataChannel error:", error);
        connectionStatus.textContent = "连接错误";
        connectionStatus.className = "status error";
    };
    
    // 监听DataChannel消息（流式文本）
    dc.onmessage = (event) => {
        const data = event.data;
        console.log("收到消息:", data);
        
        // 解析消息类型
        try {
            const message = JSON.parse(data);
            
            if (message.type === "text_chunk") {
                // 文本流式片段（现在包含tag字段，没有is_final字段）
                handleTextChunk(message.content, message.tag);
            } else if (message.type === "text_complete") {
                // 文本生成完成
                handleTextComplete(message.content);
            } else if (message.type === "error") {
                // 错误消息
                handleError(message.error);
            } else if (message.type === "tts_start") {
                // TTS开始
                handleTTSStart(message.text);
            } else if (message.type === "tts_complete") {
                // TTS完成
                handleTTSComplete();
            }
        } catch (e) {
            // 如果不是JSON，直接显示文本
            console.log("收到非JSON消息，直接显示:", data);
            handleTextChunk(data, null);
        }
    };

    await navigator.mediaDevices.getUserMedia({ audio: true });

    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);

    const response = await fetch("/offer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sdp: offer.sdp, type: offer.type })
    });
    const answer = await response.json();
    await pc.setRemoteDescription(answer);

    console.log("连接成功");
    connectionStatus.textContent = "连接成功";
    connectionStatus.className = "status";
}

// 处理文本流式片段（通过检测tag变化来刷新文本）
function handleTextChunk(chunk, tag) {
    const responseText = document.getElementById("responseText");
    const responseStatus = document.getElementById("responseStatus");
    
    console.log(`处理文本chunk: "${chunk}" (标签: ${tag}, 当前标签: ${currentTag})`);
    
    // 检测标签变化：如果tag变化，开始新的响应
    if (tag !== currentTag) {
        console.log(`标签变化，开始新响应: ${currentTag} -> ${tag}`);
        
        // 重置响应状态
        currentResponse = "";
        currentTag = tag;
        
        // 检查是否有用户输入在队列中
        if (userInputQueue.length > 0) {
            // 从队列中取出第一个用户输入
            const userInput = userInputQueue.shift();
            console.log("从队列中取出用户输入:", userInput, "剩余队列长度:", userInputQueue.length);
            
            // 显示用户输入和AI回复的开始
            responseText.textContent = `用户: ${userInput}\n\nAI: ${chunk}`;
            currentResponse = `用户: ${userInput}\n\nAI: ${chunk}`;
        } else {
            // 没有用户输入，只显示AI回复
            responseText.textContent = chunk;
            currentResponse = chunk;
        }
        
        responseStatus.textContent = "正在生成响应...";
        responseStatus.className = "status streaming";
    } else {
        // 继续流式响应（相同标签）
        console.log(`继续相同标签的响应: ${tag}`);
        // 直接将新的chunk追加到当前响应
        currentResponse += chunk;
        responseText.textContent = currentResponse;
    }
    
    // 滚动到底部
    responseText.scrollTop = responseText.scrollHeight;
}

// 处理文本生成完成
function handleTextComplete(fullText) {
    const responseText = document.getElementById("responseText");
    const responseStatus = document.getElementById("responseStatus");
    
    responseText.textContent = fullText;
    currentResponse = fullText;
    
    responseStatus.textContent = "响应完成";
    responseStatus.className = "status";
    
    // 滚动到底部
    responseText.scrollTop = responseText.scrollHeight;
}

// 处理错误
function handleError(error) {
    const responseText = document.getElementById("responseText");
    const responseStatus = document.getElementById("responseStatus");
    
    responseText.textContent = "错误: " + error;
    responseStatus.textContent = "发生错误";
    responseStatus.className = "status error";
}

// 处理TTS开始
function handleTTSStart(text) {
    const audioStatus = document.getElementById("audioStatus");
    audioStatus.textContent = "正在生成语音: " + (text.length > 50 ? text.substring(0, 50) + "..." : text);
    audioStatus.className = "status streaming";
}

// 处理TTS完成
function handleTTSComplete() {
    const audioStatus = document.getElementById("audioStatus");
    const responseStatus = document.getElementById("responseStatus");
    
    audioStatus.textContent = "语音生成完成";
    audioStatus.className = "status";
    
    responseStatus.textContent = "响应完成";
    responseStatus.className = "status";
}

function sendText() {
    const text = document.getElementById("textInput").value;
    const responseStatus = document.getElementById("responseStatus");
    
    if (!text.trim()) {
        alert("请输入文本");
        return;
    }
    
    if (dc && dc.readyState === "open") {
        dc.send(text);
        console.log("发送文本:", text);
        
        // 将用户输入添加到队列
        userInputQueue.push(text);
        console.log("用户输入已添加到队列，队列长度:", userInputQueue.length);
        
        // 清空输入框
        document.getElementById("textInput").value = "";
        
        // 更新状态（但不刷新回复文本）
        responseStatus.textContent = "正在等待LLM响应...";
        responseStatus.className = "status streaming";
        
        // 注意：不再在发送按钮时刷新回复文本
        // 回复文本将在tag改变时（收到第一个text_chunk）刷新
    } else {
        console.warn("DataChannel 未打开");
        alert("请先连接服务器");
    }
}
