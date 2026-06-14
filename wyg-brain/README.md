# WYG Brain - 外脑 App

你的 AI 决策伙伴——随时记录一切，AI 自动分析、出方案、拆任务。

## 架构

```
Flutter App (Android) ←→ FastAPI Backend ←→ WYG Agent Engine
       ↕                        ↕
Flutter Web (电脑端)      WebSocket 实时同步
```

## 后端启动

```bash
cd backend
pip install -r requirements.txt
# 配置 .env
cp .env.example .env
# 编辑 .env 填入 DEEPSEEK_API_KEY

# 启动
python -m app.main
# 或
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/records` | POST | 创建记录 |
| `/api/records` | GET | 获取记录列表 |
| `/api/wyg/explore` | POST | /WYG explore 阶段 |
| `/api/wyg/propose` | POST | /WYG propose 阶段 |
| `/api/wyg/chat` | POST | 与 BA 对话 |
| `/api/wyg/solutions/{id}` | GET | 获取方案详情 |
| `/ws/{user_id}` | WebSocket | 实时同步 |
| `/health` | GET | 健康检查 |

## LLM 配置

支持三个 LLM 提供者，通过 `.env` 配置：

| 提供者 | 环境变量 | 默认 |
|--------|---------|------|
| DeepSeek | `DEEPSEEK_API_KEY` | ✅ 主力 |
| 豆包 | `DOUBAO_API_KEY` | 备用 |
| Ollama | `OLLAMA_BASE_URL` | 未来 |

## 技术栈

- **后端**: FastAPI + SQLAlchemy + SQLite
- **AI**: WYG Agent Engine (7 Agent 流水线)
- **LLM**: DeepSeek / 豆包 / Ollama（抽象层可切换）
- **实时同步**: WebSocket
- **前端**: Flutter (Android + Web)
