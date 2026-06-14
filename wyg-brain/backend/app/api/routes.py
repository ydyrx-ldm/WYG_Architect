"""API 路由 - /WYG 端点"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
from app.models.database import get_db, Record, Solution, ChatMessage
from app.agents.engine import WYGPipeline

router = APIRouter(prefix="/api", tags=["wyg-brain"])


# ============================================================
# 请求/响应模型
# ============================================================

class RecordCreate(BaseModel):
    content: str
    content_type: str = "text"
    mood: Optional[str] = None
    tags: list[str] = []


class RecordResponse(BaseModel):
    id: int
    content: str
    content_type: str
    mood: Optional[str]
    tags: list
    created_at: str

    class Config:
        from_attributes = True


class WYGRequest(BaseModel):
    requirement: str
    record_id: Optional[int] = None  # 关联已有记录


class WYGExploreResponse(BaseModel):
    solution_id: int
    ba_output: str


class WYGProposeRequest(BaseModel):
    solution_id: int
    confirmed: bool = True  # 用户确认 explore 结果后进入 propose


class ChatRequest(BaseModel):
    solution_id: int
    message: str


class ChatResponse(BaseModel):
    role: str
    agent: str
    content: str


# ============================================================
# 记录 API
# ============================================================

@router.post("/records", response_model=RecordResponse)
async def create_record(
    data: RecordCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建一条记录"""
    record = Record(
        content=data.content,
        content_type=data.content_type,
        mood=data.mood,
        tags=data.tags,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return RecordResponse(
        id=record.id,
        content=record.content,
        content_type=record.content_type,
        mood=record.mood,
        tags=record.tags or [],
        created_at=record.created_at.isoformat(),
    )


@router.get("/records", response_model=list[RecordResponse])
async def list_records(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """获取记录列表"""
    from sqlalchemy import select
    stmt = select(Record).order_by(Record.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    records = result.scalars().all()
    return [
        RecordResponse(
            id=r.id,
            content=r.content,
            content_type=r.content_type,
            mood=r.mood,
            tags=r.tags or [],
            created_at=r.created_at.isoformat(),
        )
        for r in records
    ]


# ============================================================
# /WYG API
# ============================================================

@router.post("/wyg/explore", response_model=WYGExploreResponse)
async def wyg_explore(
    data: WYGRequest,
    db: AsyncSession = Depends(get_db),
):
    """/WYG explore 阶段：BA 反问澄清"""
    pipeline = WYGPipeline()

    # 创建或关联记录
    if data.record_id:
        record = await db.get(Record, data.record_id)
        if not record:
            raise HTTPException(404, "Record not found")
    else:
        record = Record(content=data.requirement, content_type="text")
        db.add(record)
        await db.flush()

    # 创建 Solution
    solution = Solution(
        record_id=record.id,
        phase="explore",
        status="in_progress",
    )
    db.add(solution)
    await db.flush()

    # BA 执行
    ba_output = await pipeline.explore(data.requirement)

    # 保存结果
    solution.ba_output = ba_output
    solution.status = "completed"
    await db.commit()
    await db.refresh(solution)

    return WYGExploreResponse(
        solution_id=solution.id,
        ba_output=ba_output,
    )


@router.post("/wyg/propose")
async def wyg_propose(
    data: WYGProposeRequest,
    db: AsyncSession = Depends(get_db),
):
    """/WYG propose 阶段：SA 方案设计 + PM 拆任务 + RR 准入"""
    solution = await db.get(Solution, data.solution_id)
    if not solution:
        raise HTTPException(404, "Solution not found")
    if not solution.ba_output:
        raise HTTPException(400, "Explore phase not completed")

    pipeline = WYGPipeline()
    result = await pipeline.propose(solution.ba_output)

    # 保存结果
    solution.sa_output = result["sa_output"]
    solution.pm_tasks = result["pm_output"]
    solution.rr_verdict = "pass" if "通过" in result["rr_output"] else "fail"
    solution.phase = "propose"
    await db.commit()

    return {
        "solution_id": solution.id,
        "sa_output": result["sa_output"],
        "pm_output": result["pm_output"],
        "rr_output": result["rr_output"],
        "rr_verdict": solution.rr_verdict,
    }


@router.post("/wyg/chat", response_model=ChatResponse)
async def wyg_chat(
    data: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """与 BA 对话（explore 阶段的澄清对话）"""
    solution = await db.get(Solution, data.solution_id)
    if not solution:
        raise HTTPException(404, "Solution not found")

    # 保存用户消息
    user_msg = ChatMessage(
        solution_id=solution.id,
        role="user",
        content=data.message,
    )
    db.add(user_msg)

    # 加载历史对话
    from sqlalchemy import select
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.solution_id == solution.id)
        .order_by(ChatMessage.created_at)
    )
    result = await db.execute(stmt)
    history_msgs = result.scalars().all()
    history = [{"role": m.role, "content": m.content} for m in history_msgs]

    # BA 回复
    pipeline = WYGPipeline()
    ba_reply = await pipeline.explore(data.message, history)

    # 保存 BA 回复
    assistant_msg = ChatMessage(
        solution_id=solution.id,
        role="assistant",
        agent="BA",
        content=ba_reply,
    )
    db.add(assistant_msg)
    await db.commit()

    return ChatResponse(
        role="assistant",
        agent="BA",
        content=ba_reply,
    )


@router.get("/wyg/solutions/{solution_id}")
async def get_solution(
    solution_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取方案详情"""
    solution = await db.get(Solution, solution_id)
    if not solution:
        raise HTTPException(404, "Solution not found")
    return {
        "id": solution.id,
        "record_id": solution.record_id,
        "phase": solution.phase,
        "ba_output": solution.ba_output,
        "sa_output": solution.sa_output,
        "rr_verdict": solution.rr_verdict,
        "pm_tasks": solution.pm_tasks,
        "status": solution.status,
        "created_at": solution.created_at.isoformat(),
        "updated_at": solution.updated_at.isoformat(),
    }
