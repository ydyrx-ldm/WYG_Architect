## Why

当前 WYG 架构师的 7 个 Agent（BA/SA/RR/PM/DEV/CR/TE）已定义完整的行为规则和知识库，OpenSpec 提供了 4 个阶段指令（`/opsx:explore`、`/opsx:propose`、`/opsx:apply`、`/opsx:archive`），但用户缺少一个统一入口指令来自动编排整个流水线。用户需要手动识别应该进入哪个阶段、手动按顺序调用每个指令。需要一个独立的 `/WYG` 指令作为统一入口，自动识别用户意图、编排 7 个 Agent、按阶段推进完整流水线。`/WYG` 与现有 opsx 指令并列共存，不替换任何一个。

## What Changes

- 新增 `/WYG` 指令：独立于现有 opsx 指令，作为 7 个 Agent 的统一入口，用户只需输入 `/WYG {需求描述}` 即可启动整个流水线
- `/WYG` 不替换 `/opsx:explore`、`/opsx:propose`、`/opsx:apply`、`/opsx:archive`，它们继续独立可用
- WYG 架构师自动识别用户意图，路由到正确的 opsx 阶段（explore/propose/apply/archive）
- 每次调用先打印完整流水线编排表，让用户看到 7 个 Agent 如何协作
- 按阶段串行执行，门禁不可绕过（RR→CR→TE）
- 支持回退机制：任何阶段发现问题可回退到上游阶段

## Capabilities

### New Capabilities

- `wyg-command`: `/WYG` 统一入口指令，自动识别意图、编排 7 Agent、按阶段推进流水线

### Modified Capabilities

- `wyg-god-view`: WYG 架构师行为从"被动分发"升级为"主动编排"，新增编排打印和阶段路由职责
- `agent-pipeline`: 流水线新增统一入口触发机制，支持从 `/WYG` 指令启动

## Impact

- `.codebuddy/rules/wyg-architect.mdc`：WYG 架构师 Rule 需要新增 `/WYG` 指令处理逻辑
- `wyg-space/wyg-architect.md`：知识库需要新增 `/WYG` 指令文档
- 现有 7 个 Agent 的 Rule 无需修改（它们的行为规范已完备）
- 现有 opsx 指令（`/opsx:explore`、`/opsx:propose`、`/opsx:apply`、`/opsx:archive`）不受影响，继续独立可用
