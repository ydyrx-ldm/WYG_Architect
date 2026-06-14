## Why

当前 AI Agent 项目（如 ai-log-analyze）采用单 Agent 多技能模式，无法覆盖软件工程全生命周期。需要一个多 Agent 协作体系，让一个"架构师"同时具备项目管理、需求分析、架构设计、就绪评审、开发实现、代码评审、测试验证七种能力，严格串行执行，测试失败则回退重做，并从错误中学习。

## What Changes

- 新增 7 个独立 Agent（PM/BA/SA/RR/DEV/CR/TE），严格串行流水线执行，TE 测试失败时回退到指定阶段重做
- 新增 WYG 架构师上帝视角层，负责接收用户需求、分发给 PM、汇总 7 路 Agent 输出返回用户
- 新增 7 套 Rule（.codebuddy/rules/），每个 Agent 各自的行为约束
- 新增 7 份 Memory（wyg-space/memory/），每个 Agent 各自的上下文记忆 + 共享错误记忆
- 新增 7 域知识库（wyg-space/knowledge/），每个 Agent 各自的领域知识 + references
- 新增知识地图（wyg-space/knowledge-map/），AI 自动推断关联的拓扑网络，最细粒度存储（每条关联一个 YAML 文件）
- 新增文件地图（wyg-space/file-map/），项目文件到 Agent 的映射
- 新增 PM 主导的 GitHub 同步机制，硬约束：每个本地更新必须同步到 GitHub
- 新增错误记忆机制，回退时记录错误原因和教训，下次执行时避免重复错误
- RR 准入标准：执行快速 + 用户友好（硬约束），性能/稳定性/功耗（占位后续补充）

## Capabilities

### New Capabilities

- `agent-pipeline`: 7 Agent 严格串行流水线（PM→BA→SA→RR→DEV→CR→TE），含回退机制和错误记忆
- `agent-rules`: 7 套 Agent Rule 系统，定义每个 Agent 的行为约束和输出规范
- `agent-memory`: 7 份 Agent 上下文记忆 + 错误记忆（从失败中学习）
- `knowledge-base`: 7 域知识库（PM/BA/SA/RR/DEV/CR/TE），每个含主文档 + references
- `knowledge-map`: AI 推断关联的拓扑知识地图，最细粒度关联文件 + 自动索引
- `file-map`: 项目文件到 Agent 的映射导航
- `github-sync`: PM 主导的 GitHub 同步机制，硬约束每个更新必须同步
- `wyg-god-view`: WYG 架构师上帝视角，需求分发与输出汇总（rule 占位后续补充）

### Modified Capabilities

## Impact

- 新增 wyg-space/ 目录结构（knowledge/、knowledge-map/、file-map/、memory/）
- 新增 .codebuddy/rules/ 下 7 个 .mdc 规则文件
- 需要关联引擎实现（AI 推断关联 + index.yaml 自动生成）
- 需要 PM 的 GitHub 同步策略实现
- 参考 ai-log-analyze 的 SKILL.md + references 模式组织知识库
