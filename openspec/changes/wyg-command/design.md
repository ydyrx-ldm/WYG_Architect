## Context

WYG 架构师体系已建立 7 个 Agent（BA/SA/RR/PM/DEV/CR/TE）的完整行为规则和知识库，通过 OpenSpec 的 4 个阶段（explore/propose/apply/archive）串行协作。当前用户可以手动调用 `/opsx:explore`、`/opsx:propose`、`/opsx:apply`、`/opsx:archive`，但缺少一个统一入口来自动编排整个流水线。

WYG 架构师（上帝视角）已有编排打印和阶段路由行为定义，但尚未绑定为一个可执行的指令。`/WYG` 是独立新指令，与现有 opsx 指令并列共存。

## Goals / Non-Goals

**Goals:**
- 创建独立的 `/WYG` 指令，作为 7 个 Agent 的统一入口
- 用户输入 `/WYG {需求描述}` 后，WYG 架构师自动识别意图、打印编排、按阶段推进
- 指令覆盖完整流水线：explore → propose → apply → archive
- 支持回退机制和门禁约束
- `/WYG` 与 `/opsx:*` 指令并列共存，互不影响

**Non-Goals:**
- 不替换或修改现有 `/opsx:explore`、`/opsx:propose`、`/opsx:apply`、`/opsx:archive` 指令
- 不改变现有 7 个 Agent 的行为规则
- 不实现多用户/多会话并发
- 不实现 Agent 间的异步通信（当前为同步串行）
- 不实现自动重试或超时机制

## Decisions

### Decision 1: `/WYG` 作为独立新指令，通过 Rule 增强 WYG 架构师

**选择**：将 `/WYG` 实现为 `.codebuddy/rules/wyg-architect.mdc` 中的行为规则增强，作为独立指令与 opsx 指令并列

**理由**：
- WYG 架构师已有完整的 Rule 文件，只需增强其行为定义
- `/WYG` 是编排层指令，与 `/opsx:*` 阶段指令是不同层级：`/WYG` = 自动编排全流程，`/opsx:*` = 手动进入单阶段
- 两者并列共存，用户可以选择自动（`/WYG`）或手动（`/opsx:*`）
- Rule 文件中的 `alwaysApply: true` 确保每次对话都会加载

**备选方案**：
- A) 创建独立 Skill → 过重，WYG 本质是编排逻辑而非独立能力
- B) 修改 OpenSpec 指令 → 不应修改通用框架
- C) 替换 opsx 指令 → 破坏现有工作流，用户仍需手动单阶段操作的能力

### Decision 2: 意图识别基于关键词匹配

**选择**：基于用户输入的关键词识别应进入的阶段

| 关键词 | 阶段 |
|--------|------|
| "调研""了解""看看" / 模糊描述 | explore |
| "设计""方案""怎么做" | propose |
| "实现""开发""修复""跑一下" | apply |
| "完成了""总结""复盘" | archive |
| 无明确阶段信号 | 默认从 explore 开始 |

**理由**：简单直接，已在跨阶段共性原则中定义，所有 Agent 已有共识

### Decision 3: 编排打印为强制首步

**选择**：每次 `/WYG` 调用必须先打印完整流水线编排表

**理由**：
- 让用户看到 7 个 Agent 如何协作
- 明确当前阶段和参与 Agent
- 提供流水线全貌，降低认知负担

### Decision 4: 阶段串行执行，门禁不可绕过

**选择**：严格按 explore → propose → apply → archive 串行，门禁（RR/CR/TE）不可跳过

**理由**：这是 WYG 体系的核心设计原则，已在所有 Agent 的"阶段身份纪律"中定义

## Risks / Trade-offs

- **[意图误识别]** → 缓解：打印编排后让用户确认当前阶段，用户可手动指定阶段
- **[长流水线耗时]** → 缓解：小型任务/紧急修复可走轻量流程（如直接 apply 修复 bug）
- **[回退循环]** → 缓解：WYG 架构师待补充"终止流水线"规则，当前依赖人工判断
