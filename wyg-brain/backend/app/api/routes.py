"""API 路由 - /WYG 端点"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
from app.models.database import get_db, Record, Solution, ChatMessage
from app.agents.engine import WYGPipeline

logger = logging.getLogger(__name__)
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


class ReviseRequest(BaseModel):
    solution_id: int
    message: str  # 用户的追问或修改意见


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
    try:
        ba_output = await pipeline.explore(data.requirement)
    except Exception as e:
        logger.error(f"BA explore failed: {e}", exc_info=True)
        raise HTTPException(500, f"AI 调用失败: {str(e)}")

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
    try:
        result = await pipeline.propose(solution.ba_output)
    except Exception as e:
        logger.error(f"SA propose failed: {e}", exc_info=True)
        raise HTTPException(500, f"AI 调用失败: {str(e)}")

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
        "summary_output": result.get("summary_output", ""),
    }


@router.post("/wyg/revise")
async def wyg_revise(
    data: ReviseRequest,
    db: AsyncSession = Depends(get_db),
):
    """/WYG propose 阶段追问/修改：基于已有方案 + 用户反馈，SA 重新设计"""
    solution = await db.get(Solution, data.solution_id)
    if not solution:
        raise HTTPException(404, "Solution not found")
    if not solution.sa_output:
        raise HTTPException(400, "Propose phase not completed")

    pipeline = WYGPipeline()
    try:
        # SA 基于已有方案 + 用户反馈重新设计
        sa_output = await pipeline.agents["SA"].run(
            f"用户对以下方案有反馈，请根据反馈修改方案：\n\n"
            f"【当前方案】\n{solution.sa_output}\n\n"
            f"【用户反馈】\n{data.message}"
        )

        # PM 重新拆解任务
        pm_output = await pipeline.agents["PM"].run(
            f"基于以下修改后的方案设计，拆解为可执行的任务列表：\n\n{sa_output}"
        )

        # RR 重新准入评审
        rr_output = await pipeline.agents["RR"].run(
            f"评审以下修改后的方案是否满足准入标准：\n\n方案设计：{sa_output}\n\n任务列表：{pm_output}"
        )

        # 重新生成决策摘要
        summary_output = await pipeline.agents["SUMMARY"].run(
            f"请根据以下信息，生成用户友好的决策摘要：\n\n"
            f"【需求探索】{solution.ba_output}\n\n"
            f"【方案设计】{sa_output}\n\n"
            f"【任务列表】{pm_output}\n\n"
            f"【准入评审】{rr_output}\n\n"
            f"【用户反馈】{data.message}"
        )
    except Exception as e:
        logger.error(f"Revise failed: {e}", exc_info=True)
        raise HTTPException(500, f"AI 调用失败: {str(e)}")

    # 更新方案
    solution.sa_output = sa_output
    solution.pm_tasks = pm_output
    solution.rr_verdict = "pass" if "通过" in rr_output else "fail"
    await db.commit()

    return {
        "solution_id": solution.id,
        "sa_output": sa_output,
        "pm_output": pm_output,
        "rr_output": rr_output,
        "rr_verdict": solution.rr_verdict,
        "summary_output": summary_output,
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

    # 加载历史对话（包含 BA 的历史回复，让 BA 知道自己问过什么）
    from sqlalchemy import select
    import re
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.solution_id == solution.id)
        .order_by(ChatMessage.created_at)
    )
    result = await db.execute(stmt)
    history_msgs = result.scalars().all()
    # 构建完整历史：用户原始需求 + BA 的首次回复 + 后续对话
    history = []
    # 用户的原始需求（从关联的 Record 获取）
    if solution.record_id:
        record = await db.get(Record, solution.record_id)
        if record:
            history.append({"role": "user", "content": f"[用户原始需求] {record.content}"})
    # BA 的首次回复
    if solution.ba_output:
        history.append({"role": "assistant", "content": solution.ba_output})
    # 后续对话
    for m in history_msgs:
        history.append({"role": m.role, "content": m.content})

    # 提取已澄清的维度（问题+用户选择），防止重复问同一维度
    clarified_dimensions = []  # 每项 = {"question": "问题文本", "keywords": ["关键词1",...], "options": ["选项1",...]}
    all_banned_keywords = set()  # 所有已问问题的核心关键词

    def extract_qa_pairs(text):
        """从 BA 回复中提取 问题+选项 对，返回结构化数据"""
        pairs = []
        lines = text.split('\n')
        current_q = None
        current_opts = []

        for line in lines:
            stripped = line.strip()
            # 检测问题标题行
            q_match = re.match(r'^(?:问题\s*\d+|Q\d+)[：:]\s*(.+)', stripped)
            if q_match:
                # 保存上一个问题
                if current_q:
                    pairs.append({"question": current_q, "options": current_opts})
                current_q = q_match.group(1).strip()
                current_opts = []
                continue

            # 检测选项行
            opt_match = re.match(r'^[A-C][)\．.）]\s*(.+)', stripped)
            if opt_match and current_q is not None:
                current_opts.append(opt_match.group(1).strip())
                continue

            # 空行 = 问题分隔
            if stripped == '' and current_q:
                pairs.append({"question": current_q, "options": current_opts})
                current_q = None
                current_opts = []

        # 保存最后一个问题
        if current_q:
            pairs.append({"question": current_q, "options": current_opts})

        return pairs

    def extract_keywords(question_text: str, options: list) -> list:
        """从问题文本和选项中提取核心关键词（去掉停用词）"""
        stopwords = {'的', '了', '吗', '呢', '吧', '啊', '呀', '是', '有', '在', '你', '我',
                     '想', '要', '去', '会', '能', '可以', '什么', '怎么', '如何', '哪个',
                     '哪些', '还是', '或者', '和', '与', '及', '等', '对', '最', '比较',
                     '更', '很', '非常', '偏好', '喜欢', '倾向', '选择', '希望', '主要',
                     '安排', '关注', '考虑', '需求', '要求', '类型', '方面', '方向'}
        # 合并问题文本和选项
        all_text = question_text + ' ' + ' '.join(options)
        # 分词（简单按标点和空格切分）
        words = re.findall(r'[\u4e00-\u9fff]{2,}|[a-zA-Z]+', all_text)
        keywords = [w for w in words if w not in stopwords]
        return keywords

    # 从 BA 的首次回复中提取问题
    if solution.ba_output:
        for pair in extract_qa_pairs(solution.ba_output):
            kws = extract_keywords(pair["question"], pair["options"])
            clarified_dimensions.append(pair)
            all_banned_keywords.update(kws)

    # 从后续 BA 回复中提取问题
    for m in history_msgs:
        if m.role == "assistant" and m.content:
            for pair in extract_qa_pairs(m.content):
                kws = extract_keywords(pair["question"], pair["options"])
                clarified_dimensions.append(pair)
                all_banned_keywords.update(kws)

    # 从用户回复中提取已选答案
    user_answers = []
    for m in history_msgs:
        if m.role == "user" and m.content:
            for line in m.content.split('\n'):
                if '→' in line:
                    user_answers.append(line.strip())

    # 构建增强的用户消息
    enhanced_message = data.message
    context_parts = []
    if clarified_dimensions or user_answers:
        context_parts.append("【已澄清的维度，绝对不要再问这些方向的问题！以下每个问题及其变体都已问过，禁止重复！】")
        if clarified_dimensions:
            context_parts.append("")
            context_parts.append("已问过的问题（禁止再问，也禁止换种说法问同一维度）：")
            for idx, dim in enumerate(clarified_dimensions, 1):
                opts_str = " / ".join(dim["options"]) if dim["options"] else ""
                line = f"  {idx}. {dim['question']}"
                if opts_str:
                    line += f"（选项：{opts_str}）"
                context_parts.append(line)
        if all_banned_keywords:
            context_parts.append("")
            context_parts.append("禁止涉及的关键词维度（任何包含这些关键词的问题都不允许）：")
            context_parts.append(f"  {', '.join(sorted(all_banned_keywords))}")
        if user_answers:
            context_parts.append("")
            context_parts.append("用户已选答案：")
            for a in user_answers:
                context_parts.append(f"  - {a}")
        context_parts.append("")
        context_parts.append(f"【用户最新回复】{data.message}")
        context_parts.append("")
        context_parts.append('你必须问全新的、与以上任何维度都不重叠的问题。如果需求已足够清晰，输出"需求已澄清"并附上需求摘要。')
        enhanced_message = "\n".join(context_parts)

    # BA 回复
    pipeline = WYGPipeline()
    try:
        ba_reply = await pipeline.explore(enhanced_message, history)
    except Exception as e:
        logger.error(f"BA chat failed: {e}", exc_info=True)
        raise HTTPException(500, f"AI 调用失败: {str(e)}")

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


# ============================================================
# 猜词游戏 API
# ============================================================

import random as _random
import uuid as _uuid
import time as _time
import sys as _sys
import os as _os

# 将 mcp-chinese-dict 加入路径以复用词林
_MCP_DICT_PATH = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))), "mcp-chinese-dict")
if _MCP_DICT_PATH not in _sys.path:
    _sys.path.insert(0, _MCP_DICT_PATH)

# 词林加载（惰性初始化）
_cilin_loader = None

def _get_cilin():
    global _cilin_loader
    if _cilin_loader is None:
        try:
            from loaders.cilin_loader import get_loader
            _cilin_loader = get_loader()
        except Exception as e:
            logger.warning(f"Cilin loader unavailable: {e}")
            _cilin_loader = False  # 标记不可用
    return _cilin_loader if _cilin_loader is not False else None

# 内存中的游戏会话（无需持久化）
_game_sessions: dict[str, dict] = {}

# 词库按类别分组，用于即时语义相似度计算
_WORD_CATEGORIES = {
    "城市": ["中国", "北京", "上海", "广州", "深圳", "杭州", "成都", "西安", "南京", "武汉"],
    "景点": ["长城", "故宫", "黄河", "长江", "泰山", "黄山", "西湖", "太湖", "昆仑", "珠峰",
              "兵马俑", "敦煌", "颐和园", "天坛", "鸟巢", "东方明珠", "外滩", "洪崖洞", "鼓浪屿"],
    "节日": ["春节", "中秋", "端午", "清明", "元宵", "重阳", "国庆", "元旦", "圣诞", "感恩"],
    "天文": ["太阳", "月亮", "星星", "地球", "火星", "宇宙", "银河", "彗星", "极光", "日食"],
    "水果": ["苹果", "香蕉", "西瓜", "葡萄", "芒果", "荔枝", "榴莲", "樱桃", "草莓", "菠萝"],
    "动物": ["老虎", "狮子", "大象", "熊猫", "企鹅", "海豚", "鲨鱼", "老鹰", "孔雀", "蝴蝶"],
    "乐器": ["钢琴", "吉他", "小提琴", "二胡", "笛子", "鼓", "萨克斯", "口琴", "古筝", "琵琶"],
    "运动": ["篮球", "足球", "网球", "乒乓", "游泳", "跑步", "滑雪", "攀岩", "骑行", "射箭"],
    "饮品": ["咖啡", "奶茶", "可乐", "果汁", "红酒", "啤酒", "绿茶", "豆浆", "酸奶", "矿泉"],
    "交通": ["飞机", "高铁", "地铁", "公交", "出租", "轮船", "自行车", "摩托", "直升机", "缆车"],
    "电子": ["手机", "电脑", "电视", "冰箱", "空调", "相机", "手表", "耳机", "音箱", "平板"],
    "场所": ["学校", "医院", "银行", "超市", "公园", "博物馆", "图书馆", "体育场", "机场", "车站"],
    "时间": ["春天", "夏天", "秋天", "冬天", "早晨", "中午", "傍晚", "深夜", "黎明", "黄昏"],
    "颜色": ["红色", "蓝色", "绿色", "黄色", "紫色", "橙色", "黑色", "白色", "粉色", "灰色"],
    "职业": ["医生", "老师", "警察", "消防", "工程师", "画家", "音乐家", "厨师", "飞行员", "农民"],
    "情感": ["爱情", "友情", "亲情", "梦想", "自由", "勇气", "智慧", "幸福", "希望", "和平"],
    "应用": ["微信", "淘宝", "抖音", "美团", "百度", "京东", "拼多多", "B站", "知乎", "微博"],
    "文学": ["红楼梦", "西游记", "水浒传", "三国演义", "诗经", "论语", "道德经", "史记", "聊斋", "山海经"],
}

# 扁平词库
_WORD_POOL = [w for words in _WORD_CATEGORIES.values() for w in words]

# 词→类别 反向索引
_WORD_TO_CATEGORY = {}
for cat, words in _WORD_CATEGORIES.items():
    for w in words:
        _WORD_TO_CATEGORY[w] = cat

# 类别关联度（不同类别之间的关联程度 0-100）
_CATEGORY_RELATIONS = {
    ("城市", "景点"): 70, ("景点", "城市"): 70,
    ("城市", "交通"): 55, ("交通", "城市"): 55,
    ("城市", "场所"): 60, ("场所", "城市"): 60,
    ("水果", "饮品"): 65, ("饮品", "水果"): 65,
    ("动物", "天文"): 15,
    ("乐器", "运动"): 20,
    ("运动", "饮品"): 35, ("饮品", "运动"): 35,
    ("节日", "文学"): 30, ("文学", "节日"): 30,
    ("节日", "城市"): 25, ("城市", "节日"): 25,
    ("电子", "应用"): 75, ("应用", "电子"): 75,
    ("电子", "交通"): 40, ("交通", "电子"): 40,
    ("颜色", "水果"): 45, ("水果", "颜色"): 45,
    ("颜色", "动物"): 30, ("动物", "颜色"): 30,
    ("时间", "节日"): 50, ("节日", "时间"): 50,
    ("职业", "场所"): 55, ("场所", "职业"): 55,
    ("情感", "文学"): 60, ("文学", "情感"): 60,
    ("天文", "时间"): 45, ("时间", "天文"): 45,
    ("景点", "文学"): 40, ("文学", "景点"): 40,
    ("动物", "水果"): 10,
    ("乐器", "电子"): 25, ("电子", "乐器"): 25,
    # 补充：所有类别对都有基础关联，确保不会全为0
    ("城市", "天文"): 20, ("天文", "城市"): 20,
    ("城市", "水果"): 12, ("水果", "城市"): 12,
    ("城市", "动物"): 12, ("动物", "城市"): 12,
    ("城市", "乐器"): 10, ("乐器", "城市"): 10,
    ("城市", "运动"): 15, ("运动", "城市"): 15,
    ("城市", "饮品"): 15, ("饮品", "城市"): 15,
    ("城市", "电子"): 20, ("电子", "城市"): 20,
    ("城市", "时间"): 18, ("时间", "城市"): 18,
    ("城市", "颜色"): 10, ("颜色", "城市"): 10,
    ("城市", "职业"): 25, ("职业", "城市"): 25,
    ("城市", "情感"): 15, ("情感", "城市"): 15,
    ("城市", "应用"): 20, ("应用", "城市"): 20,
    ("城市", "文学"): 30, ("文学", "城市"): 30,
    ("景点", "天文"): 25, ("天文", "景点"): 25,
    ("景点", "水果"): 10, ("水果", "景点"): 10,
    ("景点", "动物"): 15, ("动物", "景点"): 15,
    ("景点", "乐器"): 10, ("乐器", "景点"): 10,
    ("景点", "运动"): 20, ("运动", "景点"): 20,
    ("景点", "饮品"): 12, ("饮品", "景点"): 12,
    ("景点", "电子"): 15, ("电子", "景点"): 15,
    ("景点", "时间"): 25, ("时间", "景点"): 25,
    ("景点", "颜色"): 12, ("颜色", "景点"): 12,
    ("景点", "职业"): 15, ("职业", "景点"): 15,
    ("景点", "情感"): 20, ("情感", "景点"): 20,
    ("景点", "应用"): 15, ("应用", "景点"): 15,
    ("节日", "天文"): 20, ("天文", "节日"): 20,
    ("节日", "水果"): 15, ("水果", "节日"): 15,
    ("节日", "动物"): 12, ("动物", "节日"): 12,
    ("节日", "乐器"): 15, ("乐器", "节日"): 15,
    ("节日", "运动"): 15, ("运动", "节日"): 15,
    ("节日", "饮品"): 20, ("饮品", "节日"): 20,
    ("节日", "交通"): 15, ("交通", "节日"): 15,
    ("节日", "电子"): 12, ("电子", "节日"): 12,
    ("节日", "场所"): 20, ("场所", "节日"): 20,
    ("节日", "颜色"): 25, ("颜色", "节日"): 25,
    ("节日", "职业"): 12, ("职业", "节日"): 12,
    ("节日", "情感"): 35, ("情感", "节日"): 35,
    ("节日", "应用"): 10, ("应用", "节日"): 10,
    ("天文", "水果"): 8, ("水果", "天文"): 8,
    ("天文", "动物"): 10, ("动物", "天文"): 10,
    ("天文", "乐器"): 8, ("乐器", "天文"): 8,
    ("天文", "运动"): 10, ("运动", "天文"): 10,
    ("天文", "饮品"): 8, ("饮品", "天文"): 8,
    ("天文", "交通"): 12, ("交通", "天文"): 12,
    ("天文", "电子"): 15, ("电子", "天文"): 15,
    ("天文", "场所"): 12, ("场所", "天文"): 12,
    ("天文", "颜色"): 20, ("颜色", "天文"): 20,
    ("天文", "职业"): 8, ("职业", "天文"): 8,
    ("天文", "情感"): 15, ("情感", "天文"): 15,
    ("天文", "应用"): 10, ("应用", "天文"): 10,
    ("水果", "动物"): 12, ("动物", "水果"): 12,
    ("水果", "乐器"): 8, ("乐器", "水果"): 8,
    ("水果", "运动"): 10, ("运动", "水果"): 10,
    ("水果", "交通"): 8, ("交通", "水果"): 8,
    ("水果", "电子"): 10, ("电子", "水果"): 10,
    ("水果", "场所"): 15, ("场所", "水果"): 15,
    ("水果", "时间"): 12, ("时间", "水果"): 12,
    ("水果", "颜色"): 30, ("颜色", "水果"): 30,
    ("水果", "职业"): 8, ("职业", "水果"): 8,
    ("水果", "情感"): 10, ("情感", "水果"): 10,
    ("水果", "应用"): 8, ("应用", "水果"): 8,
    ("水果", "文学"): 10, ("文学", "水果"): 10,
    ("动物", "乐器"): 8, ("乐器", "动物"): 8,
    ("动物", "运动"): 15, ("运动", "动物"): 15,
    ("动物", "饮品"): 8, ("饮品", "动物"): 8,
    ("动物", "交通"): 10, ("交通", "动物"): 10,
    ("动物", "电子"): 8, ("电子", "动物"): 8,
    ("动物", "场所"): 20, ("场所", "动物"): 20,
    ("动物", "时间"): 15, ("时间", "动物"): 15,
    ("动物", "职业"): 10, ("职业", "动物"): 10,
    ("动物", "情感"): 15, ("情感", "动物"): 15,
    ("动物", "应用"): 8, ("应用", "动物"): 8,
    ("动物", "文学"): 15, ("文学", "动物"): 15,
    ("乐器", "运动"): 12, ("运动", "乐器"): 12,
    ("乐器", "饮品"): 10, ("饮品", "乐器"): 10,
    ("乐器", "交通"): 8, ("交通", "乐器"): 8,
    ("乐器", "场所"): 15, ("场所", "乐器"): 15,
    ("乐器", "时间"): 10, ("时间", "乐器"): 10,
    ("乐器", "颜色"): 10, ("颜色", "乐器"): 10,
    ("乐器", "职业"): 15, ("职业", "乐器"): 15,
    ("乐器", "情感"): 25, ("情感", "乐器"): 25,
    ("乐器", "文学"): 20, ("文学", "乐器"): 20,
    ("运动", "饮品"): 30, ("饮品", "运动"): 30,
    ("运动", "交通"): 15, ("交通", "运动"): 15,
    ("运动", "电子"): 12, ("电子", "运动"): 12,
    ("运动", "场所"): 25, ("场所", "运动"): 25,
    ("运动", "时间"): 15, ("时间", "运动"): 15,
    ("运动", "颜色"): 10, ("颜色", "运动"): 10,
    ("运动", "职业"): 20, ("职业", "运动"): 20,
    ("运动", "情感"): 20, ("情感", "运动"): 20,
    ("运动", "应用"): 10, ("应用", "运动"): 10,
    ("运动", "文学"): 12, ("文学", "运动"): 12,
    ("饮品", "交通"): 10, ("交通", "饮品"): 10,
    ("饮品", "电子"): 10, ("电子", "饮品"): 10,
    ("饮品", "场所"): 20, ("场所", "饮品"): 20,
    ("饮品", "时间"): 12, ("时间", "饮品"): 12,
    ("饮品", "颜色"): 15, ("颜色", "饮品"): 15,
    ("饮品", "职业"): 10, ("职业", "饮品"): 10,
    ("饮品", "情感"): 15, ("情感", "饮品"): 15,
    ("饮品", "应用"): 8, ("应用", "饮品"): 8,
    ("饮品", "文学"): 10, ("文学", "饮品"): 10,
    ("交通", "电子"): 20, ("电子", "交通"): 20,
    ("交通", "场所"): 25, ("场所", "交通"): 25,
    ("交通", "时间"): 15, ("时间", "交通"): 15,
    ("交通", "颜色"): 8, ("颜色", "交通"): 8,
    ("交通", "职业"): 15, ("职业", "交通"): 15,
    ("交通", "情感"): 10, ("情感", "交通"): 10,
    ("交通", "应用"): 12, ("应用", "交通"): 12,
    ("交通", "文学"): 10, ("文学", "交通"): 10,
    ("电子", "场所"): 20, ("场所", "电子"): 20,
    ("电子", "时间"): 12, ("时间", "电子"): 12,
    ("电子", "颜色"): 10, ("颜色", "电子"): 10,
    ("电子", "职业"): 12, ("职业", "电子"): 12,
    ("电子", "情感"): 10, ("情感", "电子"): 10,
    ("电子", "文学"): 10, ("文学", "电子"): 10,
    ("场所", "时间"): 15, ("时间", "场所"): 15,
    ("场所", "颜色"): 8, ("颜色", "场所"): 8,
    ("场所", "情感"): 15, ("情感", "场所"): 15,
    ("场所", "应用"): 15, ("应用", "场所"): 15,
    ("场所", "文学"): 20, ("文学", "场所"): 20,
    ("时间", "颜色"): 20, ("颜色", "时间"): 20,
    ("时间", "职业"): 10, ("职业", "时间"): 10,
    ("时间", "情感"): 25, ("情感", "时间"): 25,
    ("时间", "应用"): 8, ("应用", "时间"): 8,
    ("时间", "文学"): 15, ("文学", "时间"): 15,
    ("颜色", "职业"): 8, ("职业", "颜色"): 8,
    ("颜色", "情感"): 20, ("情感", "颜色"): 20,
    ("颜色", "应用"): 8, ("应用", "颜色"): 8,
    ("颜色", "文学"): 12, ("文学", "颜色"): 12,
    ("职业", "情感"): 15, ("情感", "职业"): 15,
    ("职业", "应用"): 10, ("应用", "职业"): 10,
    ("职业", "文学"): 15, ("文学", "职业"): 15,
    ("情感", "应用"): 10, ("应用", "情感"): 10,
    ("应用", "文学"): 12, ("文学", "应用"): 12,
}


# 三维语义向量表（独立模块）
from app.api.semantic_vectors import get_svt as _get_svt

# 初始化向量表并注入词库映射
_svt = _get_svt()
_svt.set_word_categories(_WORD_TO_CATEGORY)


def _calc_similarity(target: str, guess: str) -> int:
    """即时计算两词的语义相似度（0-100），三维向量表，<1ms

    三维综合：
    1. 关联表（名人→领域、品牌→产品）→ 80-95
    2. 类别向量 + 属性向量 → 8-100
    3. 词林近义链 + 字义关联 + 基础分 → 5-92
    """
    cilin = _get_cilin()
    return _svt.similarity(
        target, guess,
        word_categories=_WORD_TO_CATEGORY,
        word_pool=_WORD_POOL,
        cilin=cilin,
    )


class GameStartResponse(BaseModel):
    game_id: str
    word_length: int
    hint: str


class GameGuessRequest(BaseModel):
    game_id: str
    guess: str


class GameGuessResponse(BaseModel):
    probability: int
    is_correct: bool
    guess: str
    hint: str
    history: list[dict]
    bonus_hint: str


@router.post("/game/start", response_model=GameStartResponse)
async def game_start():
    """开始一局猜词游戏：随机选词，返回 game_id"""
    target = _random.choice(_WORD_POOL)
    game_id = str(_uuid.uuid4())[:8]

    _game_sessions[game_id] = {
        "target": target,
        "history": [],
        "started_at": _time.time(),
    }

    # 提示：只给词长，不给首字
    hint = f"{len(target)}字词语"

    return GameStartResponse(
        game_id=game_id,
        word_length=len(target),
        hint=hint,
    )


@router.post("/game/guess", response_model=GameGuessResponse)
async def game_guess(data: GameGuessRequest):
    """猜词：即时计算语义相关度（无 LLM 调用，<1ms）"""
    session = _game_sessions.get(data.game_id)
    if not session:
        raise HTTPException(404, "游戏不存在或已结束")

    guess = data.guess.strip()
    target = session["target"]

    # 即时计算相似度
    probability = _calc_similarity(target, guess)
    is_correct = (guess == target)

    if is_correct:
        hint = f"恭喜猜中！答案是「{target}」"
    elif probability >= 80:
        hint = "非常接近！再想想"
    elif probability >= 60:
        hint = "有关联，继续猜"
    elif probability >= 30:
        hint = "有一点关系"
    elif probability >= 10:
        hint = "联系不大，换个方向试试"
    else:
        hint = "差得远呢"

    # 记录历史
    session["history"].append({
        "guess": guess,
        "probability": probability,
    })

    # 渐进提示：每5次给一个提示（类别→首字→尾字）
    guess_count = len(session["history"])
    bonus_hint = ""
    if not is_correct:
        t_cat = _WORD_TO_CATEGORY.get(target, "")
        if guess_count == 5:
            bonus_hint = f"💡 提示：属于「{t_cat}」类" if t_cat else ""
        elif guess_count == 10:
            bonus_hint = f"💡 提示：首字是「{target[0]}」"
        elif guess_count == 15:
            bonus_hint = f"💡 提示：尾字是「{target[-1]}」"

    # 按概率降序排列历史
    sorted_history = sorted(
        session["history"],
        key=lambda x: x["probability"],
        reverse=True,
    )

    return GameGuessResponse(
        probability=probability,
        is_correct=is_correct,
        guess=guess,
        hint=hint,
        history=sorted_history,
        bonus_hint=bonus_hint,
    )


class GamePreviewRequest(BaseModel):
    game_id: str
    guess: str


class GamePreviewResponse(BaseModel):
    probability: int
    guess: str


@router.post("/game/preview", response_model=GamePreviewResponse)
async def game_preview(data: GamePreviewRequest):
    """实时预览：输入时即时返回相似度（不记录历史）"""
    session = _game_sessions.get(data.game_id)
    if not session:
        raise HTTPException(404, "游戏不存在或已结束")

    guess = data.guess.strip()
    if not guess:
        return GamePreviewResponse(probability=0, guess=guess)

    target = session["target"]
    probability = _calc_similarity(target, guess)

    return GamePreviewResponse(probability=probability, guess=guess)


@router.post("/game/giveup")
async def game_giveup(data: GameGuessRequest):
    """放弃游戏，揭晓答案"""
    session = _game_sessions.get(data.game_id)
    if not session:
        raise HTTPException(404, "游戏不存在或已结束")

    target = session["target"]
    del _game_sessions[data.game_id]
    return {"answer": target}
