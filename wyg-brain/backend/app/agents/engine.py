"""WYG Agent Engine - 7 Agent 流水线"""

from typing import AsyncGenerator, Optional
from app.core.llm import get_llm, LLMProviderBase
from app.models.database import Solution, ChatMessage


# ============================================================
# Agent 系统提示词
# ============================================================

BA_SYSTEM = """你是 BA（需求分析师），负责 explore 阶段。

核心职责：
1. 反问澄清：挖掘模糊需求背后的真实意图
2. 具体化：将模糊/相对描述转化为可量化、可验证的需求
3. 红线：理解问题，不做决策，不出方案

你必须遵守：
- 不越界：explore 阶段不出方案
- 不下结论、不选方案、不给推荐
- 只列选项和约束
- 通过连续追问找到根因

【绝对禁止】重复问题！
- 用户消息中会包含"已澄清的维度"，里面列出了：
  1. 已问过的问题（完整文本 + 选项）—— 这些问题的任何变体都禁止再问
  2. 禁止涉及的关键词维度 —— 任何包含这些关键词的问题都不允许
  3. 用户已选答案 —— 代表该维度已完全澄清
- 判断"是否重复"的标准：如果新问题的核心维度与已问问题相同，就是重复
  - 例如：你问了"景点类型"，就不能再问"喜欢山水还是城市"、"想去户外还是室内"、"自然还是人文"——这些都是"景点类型"维度
  - 例如：你问了"预算范围"，就不能再问"花多少钱"、"消费水平"——这些都是"预算"维度
- 每次只问新的、之前从未涉及的问题维度
- 如果需求已经足够清晰（用户已回答了2轮以上问题，且没有新的维度可问），直接输出"需求已澄清"四个字开头，然后附上需求摘要，不要再输出选择题
- 判断是否足够清晰的标准：你已经问了至少2轮问题，且用户的选择已经覆盖了主要维度

【用户回复格式说明】
用户回复选择题时，格式为"问题文本 → 选项文本"，每行一个。
例如：
景点类型 → A) 自然风光
预算范围 → B) 舒适型
你需要从中提取用户的选择，理解用户意图，然后问新的问题。

【重要】输出格式规范：
每次回复必须包含选择题，让用户点击选择即可，无需打字。

格式要求（严格遵守）：
1. 每个问题必须有"问题N："标题行，不能省略
2. 每个问题只给 3 个选项（A/B/C），不要多
3. 每次最多问 2 个问题
4. 问题之间用空行隔开
5. 选项文字要简短（10字以内）
6. 不要输出长篇分析，直接给问题+选项
7. 绝对不要重复之前对话中已经出现的问题
8. 每个问题只聚焦一个维度，不要复合问题
9. 【最重要】同一问题的3个选项必须含义完全不同、互不重叠、互不近似

近义词禁止规则（必须遵守）：
- 输出选项前，先自检：3个选项是否存在近义词/同义词？如果存在，必须替换为含义完全不同的选项
- 判断近义词的方法：如果两个选项描述的是同一类事物、同一方向、同一种体验，就是近义词
- 常见近义词陷阱（举例，不限于此）：
  - "自然风光"和"自然景观" → 同义，只保留一个
  - "历史文化"和"人文古迹" → 同义，只保留一个
  - "休闲放松"和"休闲度假" → 同义，只保留一个
  - "自驾"和"自驾游" → 同义，只保留一个
  - "跟团游"和"团队游" → 同义，只保留一个
  - "自由行"和"自助游" → 同义，只保留一个
  - "海边"和"海滨" → 同义，只保留一个
  - "深度游"和"慢游" → 同义，只保留一个

选项差异化规则（必须遵守）：
- 3个选项必须代表3个截然不同的方向/类别/程度
- 禁止同义词/近义词选项
- 禁止程度递进变体：如"轻松"和"很轻松"、"省钱"和"经济"
- 禁止包含关系：如"户外"和"户外运动"、"美食"和"特色美食"
- 每个选项必须让用户能明确区分"我选A不选B"的理由
- 正确示例：A) 自然风光 B) 历史文化 C) 美食体验（三个完全不同的类别）
- 错误示例：A) 自然风光 B) 自然景观 C) 山水游览（三个几乎一样）
- 错误示例：A) 休闲放松 B) 休闲戏水 C) 休闲购物（都有"休闲"，不够差异化）

输出格式示例：

问题1：你想去什么类型的景点？
A) 自然风光
B) 历史文化
C) 美食体验

问题2：你的预算范围？
A) 经济型
B) 舒适型
C) 豪华型

注意：
- 每个问题必须有"问题N："标题，不能只给选项不给问题
- 选项文字必须简短
- 同一问题的3个选项必须含义完全不同，绝对不能有相同或近似的选项
- 问题之间必须空一行
- 不要在选项后面加长篇解释
- 最后一个选项后面不要再输出其他文字
- 绝对不要重复之前对话中已经出现的问题
- 每个问题只问一个维度，不要复合问题"""

SA_SYSTEM = """你是 SA（架构设计师），负责 propose 阶段。

核心职责：
1. 方案设计：产出多方案 + 推荐，必须下结论、做决策
2. 选型质疑：不能用户说什么就做什么，必须识别选型与场景的错配

你必须遵守：
- 必须产出多个方案并给出推荐
- 每个重要架构决策必须记录 ADR
- 紧急修复必须分层出方案（短期/中期/长期）

输出格式：方案 A/B/C + 推荐 + ADR"""

RR_SYSTEM = """你是 RR（就绪评审员），负责 propose 阶段的准入评审。

核心职责：
1. DoR 守门：确保 SA 的方案满足准入标准后才进入 apply 阶段
2. 硬约束不可妥协：执行快速 + 用户友好，任一不通过即回退

硬约束：
- 执行快速：产出的产品必须响应迅速、执行高效
- 用户友好：产出的产品必须对用户友好、易用

输出格式：DoR 检查清单 + 结论（准入通过/暂不准入）"""

PM_SYSTEM = """你是 PM（项目管理），负责 propose 阶段辅助（拆任务）。

核心职责：
1. 任务拆解：将 SA 的方案拆解为可执行的任务列表
2. 里程碑规划：定义关键节点和交付物

任务粒度：每个任务可在一次会话中完成
依赖排序：按依赖关系排列任务顺序

输出格式：tasks.md（任务组 + 子任务列表）"""

DEV_SYSTEM = """你是 DEV（开发工程师），负责 apply 阶段。

核心职责：
1. 按方案实现：严格遵循 SA 的方案设计和 RR 的准入要求
2. 质量自保：写单元测试覆盖正常路径和异常路径
3. 方案偏离即停：发现方案不可行时，立即停止并请求回 propose

你必须遵守：
- 不擅自修改方案中的关键决策
- 错误处理完备，不吞异常
- 命名规范、目录结构符合团队约定"""

CR_SYSTEM = """你是 CR（代码评审员），负责 apply 阶段的评审门禁。

核心职责：
1. 评审门禁：DEV 所有任务完成后一次性评审
2. 方案偏离检测：对比实现与 propose 阶段的方案
3. 意见分类：必须修改 / 建议修改 / 认可

评审检查：准确性、完整性、规范性、安全性

输出格式：✅认可 / ❌必须修改 / ⚠️建议修改 + 结论"""

TE_SYSTEM = """你是 TE（测试工程师），负责 apply 阶段的端到端验收。

核心职责：
1. 端到端验收：基于 propose 阶段的验收标准
2. 问题识别与回退：判断问题性质（实现/方案/需求），回退到正确的阶段
3. 错误记忆创建：每次回退必须创建错误记忆

测试策略：模拟执行、边界测试、回归测试

输出格式：验收测试报告 + 结论（通过/打回）"""

SUMMARY_SYSTEM = """你是一个面向用户的决策摘要生成器。你的任务是把多个 AI Agent 的技术输出，转化为普通用户能看懂的、简洁友好的决策摘要。

你必须遵守：
1. 用大白话，不用技术术语（不要出现"架构""方案A/B""准入""评审"等词）
2. 结构清晰，一目了然
3. 突出用户最关心的：最终推荐是什么、为什么、要做什么
4. 不要超过 300 字
5. 语气亲切自然，像朋友在给建议

输出格式（严格遵守）：

## 决策摘要

### 我的需求
（一句话概括用户想要什么）

### 推荐方案
（方案名称 + 一句话说清楚，用"建议你..."的语气）

### 为什么推荐
（2-3 个理由，每个一行，用"因为..."开头）

### 接下来要做什么
（2-3 个具体步骤，用"1. 2. 3."编号）"""


# ============================================================
# Agent 类
# ============================================================

class Agent:
    """WYG Agent 基类"""

    def __init__(self, name: str, system_prompt: str, llm: Optional[LLMProviderBase] = None):
        self.name = name
        self.system_prompt = system_prompt
        self.llm = llm or get_llm()

    async def run(self, user_input: str, history: list[dict] | None = None) -> str:
        """执行 Agent，返回输出"""
        messages = [{"role": "system", "content": self.system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_input})
        return await self.llm.chat(messages)

    async def run_stream(self, user_input: str, history: list[dict] | None = None) -> AsyncGenerator[str, None]:
        """流式执行 Agent"""
        messages = [{"role": "system", "content": self.system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_input})
        async for token in self.llm.chat_stream(messages):
            yield token


# ============================================================
# 7 Agent 实例
# ============================================================

def create_agents(llm: Optional[LLMProviderBase] = None) -> dict[str, Agent]:
    """创建 8 个 Agent 实例（7 + SUMMARY）"""
    return {
        "BA": Agent("BA", BA_SYSTEM, llm),
        "SA": Agent("SA", SA_SYSTEM, llm),
        "RR": Agent("RR", RR_SYSTEM, llm),
        "PM": Agent("PM", PM_SYSTEM, llm),
        "DEV": Agent("DEV", DEV_SYSTEM, llm),
        "CR": Agent("CR", CR_SYSTEM, llm),
        "TE": Agent("TE", TE_SYSTEM, llm),
        "SUMMARY": Agent("SUMMARY", SUMMARY_SYSTEM, llm),
    }


# ============================================================
# BA 输出后处理
# ============================================================

import re as _re
import sys as _sys
import os as _os

# 将 mcp-chinese-dict 项目加入 sys.path，以便导入词林加载器
# 路径：engine.py → agents/ → app/ → backend/ → wyg-brain/ → WYG/ → mcp-chinese-dict/
_MCP_DICT_PATH = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))), "mcp-chinese-dict")
if _MCP_DICT_PATH not in _sys.path:
    _sys.path.insert(0, _MCP_DICT_PATH)

try:
    from loaders.cilin_loader import get_loader as _get_cilin_loader
    _CILIN_AVAILABLE = True
except Exception:
    _CILIN_AVAILABLE = False


def _normalize_ba_output(text: str) -> str:
    """修复 BA 输出中的格式问题：
    1. 没有问题标题的选项组 → 补充"问题N："标题
    2. 去重同一问题中含义相同/近似的选项（词林 + 规则匹配）
    """
    lines = text.split('\n')
    result_lines = []
    question_counter = 0
    i = 0

    # 获取词林加载器单例（如果可用）
    _cilin = _get_cilin_loader() if _CILIN_AVAILABLE else None

    def _char_overlap(s1: str, s2: str) -> float:
        """计算两个字符串的字符重叠度（0~1），用于模糊去重"""
        if not s1 or not s2:
            return 0.0
        set1 = set(s1)
        set2 = set(s2)
        intersection = set1 & set2
        denominator = min(len(set1), len(set2))
        return len(intersection) / denominator if denominator > 0 else 0.0

    def _is_similar_option(opt: str, seen_list: list) -> bool:
        """判断选项是否与已有选项语义近似

        优先使用词林 MCP 判断，回退到规则匹配。
        """
        # 去掉语气词和常见修饰词
        filler_words = r'[的了吗呢吧啊呀很非常比较更加最]'
        opt_clean = _re.sub(filler_words, '', opt.strip())

        for seen in seen_list:
            seen_clean = _re.sub(filler_words, '', seen.strip())

            # 优先：词林 MCP 判断
            if _cilin is not None:
                if _cilin.is_similar(opt_clean, seen_clean):
                    return True
                # 词林未命中，继续走规则

            # 1. 精确匹配
            if opt_clean == seen_clean:
                return True
            # 2. 一个包含另一个
            if opt_clean in seen_clean or seen_clean in opt_clean:
                return True
            # 3. 字符重叠度 > 0.5
            if _char_overlap(opt_clean, seen_clean) > 0.5:
                return True
            # 4. 共享前缀检测（>=2 字符）
            prefix_len = 0
            for c1, c2 in zip(opt_clean, seen_clean):
                if c1 == c2:
                    prefix_len += 1
                else:
                    break
            if prefix_len >= 2:
                return True
        return False

    while i < len(lines):
        line = lines[i].strip()

        # 检测已有的问题标题行
        if _re.match(r'^(问题\s*\d+[：:]|Q\d+[：:])', line):
            question_counter += 1
            result_lines.append(lines[i])
            i += 1
            continue

        # 检测连续的选项行（没有问题标题的情况）
        if _re.match(r'^[A-C][)\．.）]\s*.+', line):
            # 收集连续的选项行
            options = []
            while i < len(lines) and _re.match(r'^[A-C][)\．.）]\s*.+', lines[i].strip()):
                opt_match = _re.match(r'^([A-C])[)\．.）]\s*(.+)', lines[i].strip())
                if opt_match:
                    options.append((opt_match.group(1), opt_match.group(2).strip()))
                i += 1

            # 检查前一行是否已经是问题标题
            has_title = False
            if result_lines:
                last_line = result_lines[-1].strip()
                if _re.match(r'^(问题\s*\d+[：:]|Q\d+[：:])', last_line):
                    has_title = True

            if not has_title and options:
                # 没有问题标题，补充一个
                question_counter += 1
                result_lines.append(f'问题{question_counter}：请选择')

            # 去重：精确匹配 + 模糊匹配
            seen_texts = []
            deduped_options = []
            for label, opt_text in options:
                if not _is_similar_option(opt_text, seen_texts):
                    seen_texts.append(opt_text.strip())
                    deduped_options.append((label, opt_text))

            # 去重后选项不足 3 个时，补充通用选项
            while len(deduped_options) < 3:
                fill_labels = ['其他', '都不选', '看情况']
                fill_idx = len(deduped_options)
                if fill_idx < len(fill_labels):
                    deduped_options.append(('X', fill_labels[fill_idx]))
                else:
                    break

            # 重新分配选项标签（A/B/C）
            label_map = {0: 'A', 1: 'B', 2: 'C'}
            for idx, (_, opt_text) in enumerate(deduped_options[:3]):
                new_label = label_map.get(idx, chr(65 + idx))
                result_lines.append(f'{new_label}) {opt_text}')

            continue

        # 非选项行，直接保留
        result_lines.append(lines[i])
        i += 1

    return '\n'.join(result_lines)


# ============================================================
# 流水线编排
# ============================================================

class WYGPipeline:
    """WYG 流水线：explore → propose → apply → archive"""

    def __init__(self, llm: Optional[LLMProviderBase] = None):
        self.agents = create_agents(llm)

    async def explore(self, requirement: str, chat_history: list[dict] | None = None) -> str:
        """explore 阶段：BA 反问澄清"""
        raw_output = await self.agents["BA"].run(requirement, chat_history)
        return _normalize_ba_output(raw_output)

    async def propose(self, explore_output: str) -> dict:
        """propose 阶段：SA 方案设计 + PM 任务拆解 + RR 准入评审 + 决策摘要"""
        # SA 设计方案
        sa_output = await self.agents["SA"].run(
            f"基于以下需求探索纪要，设计方案：\n\n{explore_output}"
        )

        # PM 拆解任务
        pm_output = await self.agents["PM"].run(
            f"基于以下方案设计，拆解为可执行的任务列表：\n\n{sa_output}"
        )

        # RR 准入评审
        rr_output = await self.agents["RR"].run(
            f"评审以下方案是否满足准入标准：\n\n方案设计：{sa_output}\n\n任务列表：{pm_output}"
        )

        # 生成用户友好的决策摘要
        summary_output = await self.agents["SUMMARY"].run(
            f"请根据以下信息，生成用户友好的决策摘要：\n\n"
            f"【需求探索】{explore_output}\n\n"
            f"【方案设计】{sa_output}\n\n"
            f"【任务列表】{pm_output}\n\n"
            f"【准入评审】{rr_output}"
        )

        return {
            "sa_output": sa_output,
            "pm_output": pm_output,
            "rr_output": rr_output,
            "summary_output": summary_output,
        }

    async def apply(self, propose_output: dict) -> dict:
        """apply 阶段：DEV 实现 + CR 评审 + TE 验收"""
        # DEV 实现
        dev_output = await self.agents["DEV"].run(
            f"基于以下方案和任务列表，实现代码：\n\n方案：{propose_output['sa_output']}\n\n任务：{propose_output['pm_output']}"
        )

        # CR 评审
        cr_output = await self.agents["CR"].run(
            f"评审以下实现：\n\n方案：{propose_output['sa_output']}\n\n实现：{dev_output}"
        )

        # TE 验收
        te_output = await self.agents["TE"].run(
            f"验收以下实现：\n\n方案：{propose_output['sa_output']}\n\n实现：{dev_output}\n\n评审：{cr_output}"
        )

        return {
            "dev_output": dev_output,
            "cr_output": cr_output,
            "te_output": te_output,
        }

    async def full_pipeline(self, requirement: str) -> dict:
        """完整流水线：explore → propose → apply"""
        # explore
        explore_output = await self.explore(requirement)

        # propose
        propose_output = await self.propose(explore_output)

        # apply
        apply_output = await self.apply(propose_output)

        return {
            "explore": explore_output,
            "propose": propose_output,
            "apply": apply_output,
        }
