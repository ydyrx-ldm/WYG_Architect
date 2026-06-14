# WYG Brain - 外脑 App

你的 AI 决策伙伴——随时记录一切，AI 自动分析、出方案、拆任务。

## 快速开始

```bash
cd backend
pip install -r requirements.txt

# 配置 API Key
cp .env.example .env
# 编辑 .env 填入 DEEPSEEK_API_KEY

# 启动（后端 + 前端一体）
python -m app.main
```

打开浏览器访问 **http://localhost:8000** 即可使用。

## 架构

```
Web 前端 (HTML/CSS/JS)  ←→  FastAPI 后端  ←→  WYG Agent Engine
        ↕                        ↕
   浏览器直接访问            WebSocket 实时同步
```

## API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 前端页面 |
| `/api/records` | POST | 创建记录 |
| `/api/records` | GET | 获取记录列表 |
| `/api/wyg/explore` | POST | /WYG explore 阶段 |
| `/api/wyg/propose` | POST | /WYG propose 阶段 |
| `/api/wyg/chat` | POST | 与 BA 对话 |
| `/api/wyg/solutions/{id}` | GET | 获取方案详情 |
| `/ws/{user_id}` | WebSocket | 实时同步 |
| `/health` | GET | 健康检查 |
| `/docs` | GET | API 文档 |

## LLM 配置

支持三个 LLM 提供者，通过 `.env` 配置：

| 提供者 | 环境变量 | 默认 |
|--------|---------|------|
| DeepSeek | `DEEPSEEK_API_KEY` | ✅ 主力 |
| 豆包 | `DOUBAO_API_KEY` | 备用 |
| Ollama | `OLLAMA_BASE_URL` | 未来 |

## 技术栈

- **前端**: HTML + CSS + JavaScript（零依赖，浏览器直接打开）
- **后端**: FastAPI + SQLAlchemy + SQLite
- **AI**: WYG Agent Engine (7 Agent 流水线)
- **LLM**: DeepSeek / 豆包 / Ollama（抽象层可切换）
- **实时同步**: WebSocket
