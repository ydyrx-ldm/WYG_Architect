---
name: wyg
description: "Orchestrate 7 Agents (BA/SA/RR/PM/DEV/CR/TE) through 4 opsx phases to fulfill a requirement. This skill should be used when the user inputs /WYG or wants automatic full-pipeline orchestration of all agents."
license: MIT
compatibility: Works with WYG multi-agent workflow system
metadata:
  author: WYG
  version: "1.0"
---

Orchestrate the full WYG pipeline to fulfill a requirement. 7 Agents collaborate through 4 opsx phases in strict serial order with mandatory gates.

**`/WYG` is an independent command that coexists with `/opsx:*` commands.**

---

## Pipeline Orchestration

Every `/WYG` invocation MUST first print the complete pipeline orchestration table:

```
## 🎯 WYG 流水线编排

**需求**：{user's original requirement in one sentence}

| 阶段 | ★ 主导 | 辅助 | 门禁 | 产出 |
|------|--------|------|------|------|
| explore | BA（反问澄清） | SA（技术可行性） | — | 需求探索纪要 |
| propose | SA（方案设计） | PM（拆任务）+ RR（准入评审） | RR | 方案+任务列表 |
| apply | DEV（按方案实现） | — | CR→TE | 代码+测试报告 |
| archive | PM（归档复盘） | — | — | 归档报告 |

**当前阶段**：{identified phase}
**参与 Agent**：{list of participating Agents for this phase}
```

## Intent Identification & Phase Routing

| User Input Signals | Route To | Default Behavior |
|---|---|---|
| Vague / "调研""了解""看看" | explore | — |
| "设计""方案""怎么做" | propose | Must complete explore first |
| "实现""开发""修复""跑一下" | apply | Must complete propose first |
| "完成了""总结""复盘" | archive | Must complete apply first |
| No clear phase signal | **explore** (default) | Start from beginning |

## Phase Execution Rules

### explore Phase (BA★ + SA辅助)
- BA: Ask clarifying questions, dig into real needs, produce 《需求探索纪要》
- SA: Assess technical feasibility, list options and constraints (NO conclusions, NO recommendations)
- Output: 需求探索纪要

### propose Phase (SA★ + PM辅助 + RR门禁)
- SA: Design solution with multiple options + recommendation, produce ADR
- PM: Break down tasks from SA's design into tasks.md
- RR: DoR review — hard constraints (执行快速 + 用户友好) must pass
- If RR fails → roll back to SA, cannot proceed to apply
- Output: proposal.md + design.md + specs/ + tasks.md

### apply Phase (DEV★ + CR门禁 + TE验收)
- DEV: Implement per SA's design and PM's tasks, write tests
- CR: Code review gate — all must-pass items resolved before TE
- TE: End-to-end acceptance testing based on propose phase acceptance criteria
- If CR fails → roll back to DEV
- If TE fails → roll back to DEV (implementation issue) or SA (design issue) or BA (requirement issue)
- Output: Code + test report

### archive Phase (PM★)
- PM: Archive change, sync delta specs to main specs, push to GitHub
- Output: 归档报告

## Gate Enforcement

- **RR** (propose gate): Hard constraints must pass. If not → roll back to SA
- **CR** (apply gate): All must-fix items resolved. If not → roll back to DEV
- **TE** (apply gate): All acceptance criteria met. If not → roll back with error memory
- **Gates are NEVER bypassed**

## Rollback & Error Memory

On any rollback, create an error memory:
```yaml
who: {agent who detected the issue}
stage: "{from}→{to}"
rollback_to: "{target_agent}"
error: "{problem description}"
reason: "{root cause analysis}"
lesson: "{lesson learned}"
```

## Phase Output Summary Format

```
## {Phase Name} 输出

### {Agent Name}（{Role}）
{Agent output content}

---
汇总：{brief summary}
```

## `/WYG` vs `/opsx:*`

| Command | Type | Purpose |
|---------|------|---------|
| `/WYG {requirement}` | Auto full-pipeline | 7 Agents, 4 phases, serial execution |
| `/opsx:explore` | Manual single-phase | Only explore |
| `/opsx:propose` | Manual single-phase | Only propose |
| `/opsx:apply` | Manual single-phase | Only apply |
| `/opsx:archive` | Manual single-phase | Only archive |

They coexist. `/WYG` does NOT replace any `/opsx:*` command.

## Key Principles

1. **Stage discipline**: Explore no solutions, propose no code, apply no design changes
2. **Strong linkage**: Each phase's output is based on the previous phase's deliverables
3. **Questionable**: Any agent can raise concerns about upstream output
4. **Gates mandatory**: RR → CR → TE, none can be bypassed
5. **DEV deviation = stop**: If DEV finds design infeasible, stop and roll back to propose, never self-replace architecture decisions
