"""
Main FastAPI application for the real-time translator.
Provides WebSocket endpoints and static file serving.
"""

import logging
import uuid
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pathlib import Path

from .services.websocket_handler import websocket_endpoint
from .services.whisper_service import get_whisper_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Real-time Translator",
    description="Real-time speech translation with Whisper ASR, MiniMax translation, and T2V synthesis",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (frontend)
frontend_path = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")
    logger.info(f"Mounted static files from {frontend_path}")
else:
    logger.warning(f"Frontend dist directory not found: {frontend_path}")


@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    logger.info("Starting Real-time Translator application...")

    # Force load Whisper model immediately to avoid first-use delay
    whisper_service = get_whisper_service()
    whisper_service.load_model()  # Force immediate model loading
    logger.info("Whisper model preloading completed during startup")

    logger.info("Application startup complete")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    logger.info("Shutting down Real-time Translator application...")


@app.get("/")
async def root():
    """Root endpoint - redirect to frontend"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/frontend")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    whisper_service = get_whisper_service()
    model_info = whisper_service.get_model_info()

    return {
        "status": "healthy",
        "whisper_model": model_info,
        "endpoints": {
            "websocket": "/ws/{client_id}",
            "health": "/health",
            "docs": "/docs"
        }
    }


@app.websocket("/ws/{client_id}")
async def websocket_handler(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time communication"""
    # Validate client_id
    if not client_id or len(client_id) < 8:
        await websocket.close(code=1003, reason="Invalid client ID")
        return

    logger.info(f"WebSocket connection attempt from client: {client_id}")

    try:
        await websocket_endpoint(websocket, client_id)
    except Exception as e:
        logger.error(f"WebSocket handler error: {str(e)}")
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass


@app.websocket("/ws")
async def websocket_auto_id(websocket: WebSocket):
    """WebSocket endpoint with auto-generated client ID"""
    client_id = str(uuid.uuid4())
    await websocket_handler(websocket, client_id)


@app.get("/frontend")
async def serve_frontend():
    """Serve frontend HTML"""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>MiniMax_Simultaneous Interpretation</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; background-color: #f8f9fa; }
            .container { max-width: 900px; margin: 0 auto; }
            .config-panel { background: #ffffff; padding: 25px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .chat-container {
                height: 500px;
                overflow-y: auto;
                background: #ffffff;
                padding: 20px;
                border-radius: 12px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .message {
                margin: 15px 0;
                clear: both;
                display: flex;
                flex-direction: column;
            }
            .original {
                align-self: flex-start;
                background: #e9ecef;
                color: #495057;
                padding: 12px 16px;
                border-radius: 18px 18px 18px 4px;
                max-width: 70%;
                margin-bottom: 5px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                position: relative;
                font-size: 15px;
                line-height: 1.4;
            }
            .original::before {
                content: "🎤 原文";
                display: block;
                font-size: 11px;
                color: #6c757d;
                margin-bottom: 4px;
                font-weight: 500;
            }
            .translated {
                align-self: flex-end;
                background: linear-gradient(135deg, #007bff, #0056b3);
                color: white;
                padding: 12px 16px;
                border-radius: 18px 18px 4px 18px;
                max-width: 70%;
                margin-top: 5px;
                box-shadow: 0 2px 8px rgba(0,123,255,0.3);
                position: relative;
                font-size: 15px;
                line-height: 1.4;
            }
            .translated::before {
                content: "🌐 译文";
                display: block;
                font-size: 11px;
                color: rgba(255,255,255,0.8);
                margin-bottom: 4px;
                font-weight: 500;
            }
            .error {
                align-self: center;
                background: linear-gradient(135deg, #dc3545, #c82333);
                color: white;
                padding: 12px 16px;
                border-radius: 18px;
                margin: 10px 20px;
                box-shadow: 0 2px 8px rgba(220,53,69,0.3);
                position: relative;
                font-size: 14px;
                line-height: 1.4;
                text-align: center;
                border: 2px solid #e74c3c;
            }
            .error::before {
                content: "⚠️ 错误";
                display: block;
                font-size: 11px;
                color: rgba(255,255,255,0.9);
                margin-bottom: 4px;
                font-weight: 600;
            }
            .controls {
                margin: 25px 0;
                text-align: center;
                background: #ffffff;
                padding: 20px;
                border-radius: 12px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            button {
                padding: 12px 24px;
                margin: 0 8px;
                font-size: 16px;
                border: none;
                border-radius: 8px;
                background: #007bff;
                color: white;
                cursor: pointer;
                transition: all 0.2s ease;
                font-weight: 500;
            }
            button:hover {
                background: #0056b3;
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(0,123,255,0.3);
            }
            button:disabled {
                background: #6c757d;
                cursor: not-allowed;
                transform: none;
                box-shadow: none;
            }
            input, select {
                padding: 12px;
                margin: 8px;
                width: 220px;
                border: 2px solid #e9ecef;
                border-radius: 8px;
                font-size: 14px;
                transition: border-color 0.2s ease;
            }
            input:focus, select:focus {
                outline: none;
                border-color: #007bff;
                box-shadow: 0 0 0 3px rgba(0,123,255,0.1);
            }
            .status {
                background: #ffffff;
                padding: 15px;
                border-radius: 8px;
                margin-top: 20px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                font-family: 'Courier New', monospace;
                font-size: 13px;
                border-left: 4px solid #28a745;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎙️ MiniMax_Simultaneous Interpretation</h1>

            <div class="config-panel">
                <h3>Configuration</h3>
                <div>
                    <input type="text" id="minimax-key" placeholder="MiniMax API Key (用于翻译和语音合成)" style="width: 450px;" />
                </div>
                <div>
                    <input type="text" id="voice-id" placeholder="Voice ID (例如: male-qn-qingse)" />
                    <label for="source-language" style="margin: 8px; font-weight: 500; color: #495057;">源语言:</label>
                    <select id="source-language" style="width: 120px; padding: 12px; margin: 8px; border: 2px solid #e9ecef; border-radius: 8px; font-size: 14px;">
                        <option value="auto" selected>自动检测</option>
                        <option value="zh">中文</option>
                        <option value="en">English</option>
                        <option value="ja">日本語</option>
                        <option value="es">Español</option>
                        <option value="fr">Français</option>
                        <option value="de">Deutsch</option>
                        <option value="ru">Русский</option>
                        <option value="ko">한국어</option>
                        <option value="it">Italiano</option>
                        <option value="pt">Português</option>
                        <option value="ar">العربية</option>
                        <option value="hi">हिन्दी</option>
                        <option value="th">ไทย</option>
                        <option value="vi">Tiếng Việt</option>
                    </select>
                    <label for="target-language" style="margin: 8px; font-weight: 500; color: #495057;">目标语言:</label>
                    <select id="target-language">
                        <option value="English">English</option>
                        <option value="中文">中文</option>
                        <option value="日本語">日本語</option>
                        <option value="Español">Español</option>
                    </select>
                </div>
                <div>
                    <select id="translation-style" style="width: 220px; padding: 12px; margin: 8px; border: 2px solid #e9ecef; border-radius: 8px; font-size: 14px;">
                        <option value="default">翻译风格：默认</option>
                        <option value="colloquial">翻译风格：口语化</option>
                        <option value="business">翻译风格：商务场景</option>
                        <option value="academic">翻译风格：学术场景</option>
                    </select>
                </div>
                <div>
                    <textarea id="hot-words" placeholder="热词/专业术语 (每行一个)" rows="3" style="width: 450px; resize: vertical; font-family: inherit; padding: 12px; margin: 8px; border: 2px solid #e9ecef; border-radius: 8px; font-size: 14px;"></textarea>
                </div>
                <button onclick="configure()">Configure</button>
            </div>

            <div class="controls">
                <button id="record-btn" onclick="toggleRecording()" disabled>Start Recording</button>
                <button onclick="clearChat()">Clear Chat</button>
                <button onclick="getStatus()">Get Status</button>
            </div>

            <div id="chat" class="chat-container"></div>

            <div id="status" class="status">
                Status: Not connected
            </div>
        </div>

        <script>
            let ws = null;
            let isRecording = false;
            let mediaRecorder = null;
            let audioChunks = [];

            // Performance monitoring
            let speechStartTime = null;
            let lastAudioSentTime = null;

            // Streaming audio manager with Web Audio API
            const streamingAudio = {
                audioContext: null,
                activeStreams: new Map(), // task_id -> stream info
                audioQueue: [], // Array of { taskId, chunks, format, isComplete }
                currentlyPlaying: null, // Current playing task ID
                isPlayingAny: false,
                nextStartTime: 0, // For seamless audio scheduling

                async initAudioContext() {
                    if (!this.audioContext) {
                        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
                        console.log(`[AUDIO] AudioContext initialized, sample rate: ${this.audioContext.sampleRate}`);
                    }

                    if (this.audioContext.state === 'suspended') {
                        await this.audioContext.resume();
                        console.log(`[AUDIO] AudioContext resumed`);
                    }
                },

                addToQueue(taskId, audioData, format, isLast = false) {
                    console.log(`[QUEUE] Adding audio chunk for task ${taskId}, isLast: ${isLast}, data size: ${audioData.length} bytes`);

                    // Decode audio data
                    let audioBytes;
                    try {
                        const binaryString = atob(audioData);
                        audioBytes = new Uint8Array(binaryString.length);
                        for (let i = 0; i < binaryString.length; i++) {
                            audioBytes[i] = binaryString.charCodeAt(i);
                        }
                        console.log(`[QUEUE] Successfully decoded ${audioBytes.length} bytes`);
                    } catch (e) {
                        console.error(`[QUEUE] Failed to decode base64 audio data:`, e);
                        return;
                    }

                    // Find existing queue item for this task or create new one
                    let queueItem = this.audioQueue.find(item => item.taskId === taskId);
                    if (!queueItem) {
                        queueItem = {
                            taskId: taskId,
                            chunks: [],
                            format: format,
                            isComplete: false
                        };
                        this.audioQueue.push(queueItem);
                        console.log(`[QUEUE] Created new queue item for task ${taskId}, queue length: ${this.audioQueue.length}`);
                    }

                    // Add chunk to this task
                    queueItem.chunks.push(audioBytes);

                    if (isLast) {
                        queueItem.isComplete = true;
                        console.log(`[QUEUE] ✅ Task ${taskId.substring(0,8)} marked as COMPLETE with ${queueItem.chunks.length} chunks`);
                    }

                    // Process queue if not currently playing
                    this.processQueue();
                },


                processQueue() {
                    console.log(`[QUEUE] processQueue called - queue length: ${this.audioQueue.length}, isPlaying: ${this.isPlayingAny}`);

                    if (this.audioQueue.length === 0) {
                        console.log(`[QUEUE] Queue is empty, nothing to process`);
                        return;
                    }

                    if (this.isPlayingAny) {
                        console.log(`[QUEUE] Already playing audio (task: ${this.currentlyPlaying}), waiting for it to finish`);
                        return;
                    }

                    // Get the first complete audio from queue (FIFO order)
                    const queueItem = this.audioQueue.find(item => item.isComplete);
                    if (!queueItem) {
                        console.log(`[QUEUE] No complete audio in queue yet. Queue contents: ${this.audioQueue.map(item => `${item.taskId.substring(0,8)}(complete: ${item.isComplete})`).join(', ')}`);
                        return;
                    }

                    // Remove from queue and start playing
                    const index = this.audioQueue.indexOf(queueItem);
                    this.audioQueue.splice(index, 1);

                    console.log(`[QUEUE] ✅ Starting sequential playback of task ${queueItem.taskId.substring(0,8)}, remaining in queue: ${this.audioQueue.length}`);
                    this.playCompleteAudio(queueItem);
                },

                playCompleteAudio(queueItem) {
                    console.log(`[QUEUE] ✅ playCompleteAudio called for task ${queueItem.taskId.substring(0,8)}`);
                    this.isPlayingAny = true;
                    this.currentlyPlaying = queueItem.taskId;

                    try {
                        // Combine all chunks into one audio file
                        const totalLength = queueItem.chunks.reduce((sum, chunk) => sum + chunk.length, 0);
                        const combinedAudio = new Uint8Array(totalLength);
                        let offset = 0;
                        for (const chunk of queueItem.chunks) {
                            combinedAudio.set(chunk, offset);
                            offset += chunk.length;
                        }

                        console.log(`[QUEUE] Combined audio for task ${queueItem.taskId.substring(0,8)}: ${totalLength} bytes`);

                        // Create audio blob and play with HTML Audio API
                        const blob = new Blob([combinedAudio], { type: `audio/${queueItem.format}` });
                        const audioUrl = URL.createObjectURL(blob);
                        const audio = new Audio(audioUrl);
                        audio.volume = 1.0;

                        audio.addEventListener('canplay', () => {
                            console.log(`[QUEUE] Audio ready to play for task ${queueItem.taskId.substring(0,8)}`);
                            audio.play().then(() => {
                                console.log(`[QUEUE] ✅ Audio playback STARTED for task ${queueItem.taskId.substring(0,8)}`);
                                updateStatus(`正在播放翻译 ${queueItem.taskId.substring(0,8)}...`);
                            }).catch(e => {
                                console.error(`[QUEUE] ❌ Failed to play audio for task ${queueItem.taskId.substring(0,8)}:`, e);
                                this.onAudioEnded(queueItem.taskId, audioUrl);
                            });
                        });

                        audio.addEventListener('ended', () => {
                            console.log(`[QUEUE] ✅ Audio playback ENDED for task ${queueItem.taskId.substring(0,8)}`);
                            if (speechStartTime) {
                                const audioEndTime = performance.now();
                                const speechToAudioMs = audioEndTime - speechStartTime;
                                console.log(`⏱️ Frontend Performance: Speech to Audio Complete = ${speechToAudioMs.toFixed(0)}ms`);
                                speechStartTime = null; // Reset for next speech
                            }
                            this.onAudioEnded(queueItem.taskId, audioUrl);
                        });

                        audio.addEventListener('error', (e) => {
                            console.error(`[QUEUE] ❌ Audio ERROR for task ${queueItem.taskId.substring(0,8)}:`, e);
                            this.onAudioEnded(queueItem.taskId, audioUrl);
                        });

                        audio.load();

                    } catch (e) {
                        console.error(`[QUEUE] Failed to create audio for task ${queueItem.taskId.substring(0,8)}:`, e);
                        this.onAudioEnded(queueItem.taskId, null);
                    }
                },


                onAudioEnded(taskId, audioUrl) {
                    console.log(`[QUEUE] onAudioEnded called for task ${taskId}`);

                    if (audioUrl) {
                        URL.revokeObjectURL(audioUrl);
                    }

                    console.log(`[QUEUE] Setting isPlayingAny = false, was playing: ${this.currentlyPlaying}`);
                    this.isPlayingAny = false;
                    this.currentlyPlaying = null;

                    // Process next item in queue
                    console.log(`[QUEUE] Scheduling next queue processing in 100ms. Current queue length: ${this.audioQueue.length}`);
                    setTimeout(() => {
                        console.log(`[QUEUE] Timeout callback executing, processing queue`);
                        this.processQueue();
                    }, 100); // Small delay to avoid race conditions
                },

                addChunk(taskId, audioData, isLast = false) {
                    // Maintain backward compatibility while using new queue system
                    this.addToQueue(taskId, audioData, 'mp3', isLast);
                },

                getQueueStatus() {
                    return {
                        queueLength: this.audioQueue.length,
                        isPlaying: this.isPlayingAny,
                        currentTask: this.currentlyPlaying,
                        pendingTasks: this.audioQueue.map(item => ({
                            taskId: item.taskId,
                            chunks: item.chunks.length,
                            isComplete: item.isComplete
                        }))
                    };
                }
            };

            function connect() {
                const clientId = 'web-' + Math.random().toString(36).substr(2, 9);
                // Use current host for WebSocket connection to support remote access
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const host = window.location.host;
                ws = new WebSocket(`${protocol}//${host}/ws/${clientId}`);

                ws.onopen = () => {
                    updateStatus('Connected to server');
                    console.log('WebSocket connected successfully');
                };

                ws.onmessage = (event) => {
                    console.log('Received message:', event.data);
                    try {
                        const message = JSON.parse(event.data);
                        handleMessage(message);
                    } catch (e) {
                        console.error('Failed to parse message:', e);
                        updateStatus('Message parsing error: ' + e.message);
                    }
                };

                ws.onclose = (event) => {
                    console.log('WebSocket closed:', event.code, event.reason);
                    updateStatus(`Disconnected from server (${event.code})`);
                    document.getElementById('record-btn').disabled = true;

                    // Auto-reconnect after 3 seconds
                    setTimeout(() => {
                        console.log('Attempting to reconnect...');
                        connect();
                    }, 3000);
                };

                ws.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    updateStatus('Connection error - check console for details');
                };
            }

            function handleMessage(message) {
                const type = message.type;
                const data = message.data;

                switch(type) {
                    case 'configured':
                        updateStatus('Configured successfully');
                        document.getElementById('record-btn').disabled = false;
                        break;
                    case 'transcription':
                        console.log('📥 Received transcription message:', data.text);
                        if (speechStartTime) {
                            const transcriptionTime = performance.now();
                            const speechToTranscriptionMs = transcriptionTime - speechStartTime;
                            console.log(`⏱️ Frontend Performance: Speech to Transcription = ${speechToTranscriptionMs.toFixed(0)}ms`);
                        }
                        addMessage(data.text, 'original');
                        console.log('✅ Transcription message added to chat');
                        break;
                    case 'translation':
                        if (speechStartTime) {
                            const translationTime = performance.now();
                            const speechToTranslationMs = translationTime - speechStartTime;
                            console.log(`⏱️ Frontend Performance: Speech to Translation = ${speechToTranslationMs.toFixed(0)}ms`);
                        }
                        addMessage(data.translated_text, 'translated');
                        break;
                    case 'audio_chunk':
                        console.log('=== RECEIVED AUDIO CHUNK ===');
                        console.log('Full data object:', data);
                        console.log('Has data.audio:', !!data.audio);
                        console.log('Has data.data.audio:', !!(data.data && data.data.audio));

                        // Check both possible locations for audio data
                        let audioData = data.audio || (data.data && data.data.audio);
                        let taskId = data.task_id || (data.data && data.data.task_id);
                        let format = data.format || (data.data && data.data.format) || 'mp3';
                        let isFinal = data.is_final || (data.data && data.data.is_final);

                        console.log('Extracted audio data length:', audioData ? audioData.length : 'NO AUDIO');
                        console.log('Extracted task ID:', taskId);
                        console.log('Extracted format:', format);
                        console.log('Extracted is final:', isFinal);

                        if (audioData) {
                            playAudioChunk(taskId, audioData, format, isFinal);
                        } else {
                            console.error('No audio data found in chunk:', data);
                        }
                        break;
                    case 'audio':
                        console.log('Received complete audio message:', data);
                        if (data.audio) {
                            console.log('Adding complete audio to queue, task:', data.task_id, 'format:', data.format || 'mp3');
                            // Add complete audio to queue system instead of playing directly
                            streamingAudio.addToQueue(data.task_id, data.audio, data.format || 'mp3', true);
                        } else if (data.data && data.data.audio) {
                            console.log('Adding complete audio from data.data.audio to queue');
                            // Add complete audio to queue system instead of playing directly
                            streamingAudio.addToQueue(data.task_id || 'unknown', data.data.audio, 'mp3', true);
                        } else {
                            console.error('No audio data received in message. Data keys:', Object.keys(data));
                            console.error('Full data object:', data);
                        }
                        break;
                    case 'translation_error':
                        console.log('📛 Translation error received:', data.error);
                        addMessage(`❌ 翻译失败: ${data.error}`, 'error');
                        updateStatus('Translation failed: ' + data.error);
                        break;
                    case 'transcription_error':
                        console.log('📛 Transcription error received:', data.error);
                        addMessage(`❌ 语音识别失败: ${data.error}`, 'error');
                        updateStatus('Transcription failed: ' + data.error);
                        break;
                    case 'error':
                        updateStatus('Error: ' + data.error);
                        break;
                    case 'status':
                        updateStatus('Status: ' + JSON.stringify(data, null, 2));
                        break;
                }
            }

            function configure() {
                console.log('Configure button clicked');

                // Check WebSocket connection
                if (!ws || ws.readyState !== WebSocket.OPEN) {
                    updateStatus('Error: Not connected to server. Reconnecting...');
                    connect();
                    return;
                }

                const hotWordsText = document.getElementById('hot-words').value.trim();
                const hotWords = hotWordsText ? hotWordsText.split('\\n').map(word => word.trim()).filter(word => word.length > 0) : [];

                const minimaxApiKey = document.getElementById('minimax-key').value.trim();

                const config = {
                    minimax_api_key: minimaxApiKey,
                    t2v_api_key: minimaxApiKey,  // 使用同一个API Key
                    voice_id: document.getElementById('voice-id').value.trim(),
                    source_language: document.getElementById('source-language').value,
                    target_language: document.getElementById('target-language').value,
                    translation_style: document.getElementById('translation-style').value,
                    hot_words: hotWords
                };

                console.log('Configuration:', config);

                if (!config.minimax_api_key) {
                    alert('请输入MiniMax API Key');
                    return;
                }

                updateStatus('Configuring...');

                try {
                    const message = {
                        type: 'configure',
                        data: config
                    };
                    console.log('Sending configuration message:', message);
                    ws.send(JSON.stringify(message));

                } catch (error) {
                    console.error('Failed to send configuration:', error);
                    updateStatus('Failed to send configuration: ' + error.message);
                }
            }

            async function toggleRecording() {
                if (!isRecording) {
                    await startRecording();
                } else {
                    stopRecording();
                }
            }

            async function startRecording() {
                try {
                    console.log('Requesting microphone access...');
                    const stream = await navigator.mediaDevices.getUserMedia({
                        audio: {
                            sampleRate: 16000,
                            channelCount: 1,
                            echoCancellation: true,
                            noiseSuppression: true
                        }
                    });

                    console.log('Microphone access granted');

                    // Use AudioContext for proper audio processing
                    const audioContext = new (window.AudioContext || window.webkitAudioContext)({
                        sampleRate: 16000
                    });

                    const source = audioContext.createMediaStreamSource(stream);
                    const processor = audioContext.createScriptProcessor(1024, 1, 1);

                    processor.onaudioprocess = (event) => {
                        const inputBuffer = event.inputBuffer;
                        const inputData = inputBuffer.getChannelData(0);

                        // Calculate audio level for visual feedback
                        let sum = 0;
                        for (let i = 0; i < inputData.length; i++) {
                            sum += inputData[i] * inputData[i];
                        }
                        const rms = Math.sqrt(sum / inputData.length);
                        const audioLevel = Math.min(1, rms * 10); // Normalize and amplify

                        // Update status with audio level
                        if (audioLevel > 0.01) {
                            updateStatus(`Recording... Audio level: ${(audioLevel * 100).toFixed(0)}%`);
                        }

                        // 设置麦克风阈值，低于阈值发送静音数据
                        const microphoneThreshold = 0.15; // 15% 阈值，进一步过滤杂音
                        let audioDataToSend;

                        if (audioLevel >= microphoneThreshold) {
                            // 音量超过阈值，发送真实音频数据
                            // Record speech timing for performance monitoring
                            if (!speechStartTime) {
                                speechStartTime = performance.now();
                                console.log('🎤 ⏱️ Speech detection started');
                            }

                            // Convert Float32Array to 16-bit PCM
                            const pcmData = new Int16Array(inputData.length);
                            for (let i = 0; i < inputData.length; i++) {
                                pcmData[i] = Math.max(-32768, Math.min(32767, inputData[i] * 32768));
                            }
                            audioDataToSend = pcmData;

                            console.log(`Sent REAL audio chunk: ${pcmData.length * 2} bytes, level: ${(audioLevel * 100).toFixed(1)}%`);
                        } else {
                            // 音量低于阈值，发送静音数据
                            const silentData = new Int16Array(inputData.length);
                            // silentData 默认都是0，即静音
                            audioDataToSend = silentData;

                            console.log(`Sent SILENT audio chunk: ${silentData.length * 2} bytes, level: ${(audioLevel * 100).toFixed(1)}% (below threshold)`);
                        }

                        lastAudioSentTime = performance.now();

                        // Convert to base64 and send
                        const base64 = btoa(String.fromCharCode.apply(null, new Uint8Array(audioDataToSend.buffer)));

                        if (ws && ws.readyState === WebSocket.OPEN) {
                            ws.send(JSON.stringify({
                                type: 'audio_data',
                                data: { audio: base64 }
                            }));
                        }
                    };

                    source.connect(processor);
                    processor.connect(audioContext.destination);

                    // Store references for cleanup
                    window.audioContext = audioContext;
                    window.processor = processor;
                    window.source = source;
                    window.stream = stream;

                    ws.send(JSON.stringify({
                        type: 'start_recording'
                    }));

                    isRecording = true;
                    document.getElementById('record-btn').textContent = 'Stop Recording';
                    updateStatus('Recording... Speak now!');
                    console.log('Recording started successfully');

                } catch (error) {
                    console.error('Microphone access error:', error);
                    alert('Could not access microphone: ' + error.message);
                    updateStatus('Microphone access failed');
                }
            }

            function stopRecording() {
                console.log('Stopping recording...');

                // Clean up AudioContext resources
                if (window.processor) {
                    window.processor.disconnect();
                    window.processor = null;
                }

                if (window.source) {
                    window.source.disconnect();
                    window.source = null;
                }

                if (window.audioContext) {
                    window.audioContext.close();
                    window.audioContext = null;
                }

                if (window.stream) {
                    window.stream.getTracks().forEach(track => track.stop());
                    window.stream = null;
                }

                // Legacy MediaRecorder cleanup
                if (mediaRecorder) {
                    mediaRecorder.stop();
                    if (mediaRecorder.stream) {
                        mediaRecorder.stream.getTracks().forEach(track => track.stop());
                    }
                    mediaRecorder = null;
                }

                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({
                        type: 'stop_recording'
                    }));
                }

                isRecording = false;
                document.getElementById('record-btn').textContent = 'Start Recording';
                updateStatus('Recording stopped');
                console.log('Recording stopped successfully');
            }

            function addMessage(text, type) {
                const chat = document.getElementById('chat');
                const message = document.createElement('div');
                message.className = `message ${type}`;
                message.textContent = text;
                chat.appendChild(message);
                chat.scrollTop = chat.scrollHeight;
            }

            function clearChat() {
                console.log('🧹 Clearing chat and stopping all ongoing tasks...');

                // Clear chat display
                document.getElementById('chat').innerHTML = '';

                // Stop and clear all audio playback
                if (streamingAudio) {
                    // Stop currently playing audio
                    streamingAudio.isPlayingAny = false;
                    streamingAudio.currentlyPlaying = null;

                    // Clear audio queue
                    streamingAudio.audioQueue = [];

                    console.log('🔇 Audio queue cleared and playback stopped');
                }

                // Stop recording if active
                if (isRecording) {
                    stopRecording();
                    console.log('⏹️ Recording stopped');
                }

                // Send clear command to backend
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({
                        type: 'clear_all_tasks'
                    }));
                    console.log('📡 Clear command sent to backend');
                }

                updateStatus('Chat cleared - all tasks stopped');
                console.log('✅ Clear chat completed');
            }

            function getStatus() {
                ws.send(JSON.stringify({
                    type: 'get_status'
                }));
            }

            function playAudio(base64Audio, audioFormat = 'mp3') {
                console.log('=== AUDIO DEBUG START ===');
                console.log('playAudio called with base64 length:', base64Audio.length, 'format:', audioFormat);
                console.log('Audio data preview:', base64Audio.substring(0, 100) + '...');

                // Check if base64 looks like valid MP3 data
                const binaryString = atob(base64Audio);
                const firstBytes = Array.from(binaryString.substring(0, 10))
                    .map(c => c.charCodeAt(0).toString(16).padStart(2, '0'))
                    .join(' ');
                console.log('First 10 bytes (hex):', firstBytes);

                // Map format names to MIME types
                const formatMimeMap = {
                    'mp3': 'audio/mpeg',
                    'mpeg': 'audio/mpeg',
                    'wav': 'audio/wav',
                    'pcm': 'audio/wav',
                    'flac': 'audio/flac',
                    'ogg': 'audio/ogg'
                };

                // Try the specified format first, then fallbacks
                const primaryMime = formatMimeMap[audioFormat.toLowerCase()] || 'audio/mpeg';
                const formats = [primaryMime, 'audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/ogg'];
                let formatIndex = 0;

                function tryNextFormat() {
                    if (formatIndex >= formats.length) {
                        console.error('All audio formats failed');
                        tryWebAudioAPI();
                        return;
                    }

                    const format = formats[formatIndex];
                    console.log(`Trying format: ${format}`);

                    const audio = new Audio(`data:${format};base64,${base64Audio}`);

                    audio.addEventListener('loadstart', () => console.log(`${format}: loadstart`));
                    audio.addEventListener('canplay', () => {
                        console.log(`${format}: canplay - attempting to play`);
                        audio.play().then(() => {
                            console.log(`${format}: Successfully playing!`);
                            updateStatus('音频播放成功');
                        }).catch(e => {
                            console.error(`${format}: Play failed:`, e);
                            if (e.name === 'NotAllowedError') {
                                console.log('Autoplay blocked');
                                updateStatus('自动播放被阻止');
                            } else {
                                formatIndex++;
                                setTimeout(tryNextFormat, 100);
                            }
                        });
                    });
                    audio.addEventListener('loadeddata', () => console.log(`${format}: loadeddata`));
                    audio.addEventListener('loadedmetadata', () => console.log(`${format}: loadedmetadata, duration:`, audio.duration));
                    audio.addEventListener('error', (e) => {
                        console.error(`${format}: error event:`, e);
                        formatIndex++;
                        setTimeout(tryNextFormat, 100);
                    });

                    // Set volume to maximum
                    audio.volume = 1.0;

                    // Try to load
                    audio.load();
                }

                function tryWebAudioAPI() {
                    console.log('Trying Web Audio API...');
                    try {
                        const audioContext = new (window.AudioContext || window.webkitAudioContext)();

                        // Decode base64 to array buffer
                        const binaryString = atob(base64Audio);
                        const arrayBuffer = new ArrayBuffer(binaryString.length);
                        const uint8Array = new Uint8Array(arrayBuffer);
                        for (let i = 0; i < binaryString.length; i++) {
                            uint8Array[i] = binaryString.charCodeAt(i);
                        }

                        audioContext.decodeAudioData(arrayBuffer).then(audioBuffer => {
                            console.log('Web Audio API: Audio decoded successfully');
                            console.log('Duration:', audioBuffer.duration, 'seconds');
                            console.log('Sample rate:', audioBuffer.sampleRate);
                            console.log('Channels:', audioBuffer.numberOfChannels);

                            const source = audioContext.createBufferSource();
                            source.buffer = audioBuffer;
                            source.connect(audioContext.destination);
                            source.start(0);
                            console.log('Web Audio API: Playing audio');
                            updateStatus('使用Web Audio API播放音频');
                        }).catch(e => {
                            console.error('Web Audio API decode failed:', e);
                            tryBlobDownload();
                        });
                    } catch (e) {
                        console.error('Web Audio API failed:', e);
                        tryBlobDownload();
                    }
                }

                function tryBlobDownload() {
                    console.log('Creating downloadable audio file for testing...');
                    try {
                        const binaryString = atob(base64Audio);
                        const bytes = new Uint8Array(binaryString.length);
                        for (let i = 0; i < binaryString.length; i++) {
                            bytes[i] = binaryString.charCodeAt(i);
                        }
                        const blob = new Blob([bytes], { type: 'audio/mp3' });
                        const url = URL.createObjectURL(blob);

                        // Create a temporary link for download
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = 'test_audio.mp3';
                        a.textContent = '下载测试音频文件';
                        a.style.display = 'block';
                        a.style.margin = '10px';
                        a.style.padding = '10px';
                        a.style.background = '#007bff';
                        a.style.color = 'white';
                        a.style.textDecoration = 'none';
                        a.style.borderRadius = '4px';

                        // Add to page
                        const container = document.getElementById('chat');
                        container.appendChild(a);

                        console.log('Download link created. File size:', blob.size, 'bytes');
                        updateStatus('音频文件已创建，请下载测试');

                        // Clean up after 30 seconds
                        setTimeout(() => {
                            URL.revokeObjectURL(url);
                            if (a.parentNode) {
                                a.parentNode.removeChild(a);
                            }
                        }, 30000);

                    } catch (e) {
                        console.error('Blob creation failed:', e);
                    }
                }

                // Start with user interaction check
                console.log('Checking user interaction for autoplay...');

                // Try to enable audio context (required for some browsers)
                if (window.AudioContext || window.webkitAudioContext) {
                    const tempContext = new (window.AudioContext || window.webkitAudioContext)();
                    if (tempContext.state === 'suspended') {
                        console.log('Audio context suspended, trying to resume...');
                        tempContext.resume().then(() => {
                            console.log('Audio context resumed');
                            tempContext.close();
                            tryNextFormat();
                        }).catch(e => {
                            console.log('Audio context resume failed:', e);
                            tempContext.close();
                            tryNextFormat();
                        });
                    } else {
                        tempContext.close();
                        tryNextFormat();
                    }
                } else {
                    tryNextFormat();
                }

                console.log('=== AUDIO DEBUG END ===');
            }

            function playAudioChunk(taskId, audioData, format, isLast) {
                console.log(`=== STREAMING AUDIO CHUNK ===`);
                console.log(`Task ID: ${taskId}, Format: ${format}, Is Last: ${isLast}`);
                console.log(`Chunk size: ${audioData.length} bytes`);

                // Add to queue system for sequential playback
                streamingAudio.addToQueue(taskId, audioData, format, isLast);

                // Log queue status for debugging
                const status = streamingAudio.getQueueStatus();
                console.log(`Queue status:`, status);
            }


            function updateStatus(message) {
                document.getElementById('status').textContent = message;
            }


            // Connect on page load
            connect();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


def create_app():
    """Create and configure the FastAPI application"""
    return app


if __name__ == "__main__":
    # Run the application
    uvicorn.run(
        "backend.app:app",
        host="0.0.0.0",
        port=8000,
        ssl_keyfile="certs/key.pem",
        ssl_certfile="certs/cert.pem",
        reload=True
    )