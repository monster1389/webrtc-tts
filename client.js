let pc = null;
let dc = null;

async function start() {
    const audio = document.getElementById("audio");

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
        audio.play().catch(e => console.warn("播放失败:", e));
    };

    dc = pc.createDataChannel("chat");
    dc.onopen = () => console.log("DataChannel opened");

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
}


function sendText() {
    const text = document.getElementById("textInput").value;
    if (dc && dc.readyState === "open") {
        dc.send(text);
        console.log("发送文本:", text);
    } else {
        console.warn("DataChannel 未打开");
    }
}
