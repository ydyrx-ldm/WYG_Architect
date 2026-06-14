"""WebSocket 实时同步服务"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set
import json
import asyncio


class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        # user_id -> set of websocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str = "default"):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)

    def disconnect(self, websocket: WebSocket, user_id: str = "default"):
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def broadcast_to_user(self, user_id: str, message: dict):
        """向同一用户的所有连接广播消息"""
        if user_id in self.active_connections:
            data = json.dumps(message, ensure_ascii=False)
            dead = set()
            for ws in self.active_connections[user_id]:
                try:
                    await ws.send_text(data)
                except Exception:
                    dead.add(ws)
            # 清理断开的连接
            self.active_connections[user_id] -= dead

    async def handle_websocket(self, websocket: WebSocket, user_id: str = "default"):
        """处理 WebSocket 连接生命周期"""
        await self.connect(websocket, user_id)
        try:
            while True:
                data = await websocket.receive_text()
                msg = json.loads(data)
                msg_type = msg.get("type", "unknown")

                if msg_type == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                elif msg_type == "record_update":
                    # 记录更新 → 广播给同用户的其他设备
                    await self.broadcast_to_user(user_id, {
                        "type": "record_updated",
                        "data": msg.get("data", {}),
                    })
                elif msg_type == "agent_stream":
                    # Agent 流式输出 → 广播
                    await self.broadcast_to_user(user_id, {
                        "type": "agent_stream",
                        "data": msg.get("data", {}),
                    })
                else:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": f"Unknown message type: {msg_type}",
                    }))
        except WebSocketDisconnect:
            self.disconnect(websocket, user_id)


# 全局连接管理器
manager = ConnectionManager()
