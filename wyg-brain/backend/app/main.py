"""WYG Brain - 外脑 App 后端入口"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.core.config import settings
from app.models.database import init_db
from app.api.routes import router
from app.services.ws import manager

# 前端静态文件路径
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'frontend')


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化数据库"""
    await init_db()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS - 允许所有来源（开发阶段）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(router)


# WebSocket 端点
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket 实时同步端点"""
    await manager.handle_websocket(websocket, user_id)


# 健康检查
@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}


# API 状态
@app.get("/api/status")
async def api_status():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "llm_provider": settings.DEFAULT_LLM_PROVIDER.value,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)


# 静态文件服务（前端）- 必须放在最后，避免覆盖 API 路由
if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
