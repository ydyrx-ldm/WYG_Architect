# 错误记忆目录

存储流水线回退时产生的错误记忆。每个错误记忆文件包含：

- `who`: 发现错误的 Agent
- `stage`: 错误在哪个阶段暴露
- `rollback_to`: 回退到哪个 Agent
- `error`: 问题描述
- `reason`: 错误原因
- `lesson`: 教训总结
- `timestamp`: 时间戳

## 命名规则

`{AGENT}-{YYYY-MM-DD}-{sequence}.yaml`

例如: `TE-2026-06-14-001.yaml`

## 用途

错误记忆是 WYG 架构师从失败中学习的机制。当 Agent 被回退时，它会读取相关的错误记忆，避免重复同样的错误。
