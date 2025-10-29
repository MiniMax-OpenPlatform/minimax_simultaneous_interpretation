# MiniMax 同声传译系统

基于MiniMax API的实时语音翻译系统，支持多语言同声传译、语音识别、文本翻译和语音合成。

![项目状态](https://img.shields.io/badge/状态-稳定-green)
![Python版本](https://img.shields.io/badge/Python-3.8+-blue)
![许可证](https://img.shields.io/badge/许可证-MIT-orange)

## 🌟 功能特性

### 核心功能
- **实时语音识别**：基于Whisper模型，支持多语言语音转文字
- **智能翻译**：集成MiniMax API，提供高质量的文本翻译服务
- **语音合成**：支持指定音色ID的文本转语音功能
- **热词保护**：确保专业术语和品牌名称的准确翻译
- **多种翻译风格**：支持默认、口语化、商务、学术等不同场景

### 技术特性
- **WebSocket实时通信**：低延迟的双向通信
- **流式音频处理**：边录边译，提升用户体验
- **智能语音检测**：基于VAD技术的语音活动检测
- **SSL安全连接**：支持HTTPS/WSS加密传输
- **响应式前端**：现代化的Web界面设计

## 🏗️ 系统架构

### 整体架构
```
┌─────────────────┐    WebSocket     ┌─────────────────┐
│                 │◄────────────────►│                 │
│   前端界面      │                  │   FastAPI后端   │
│   (Web UI)      │                  │                 │
└─────────────────┘                  └─────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      后端服务层                            │
├─────────────────┬─────────────────┬─────────────────────────┤
│   语音识别      │   翻译队列      │      API客户端          │
│   (Whisper)     │   (Queue)       │   (MiniMax/T2V)         │
└─────────────────┴─────────────────┴─────────────────────────┘
```

### 核心组件

#### 1. 前端层 (Frontend)
- **技术栈**：HTML5 + JavaScript + WebSocket API
- **功能**：音频录制、实时显示、配置管理
- **特点**：响应式设计，支持多种浏览器

#### 2. WebSocket处理层
- **组件**：`websocket_handler.py`
- **功能**：管理WebSocket连接，处理实时消息
- **特点**：支持多客户端并发连接

#### 3. 语音处理层
- **语音识别**：`whisper_service.py` - 基于Whisper
- **音频处理**：`audio_processor.py` - VAD检测和音频预处理
- **支持格式**：16kHz PCM音频

#### 4. 翻译服务层
- **翻译队列**：`translation_queue.py` - 智能任务调度
- **MiniMax客户端**：`minimax_client.py` - 文本翻译
- **T2V客户端**：`t2v_client.py` - 语音合成

#### 5. 数据流程
```
音频输入 → 语音识别 → 文本翻译 → 语音合成 → 音频输出
   ↓           ↓           ↓           ↓           ↓
麦克风录制  → Whisper   → MiniMax   →  T2V API  → 扬声器播放
```

## 🚀 快速开始

### 环境要求
- **Python**: 3.8 或更高版本
- **操作系统**: Windows / macOS / Linux
- **硬件**: 支持CUDA的GPU（可选，用于加速Whisper推理）
- **网络**: 稳定的互联网连接（访问MiniMax API）

### 安装步骤

#### 1. 克隆项目
```bash
git clone https://github.com/your-username/minimax-simultaneous-interpretation.git
cd minimax-simultaneous-interpretation
```

#### 2. 创建虚拟环境
```bash
# 使用venv
python -m venv .venv

# Windows激活
.venv\Scripts\activate

# macOS/Linux激活
source .venv/bin/activate
```

#### 3. 安装依赖
```bash
pip install -r requirements.txt
```

#### 4. 配置服务器设置（可选）
```bash
# 复制配置模板
cp .env.example .env

# 编辑配置文件，自定义端口等设置
nano .env
```

**可配置的服务器选项**：
```bash
# 服务器地址（0.0.0.0允许远程访问，127.0.0.1仅本地访问）
HOST=0.0.0.0
# 服务器端口（可自定义，避免端口冲突）
PORT=8867
# SSL证书路径
SSL_KEYFILE=certs/key.pem
SSL_CERTFILE=certs/cert.pem
```

#### 5. 生成SSL证书
```bash
# 创建证书目录
mkdir -p certs

# 本地开发证书（仅localhost访问）
openssl req -x509 -newkey rsa:4096 -keyout certs/key.pem -out certs/cert.pem -days 365 -nodes -subj "/C=CN/ST=Beijing/L=Beijing/O=MiniMaxTranslator/CN=localhost" -addext "subjectAltName=IP:127.0.0.1,DNS:localhost"

# 远程访问证书（替换YOUR_IP为你的实际IP地址）
# openssl req -x509 -newkey rsa:4096 -keyout certs/key.pem -out certs/cert.pem -days 365 -nodes -subj "/C=CN/ST=Beijing/L=Beijing/O=MiniMaxTranslator/CN=YOUR_IP" -addext "subjectAltName=IP:YOUR_IP,IP:127.0.0.1,DNS:localhost"
```

#### 6. 启动服务
```bash
# 本地启动
python run.py

# 远程访问启动
python run_remote.py
```

### 访问系统

#### 本地访问
```bash
# 使用run.py启动（默认8867端口）
python run.py
```
浏览器访问：https://localhost:8867/frontend

#### 远程访问
```bash
# 使用环境变量配置
export HOST=0.0.0.0
export PORT=8867
python run_remote.py
```

浏览器访问：
- **网络访问**: https://your-actual-ip:8867/frontend
- **API文档**: https://your-actual-ip:8867/docs
- **健康检查**: https://your-actual-ip:8867/health

> ⚠️ **注意**:
> 1. 首次访问时浏览器会提示SSL证书不安全，点击"高级"→"继续访问"即可
> 2. 远程访问需要生成包含实际IP的SSL证书
> 3. `run_remote.py`会自动检测并显示您的IP地址

## 🎮 使用指南

### 基础使用流程

#### 1. 系统配置
1. 打开Web界面
2. 在配置面板中输入MiniMax API密钥
3. 选择或输入Voice ID（如：male-qn-qingse）
4. 选择源语言（自动检测或手动指定）
5. 选择目标翻译语言
6. 设置翻译风格（可选）
7. 添加热词/专业术语（可选）
8. 点击"Configure"按钮

#### 2. 开始翻译
1. 点击"Start Recording"开始录音
2. 对着麦克风清晰说话
3. 系统实时显示识别结果和翻译
4. 自动播放翻译后的语音
5. 点击"Stop Recording"结束录音

#### 3. 高级功能
- **清空对话**: 点击"Clear Chat"清除所有翻译记录
- **查看状态**: 点击"Get Status"查看系统运行状态
- **调整配置**: 随时修改语言、风格等设置

### 支持的语言

#### 输入语言（自动识别）
- 中文（普通话）
- 英语
- 日语
- 西班牙语
- 法语
- 德语
- 俄语
- 韩语
- ...（Whisper支持的99种语言）

#### 输出语言
- **English** - 英语
- **中文** - 简体中文
- **日本語** - 日语
- **Español** - 西班牙语

### 翻译风格说明

| 风格 | 适用场景 | 特点 |
|------|----------|------|
| **默认** | 通用场景 | 标准翻译，平衡准确性和流畅性 |
| **口语化** | 日常对话 | 使用口语表达，更自然亲切 |
| **商务场景** | 商务会议 | 正式商务用语，专业术语准确 |
| **学术场景** | 学术交流 | 学术化表达，术语精确 |

### 热词功能
热词功能确保专业术语、品牌名称等保持原有格式：

**示例**：
- 输入热词：`MiniMax`
- 原文：你觉得minimax公司怎样
- 翻译：How do you think about **MiniMax** company

**使用技巧**：
- 每行输入一个热词
- 注意保持准确的大小写
- 适用于品牌名、专业术语、人名等

## ⚙️ 配置选项

### 系统配置

#### API配置（必须）
通过Web界面进行配置，无需修改文件：
- **MiniMax API密钥**：在Web界面配置面板输入
- **Voice ID**：在Web界面输入音色ID（如：male-qn-qingse）
- **源语言**：选择自动检测或指定语言
- **目标语言**：选择翻译目标语言

#### 服务器配置（可选）
如需自定义端口或其他服务器设置：
1. 复制配置文件：`cp .env.example .env`
2. 编辑`.env`文件，修改以下选项：
```bash
# 服务器地址（0.0.0.0允许远程访问，127.0.0.1仅本地访问）
HOST=0.0.0.0
# 服务器端口（可自定义，避免端口冲突）
PORT=8867
# SSL证书路径
SSL_KEYFILE=certs/key.pem
SSL_CERTFILE=certs/cert.pem
```

### 音色选择
系统支持多种预设音色，在Web界面的Voice ID字段输入：

| 音色ID | 描述 | 语言 |
|--------|------|------|
| `male-qn-qingse` | 男声-青涩 | 中文 |
| `female-shaonv` | 女声-少女 | 中文 |
| `male-yingqi` | 男声-英气 | 中文 |
| `female-chengshu` | 女声-成熟 | 中文 |

## 🛠️ 开发指南

### 项目结构
```
minimax-simultaneous-interpretation/
├── backend/                    # 后端核心代码
│   ├── api_clients/           # API客户端模块
│   │   ├── minimax_client.py  # MiniMax翻译客户端
│   │   └── t2v_client.py      # T2V语音合成客户端
│   ├── services/              # 核心服务模块
│   │   ├── audio_processor.py # 音频处理服务
│   │   ├── translation_queue.py # 翻译队列管理
│   │   ├── websocket_handler.py # WebSocket处理
│   │   └── whisper_service.py # Whisper语音识别
│   └── app.py                 # FastAPI应用入口
├── frontend/                  # 前端静态文件
├── certs/                     # SSL证书目录
├── docs/                      # 项目文档
├── scripts/                   # 实用脚本
├── .env.example              # 服务器配置模板（可选）
├── requirements.txt          # Python依赖
├── run.py                    # 本地启动脚本
└── run_remote.py             # 远程启动脚本
```

### API接口文档

#### WebSocket消息格式

**客户端 → 服务器**：
```javascript
// 配置系统
{
    "type": "configure",
    "data": {
        "minimax_api_key": "your-key",
        "voice_id": "male-qn-qingse",
        "target_language": "English",
        "translation_style": "default",
        "hot_words": ["MiniMax", "AI"]
    }
}

// 开始录音
{
    "type": "start_recording"
}

// 音频数据
{
    "type": "audio_data",
    "data": {
        "audio": "base64-encoded-audio"
    }
}

// 停止录音
{
    "type": "stop_recording"
}
```

**服务器 → 客户端**：
```javascript
// 配置确认
{
    "type": "configured",
    "data": {}
}

// 转录结果
{
    "type": "transcription",
    "data": {
        "text": "recognized text",
        "language": "zh",
        "confidence": 0.95
    }
}

// 翻译结果
{
    "type": "translation",
    "data": {
        "task_id": "uuid",
        "original_text": "原文",
        "translated_text": "Translated text",
        "target_language": "English"
    }
}

// 音频数据
{
    "type": "audio_chunk",
    "data": {
        "task_id": "uuid",
        "audio": "base64-audio-data",
        "format": "mp3",
        "is_final": false
    }
}
```

### 扩展开发

#### 添加新的翻译服务
1. 在`backend/api_clients/`创建新的客户端
2. 实现`translate_text`异步方法
3. 在翻译队列中集成新客户端

#### 添加新的语音合成服务
1. 在`backend/api_clients/`创建TTS客户端
2. 实现`text_to_speech`方法
3. 支持流式音频输出

#### 自定义音频处理
1. 修改`audio_processor.py`中的预处理逻辑
2. 调整VAD参数以适应不同环境
3. 添加音频降噪等功能

### 性能优化

#### GPU加速
```bash
# 安装CUDA版本的PyTorch
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118

# 配置使用GPU
export WHISPER_DEVICE=cuda
```

#### 模型选择
| 模型 | 大小 | 内存占用 | 速度 | 准确性 |
|------|------|----------|------|--------|
| tiny | 39MB | ~1GB | 最快 | 较低 |
| base | 74MB | ~1GB | 快 | 一般 |
| small | 244MB | ~2GB | 中等 | 好 |
| medium | 769MB | ~5GB | 慢 | 很好 |
| large | 1550MB | ~10GB | 最慢 | 最佳 |

#### 并发调优
```bash
# 调整并发翻译任务数
MAX_CONCURRENT_TRANSLATIONS=5

# 调整超时时间
DEFAULT_TIMEOUT_SECONDS=10.0
```

## 🔧 部署指南

### Docker部署

#### 1. 构建镜像
```bash
# 创建Dockerfile
cat > Dockerfile << EOF
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8867

CMD ["python", "run.py"]
EOF

# 构建镜像
docker build -t minimax-translator .
```

#### 2. 运行容器
```bash
docker run -d \
  --name translator \
  -p 8867:8867 \
  -v $(pwd)/certs:/app/certs \
  minimax-translator
```

### 生产环境部署

#### 使用Nginx反向代理
```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/your/cert.pem;
    ssl_certificate_key /path/to/your/key.pem;

    location / {
        proxy_pass https://localhost:8867;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /ws {
        proxy_pass https://localhost:8867;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

#### 使用systemd管理服务
```bash
# 创建服务文件
sudo cat > /etc/systemd/system/minimax-translator.service << EOF
[Unit]
Description=MiniMax Translator Service
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/minimax-simultaneous-interpretation
Environment=PATH=/path/to/.venv/bin
ExecStart=/path/to/.venv/bin/python run.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 启动服务
sudo systemctl daemon-reload
sudo systemctl enable minimax-translator
sudo systemctl start minimax-translator
```

## 🐛 故障排除

### 常见问题

#### 1. SSL证书错误
**问题**: 浏览器提示证书不安全
**解决**:
```bash
# 本地访问证书
openssl req -x509 -newkey rsa:4096 -keyout certs/key.pem -out certs/cert.pem -days 365 -nodes -subj "/C=CN/ST=Beijing/L=Beijing/O=MiniMaxTranslator/CN=localhost" -addext "subjectAltName=IP:127.0.0.1,DNS:localhost"

# 远程访问证书（获取本机IP）
export LOCAL_IP=$(ip route get 1 | awk '{print $7; exit}')
openssl req -x509 -newkey rsa:4096 -keyout certs/key.pem -out certs/cert.pem -days 365 -nodes -subj "/C=CN/ST=Beijing/L=Beijing/O=MiniMaxTranslator/CN=$LOCAL_IP" -addext "subjectAltName=IP:$LOCAL_IP,IP:127.0.0.1,DNS:localhost"

# 或者在浏览器中点击"高级"→"继续访问"
```

#### 2. API密钥错误
**问题**: 翻译失败，提示API密钥无效
**解决**:
- 确认在Web界面输入的API密钥正确
- 确认API密钥有效且有足够余额
- 检查网络连接是否正常

#### 3. 音频权限问题
**问题**: 无法录音，提示权限被拒绝
**解决**:
- 在浏览器中允许麦克风权限
- 使用HTTPS访问（HTTP无法使用麦克风）
- 检查操作系统的麦克风权限设置

#### 4. Whisper模型下载失败
**问题**: 首次运行时模型下载失败
**解决**:
```bash
# 手动下载模型
python -c "import whisper; whisper.load_model('large')"

# 或者使用较小的模型
export WHISPER_MODEL=base
```

#### 5. CUDA内存不足
**问题**: GPU内存不足导致Whisper崩溃
**解决**:
```bash
# 使用较小的模型
export WHISPER_MODEL=base

# 或切换到CPU模式
export WHISPER_DEVICE=cpu
```

### 日志调试

#### 查看详细日志
```bash
# 设置调试级别
export LOG_LEVEL=DEBUG

# 启动服务并查看日志
python run.py 2>&1 | tee debug.log
```

#### 常用日志位置
- **应用日志**: 控制台输出
- **WebSocket连接**: 查看浏览器开发者工具
- **音频处理**: 检查VAD调试信息

### 性能监控

#### 系统资源监控
```bash
# 监控CPU和内存使用
htop

# 监控GPU使用（如果使用CUDA）
nvidia-smi -l 1

# 监控网络连接
netstat -an | grep 8867
```

## 🤝 贡献指南

我们欢迎所有形式的贡献！

### 贡献方式
1. **报告问题**: 在GitHub Issues中报告bug或提出改进建议
2. **提交代码**: Fork项目后提交Pull Request
3. **完善文档**: 改进README、注释或添加示例
4. **分享经验**: 在Discussions中分享使用经验

### 开发流程
1. Fork本项目
2. 创建功能分支: `git checkout -b feature/new-feature`
3. 提交更改: `git commit -am 'Add new feature'`
4. 推送分支: `git push origin feature/new-feature`
5. 创建Pull Request

### 代码规范
- 遵循PEP 8 Python代码规范
- 添加适当的注释和文档字符串
- 编写单元测试覆盖新功能
- 保持向后兼容性

## 📄 许可证

本项目采用 [MIT许可证](LICENSE)。

## 🙏 致谢

- **MiniMax**: 优质的翻译和语音合成API
- **FastAPI**: 现代化的Python Web框架
- **Vue.js**: 响应式前端框架

## 📱 加入微信技术交流群

欢迎扫码加入我们的微信技术交流群，共同探索视频翻译的技术边界：

<img src="./同声传译交流群.jpeg" alt="微信技术交流群二维码" width="200"/>

---

**⭐ 如果这个项目对您有帮助，请给我们一个Star！**
