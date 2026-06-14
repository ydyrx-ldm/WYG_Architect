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

输出格式：需求探索纪要（澄清问题清单、已知约束、未知项）"""

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
    """创建 7 个 Agent 实例"""
    return {
        "BA": Agent("BA", BA_SYSTEM, llm),
        "SA": Agent("SA", SA_SYSTEM, llm),
        "RR": Agent("RR", RR_SYSTEM, llm),
        "PM": Agent("PM", PM_SYSTEM, llm),
        "DEV": Agent("DEV", DEV_SYSTEM, llm),
        "CR": Agent("CR", CR_SYSTEM, llm),
        "TE": Agent("TE", TE_SYSTEM, llm),
    }


# ============================================================
# 流水线编排
# ============================================================

class WYGPipeline:
    """WYG 流水线：explore → propose → apply → archive"""

    def __init__(self, llm: Optional[LLMProviderBase] = None):
        self.agents = create_agents(llm)

    async def explore(self, requirement: str, chat_history: list[dict] | None = None) -> str:
        """explore 阶段：BA 反问澄清"""
        return await self.agents["BA"].run(requirement, chat_history)

    async def propose(self, explore_output: str) -> dict:
        """propose 阶段：SA 方案设计 + PM 任务拆解 + RR 准入评审"""
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

        return {
            "sa_output": sa_output,
            "pm_output": pm_output,
            "rr_output": rr_output,
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
