"""数据库模型与初始化"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Enum as SAEnum
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()


class Record(Base):
    """记录表 - 保存用户的所有输入（想法、心情、知识、妙思）"""
    __tablename__ = "records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), default="default", index=True)
    content = Column(Text, nullable=False)
    content_type = Column(String(32), default="text")  # text / image / file / markdown
    mood = Column(String(32), nullable=True)  # 心情标签
    tags = Column(JSON, default=list)  # 标签列表
    media_paths = Column(JSON, default=list)  # 媒体文件路径
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联
    solutions = relationship("Solution", back_populates="record")


class Solution(Base):
    """方案表 - WYG Agent 产出的方案"""
    __tablename__ = "solutions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    record_id = Column(Integer, ForeignKey("records.id"), index=True)
    user_id = Column(String(64), default="default", index=True)
    phase = Column(String(32), default="explore")  # explore / propose / apply / archive
    ba_output = Column(Text, nullable=True)  # BA 需求探索纪要
    sa_output = Column(Text, nullable=True)  # SA 方案设计
    rr_verdict = Column(String(16), nullable=True)  # pass / fail
    pm_tasks = Column(JSON, nullable=True)  # PM 任务列表
    status = Column(String(32), default="pending")  # pending / in_progress / completed / archived
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    record = relationship("Record", back_populates="solutions")


class ChatMessage(Base):
    """对话消息表 - BA 与用户的澄清对话"""
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    solution_id = Column(Integer, ForeignKey("solutions.id"), index=True)
    role = Column(String(16), nullable=False)  # user / assistant / system
    agent = Column(String(16), nullable=True)  # ba / sa / rr / pm / dev / cr / te
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


async def init_db():
    """初始化数据库（创建表）"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:
    """获取数据库会话"""
    async with async_session() as session:
        yield session
