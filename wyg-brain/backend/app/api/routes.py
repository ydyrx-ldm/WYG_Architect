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
from app.core.llm import get_llm as _get_llm

# 内存中的游戏会话（无需持久化）
_game_sessions: dict[str, dict] = {}

# 常用词库（适合猜词游戏的常见中文名词）
_WORD_POOL = [
    "中国", "北京", "上海", "广州", "深圳", "杭州", "成都", "西安", "南京", "武汉",
    "长城", "故宫", "黄河", "长江", "泰山", "黄山", "西湖", "太湖", "昆仑", "珠峰",
    "春节", "中秋", "端午", "清明", "元宵", "重阳", "国庆", "元旦", "圣诞", "感恩",
    "太阳", "月亮", "星星", "地球", "火星", "宇宙", "银河", "彗星", "极光", "日食",
    "苹果", "香蕉", "西瓜", "葡萄", "芒果", "荔枝", "榴莲", "樱桃", "草莓", "菠萝",
    "老虎", "狮子", "大象", "熊猫", "企鹅", "海豚", "鲨鱼", "老鹰", "孔雀", "蝴蝶",
    "钢琴", "吉他", "小提琴", "二胡", "笛子", "鼓", "萨克斯", "口琴", "古筝", "琵琶",
    "篮球", "足球", "网球", "乒乓", "游泳", "跑步", "滑雪", "攀岩", "骑行", "射箭",
    "咖啡", "奶茶", "可乐", "果汁", "红酒", "啤酒", "绿茶", "豆浆", "酸奶", "矿泉",
    "飞机", "高铁", "地铁", "公交", "出租", "轮船", "自行车", "摩托", "直升机", "缆车",
    "手机", "电脑", "电视", "冰箱", "空调", "相机", "手表", "耳机", "音箱", "平板",
    "学校", "医院", "银行", "超市", "公园", "博物馆", "图书馆", "体育场", "机场", "车站",
    "春天", "夏天", "秋天", "冬天", "早晨", "中午", "傍晚", "深夜", "黎明", "黄昏",
    "红色", "蓝色", "绿色", "黄色", "紫色", "橙色", "黑色", "白色", "粉色", "灰色",
    "医生", "老师", "警察", "消防", "工程师", "画家", "音乐家", "厨师", "飞行员", "农民",
    "爱情", "友情", "亲情", "梦想", "自由", "勇气", "智慧", "幸福", "希望", "和平",
    "长城", "兵马俑", "敦煌", "颐和园", "天坛", "鸟巢", "东方明珠", "外滩", "洪崖洞", "鼓浪屿",
    "微信", "淘宝", "抖音", "美团", "百度", "京东", "拼多多", "B站", "知乎", "微博",
    "红楼梦", "西游记", "水浒传", "三国演义", "诗经", "论语", "道德经", "史记", "聊斋", "山海经",
]


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


@router.post("/game/start", response_model=GameStartResponse)
async def game_start():
    """开始一局猜词游戏：随机选词，返回 game_id"""
    target = _random.choice(_WORD_POOL)
    game_id = str(_uuid.uuid4())[:8]

    _game_sessions[game_id] = {
        "target": target,
        "history": [],
        "started_at": __import__("time").time(),
    }

    # 提示：首字 + 词长
    hint = f"{len(target)}字词语，首字是「{target[0]}」"

    return GameStartResponse(
        game_id=game_id,
        word_length=len(target),
        hint=hint,
    )


@router.post("/game/guess", response_model=GameGuessResponse)
async def game_guess(data: GameGuessRequest):
    """猜词：调用 LLM 计算语义相关度"""
    session = _game_sessions.get(data.game_id)
    if not session:
        raise HTTPException(404, "游戏不存在或已结束")

    guess = data.guess.strip()
    target = session["target"]

    # 完全猜中
    if guess == target:
        probability = 100
        is_correct = True
        hint = f"恭喜猜中！答案是「{target}」"
    else:
        # 调用 LLM 计算语义相关度
        llm = _get_llm()
        prompt = (
            f"你是语义相关度评估器。计算两个中文词语的语义相关度，返回0-100的整数。\n"
            f"100=完全相同，80-99=高度相关（同义词/包含关系/部分重合），"
            f"60-79=中等相关（同类/直接关联），30-59=弱相关，0-29=几乎无关。\n\n"
            f"词语1：{target}\n词语2：{guess}\n\n只返回一个数字，不要其他内容。"
        )
        try:
            raw = await llm.chat(
                [{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=10,
            )
            # 提取数字
            import re as _re
            nums = _re.findall(r'\d+', raw.strip())
            probability = int(nums[0]) if nums else 0
            probability = max(0, min(100, probability))
        except Exception as e:
            logger.error(f"Game LLM call failed: {e}")
            probability = 0

        is_correct = False

        # 根据概率给提示
        if probability >= 80:
            hint = "非常接近！再想想"
        elif probability >= 60:
            hint = "有关联，继续猜"
        elif probability >= 30:
            hint = "有一点关系"
        else:
            hint = "差得远呢"

    # 记录历史
    session["history"].append({
        "guess": guess,
        "probability": probability,
    })

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
    )


@router.post("/game/giveup")
async def game_giveup(data: GameGuessRequest):
    """放弃游戏，揭晓答案"""
    session = _game_sessions.get(data.game_id)
    if not session:
        raise HTTPException(404, "游戏不存在或已结束")

    target = session["target"]
    del _game_sessions[data.game_id]
    return {"answer": target}
