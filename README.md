# 🎙️ MiniMax实时同声传译系统

基于Whisper ASR、MiniMax翻译API和T2V语音合成技术的实时语音翻译系统，支持语音转文字、实时翻译和语音合成的完整流水线。

## ✨ 核心功能

- **🎤 实时语音识别**：采用Whisper Large模型，支持高精度多语言ASR
- **🌍 自动语言检测**：自动识别输入语言，无需手动选择
- **🔇 智能语音活动检测**：VAD算法优化，500ms静音检测，过滤噪音干扰
- **⚡ 实时翻译**：MiniMax API提供快速准确的多语言翻译
- **🔊 语音合成**：T2V API支持300+种音色的自然语音输出
- **💻 Web界面**：基于浏览器的现代化界面，支持麦克风访问
- **📋 队列管理**：智能任务队列，支持并发处理和超时控制
- **🎯 热词支持**：专业术语定制，提升特定领域翻译准确性
- **🎨 翻译风格**：支持默认、口语化、商务、学术四种翻译风格

## 🏗️ 系统架构

```
用户语音 → VAD检测 → Whisper ASR → 翻译队列 → MiniMax翻译
                                           ↓
浏览器播放 ← T2V合成 ← 音频合成 ← 翻译文本
```

## 🚀 快速开始

### 1. 环境要求

- **Python**: 3.10+
- **包管理器**: UV
- **系统工具**: OpenSSL（用于HTTPS证书）
- **硬件**: 支持麦克风的设备
- **网络**: 稳定的互联网连接

### 2. 安装部署

```bash
# 克隆项目
git clone https://github.com/zxwang2018/MiniMax-Simultaneous-Interpretation.git
cd MiniMax-Simultaneous-Interpretation/real-time-translator

# 安装依赖
uv sync

# 生成SSL证书（用于HTTPS访问）
mkdir -p certs
openssl req -x509 -newkey rsa:4096 -keyout certs/key.pem -out certs/cert.pem -days 365 -nodes -subj "/C=CN/ST=Beijing/L=Beijing/O=RealTimeTranslator/CN=localhost"
```

### 3. 配置API密钥

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑配置文件，填入你的API密钥
nano .env
```

**必填配置项**：
```env
MINIMAX_API_KEY=你的MiniMax_API密钥
T2V_API_KEY=你的T2V_API密钥
VOICE_ID=male-qn-qingse
```

### 4. 启动服务

```bash
# 本地访问模式
python run.py

# 远程访问模式（支持其他设备访问）
python run_remote.py

# 或使用UV运行
uv run python run_remote.py
```

### 5. 访问系统

**本地访问**：
- 🌐 **主界面**: https://localhost:18867/frontend
- 📚 **API文档**: https://localhost:18867/docs
- ❤️ **健康检查**: https://localhost:18867/health

**远程访问**：
- 🌐 **主界面**: https://你的服务器IP:18867/frontend
- 📚 **API文档**: https://你的服务器IP:18867/docs

## 🎯 使用指南

### 基本操作流程

1. **🔧 配置系统**：输入MiniMax和T2V的API密钥
2. **🎤 开始录音**：点击"开始录音"按钮
3. **🗣️ 自然对话**：正常语速说话，系统自动检测语音段落
4. **👀 查看结果**：实时显示语音识别和翻译结果
5. **🔊 听取翻译**：系统自动播放合成的语音翻译

### 高级功能

**热词定制**：
- 在"热词/专业术语"文本框中输入专业词汇
- 每行一个词汇，提升特定领域翻译准确性

**翻译风格选择**：
- **默认**：标准翻译风格
- **口语化**：更贴近日常对话的表达
- **商务场景**：适合商务沟通的正式表达
- **学术场景**：适合学术交流的专业表达

## ⚙️ 配置选项

### 环境变量说明

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `MINIMAX_API_KEY` | MiniMax翻译API密钥 | 必填 |
| `T2V_API_KEY` | T2V语音合成API密钥 | 必填 |
| `VOICE_ID` | 语音合成音色ID | `male-qn-qingse` |
| `HOST` | 服务器主机地址 | `0.0.0.0` |
| `PORT` | 服务器端口 | `18867` |
| `WHISPER_MODEL` | Whisper模型大小 | `large` |
| `VAD_MODE` | VAD算法严格程度(0-3) | `3` |
| `SILENCE_THRESHOLD_MS` | 静音检测阈值(毫秒) | `500` |
| `MAX_CONCURRENT_TRANSLATIONS` | 最大并发翻译数 | `3` |

### 支持的语言

**输入语言**：自动检测（支持Whisper识别的所有语言）
- 中文（普通话、粤语等方言）
- 英语、日语、韩语
- 法语、德语、西班牙语等

**输出语言**：
- 中文、English、日本語、한국어
- Español、Français、Deutsch等

### 推荐音色

**中文音色**：
- `male-qn-qingse`：男声，清澈磁性
- `female-shaonv`：女声，温柔甜美
- `broadcaster_male`：男播音员，专业标准

**英文音色**：
- `male-youthful`：年轻男声
- `female-americana`：美式女声

## 🖥️ 系统要求

### 最低配置
- **内存**: 8GB（Whisper Large模型）
- **存储**: 10GB可用空间
- **CPU**: 4核心以上
- **网络**: 稳定的互联网连接

### 推荐配置
- **内存**: 16GB以上
- **显卡**: NVIDIA GTX 1660+（CUDA加速）
- **CPU**: 8核心以上
- **网络**: 高速网络连接

### CUDA加速配置

```bash
# 检查CUDA可用性
python -c "import torch; print(f'CUDA可用: {torch.cuda.is_available()}')"

# 启用GPU加速（推荐）
export WHISPER_DEVICE=cuda

# 如需使用CPU模式
export WHISPER_DEVICE=cpu
```

## 🔧 系统架构详解

### 后端组件

- **FastAPI**: Web服务器，支持WebSocket实时通信
- **Whisper服务**: 语音识别，支持模型预加载和CUDA加速
- **音频处理器**: VAD语音活动检测和音频分块
- **翻译队列**: 智能队列管理，支持并发和超时控制
- **API客户端**: MiniMax翻译和T2V语音合成集成

### 关键文件结构

```
real-time-translator/
├── backend/
│   ├── app.py                    # FastAPI主应用
│   ├── services/
│   │   ├── whisper_service.py    # Whisper ASR服务
│   │   ├── audio_processor.py    # VAD和音频处理
│   │   ├── translation_queue.py  # 队列管理
│   │   └── websocket_handler.py  # WebSocket通信
│   └── api_clients/
│       ├── minimax_client.py     # MiniMax翻译客户端
│       └── t2v_client.py         # T2V语音合成客户端
├── certs/                        # SSL证书目录
├── models/                       # Whisper模型持久化目录
└── run_remote.py                 # 远程访问启动脚本
```

## 🐛 故障排除

### 常见问题解决

**HTTPS证书错误**
```bash
# 重新生成证书
rm -rf certs/
mkdir certs
openssl req -x509 -newkey rsa:4096 -keyout certs/key.pem -out certs/cert.pem -days 365 -nodes -subj "/C=CN/ST=Beijing/L=Beijing/O=RealTimeTranslator/CN=localhost"
```

**麦克风访问被拒绝**
- 确保使用HTTPS协议访问
- 在浏览器中允许麦克风权限
- 检查系统麦克风设置

**Whisper模型加载失败**
```bash
# 检查CUDA环境
python -c "import torch; print(torch.cuda.is_available())"

# 强制使用CPU模式
export WHISPER_DEVICE=cpu
```

**API连接错误**
- 检查`.env`文件中的API密钥配置
- 验证网络连接状态
- 查看API调用频率限制

### 性能优化建议

**启用GPU加速**
```bash
# 使用CUDA加速Whisper
export WHISPER_DEVICE=cuda
```

**内存优化**
```bash
# 测试时使用小模型
export WHISPER_MODEL=base
```

**VAD参数调优**
```bash
# 降低噪音敏感度
export VAD_MODE=2
# 调整静音检测阈值
export SILENCE_THRESHOLD_MS=800
```

## 📖 技术文档

- **交互式API文档**: https://localhost:18867/docs
- **ReDoc文档**: https://localhost:18867/redoc
- **OpenAPI规范**: https://localhost:18867/openapi.json

## 🔒 安全提醒

- **API密钥安全**: 请妥善保管你的API密钥，不要在代码中硬编码
- **HTTPS访问**: 生产环境请使用正式SSL证书
- **防火墙设置**: 适当配置防火墙规则

## 🤝 开发贡献

欢迎提交Issue和Pull Request！

1. Fork本仓库
2. 创建功能分支
3. 提交更改
4. 添加测试
5. 发起Pull Request

## 📝 开源协议

MIT License - 详见LICENSE文件

## 💬 技术支持

遇到问题时请按以下步骤：

1. 查看故障排除章节
2. 检查API文档说明
3. 在GitHub Issues中搜索相关问题
4. 创建新Issue并提供详细日志

## 🙏 致谢

本项目基于以下优秀的开源项目：

- **OpenAI Whisper**: 语音识别模型
- **FastAPI**: 现代化Web框架
- **MiniMax API**: 高质量翻译服务
- **T2V API**: 自然语音合成服务

---

**⭐ 如果这个项目对你有帮助，请给个Star支持！**