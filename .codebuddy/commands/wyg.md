---
name: WYG
description: "Orchestrate 7 Agents (BA/SA/RR/PM/DEV/CR/TE) through 4 opsx phases (explore→propose→apply→archive) to fulfill a requirement. Auto full-pipeline mode."
argument-hint: "{requirement description}"
---

Orchestrate the full WYG pipeline to fulfill a requirement. This is the automatic full-pipeline mode — 7 Agents collaborate through 4 opsx phases in strict serial order.

**`/WYG` is an independent command that coexists with `/opsx:*` commands, not replacing any of them.**

- **`/WYG {requirement}`** = Auto full-pipeline: 7 Agents collaborate, 4 opsx phases in serial
- **`/opsx:*`** = Manual single-phase: user picks a specific phase

**Input**: The argument after `/WYG` is the requirement description. Could be:
- A vague idea: "系统太慢了"
- A design request: "帮我设计一个埋点系统"
- A bug fix: "修复支付回调漏单问题"
- A completion summary: "项目上线完成了"
- Nothing (enter WYG orchestration mode)

---

## Execution Flow

```
User inputs /WYG {requirement}
  → 1. Print pipeline orchestration table
  → 2. Identify intent, determine starting phase
  → 3. Execute phases in serial (explore → propose → apply → archive)
  → 4. Summarize output after each phase
  → 5. Roll back if gate fails, proceed if gate passes
  → 6. Output final summary when all phases complete
```

## Step 1: Print Pipeline Orchestration (MUST do first)

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

## Step 2: Intent Identification & Phase Routing

Identify the user's intent based on keyword matching and route to the correct starting phase:

| User Input Signals | Route To | Default Behavior |
|---|---|---|
| Vague / "调研""了解""看看" | explore | — |
| "设计""方案""怎么做" | propose | Must complete explore first |
| "实现""开发""修复""跑一下" | apply | Must complete propose first |
| "完成了""总结""复盘" | archive | Must complete apply first |
| No clear phase signal | **explore** (default) | Start from beginning |

**Important**: Gates cannot be bypassed. If the user's intent maps to a later phase but earlier phases haven't been completed, start from the earliest incomplete phase.

## Step 3: Phase Execution

Execute each phase in strict serial order. Within each phase, activate the corresponding Agents per the orchestration table.

### explore Phase
- **★ BA**: Ask clarifying questions, dig into real needs, produce 《需求探索纪要》
- **SA (support)**: Assess technical feasibility, list options and constraints (no conclusions)
- **Gate**: None (explore always completes)
- **Output**: 需求探索纪要

### propose Phase
- **★ SA**: Design solution, make architectural decisions, produce proposal + design + specs
- **PM (support)**: Break down tasks from SA's design
- **RR (gate)**: DoR review — must pass before proceeding to apply
- **Output**: 方案+任务列表

### apply Phase
- **★ DEV**: Implement per SA's design and PM's tasks
- **CR (gate)**: Code review — all items must pass before TE
- **TE (gate)**: End-to-end acceptance testing
- **Output**: 代码+测试报告

### archive Phase
- **★ PM**: Archive change, sync specs, push to GitHub
- **Output**: 归档报告

## Step 4: Phase Output Summary

After each phase completes, summarize the output:

```
## {Phase Name} 输出

### {Agent Name}（{Role}）
{Agent output content}

### {Agent Name}（{Role}）
{Agent output content}

---
汇总：{brief summary}
```

## Step 5: Gate Enforcement

- **RR fails** → Roll back to SA (propose phase), cannot proceed to apply
- **CR fails** → Roll back to DEV (apply phase), cannot proceed to TE
- **TE fails** → Roll back to DEV or SA depending on root cause, create error memory
- **Gate bypass is NEVER allowed**

## Step 6: Final Summary

When all phases complete:

```
## ✅ WYG 流水线完成

**需求**：{original requirement}

### 阶段执行摘要
1. **explore** → {summary}
2. **propose** → {summary}
3. **apply** → {summary}
4. **archive** → {summary}

### 关键决策
- ...

### 交付物
- ...
```

---

## `/WYG` vs `/opsx:*`

| Command | Type | Purpose |
|---------|------|---------|
| `/WYG {requirement}` | Auto full-pipeline | One-click start, 7 Agents collaborate, 4 phases in serial |
| `/opsx:explore` | Manual single-phase | Only execute explore phase |
| `/opsx:propose` | Manual single-phase | Only execute propose phase |
| `/opsx:apply` | Manual single-phase | Only execute apply phase |
| `/opsx:archive` | Manual single-phase | Only execute archive phase |

**Relationship**: `/WYG` = automatic (full pipeline), `/opsx:*` = manual (single phase). They coexist and do not replace each other.

---

## Guardrails

- **Never skip phases** — explore → propose → apply → archive must be serial
- **Never bypass gates** — RR, CR, TE gates are mandatory
- **Never let DEV change architecture** — if DEV finds the design infeasible, roll back to propose
- **Always print orchestration table first** — user must see the full pipeline
- **Always identify intent** — route to correct phase before starting
- **Always summarize after each phase** — user sees progress
- **Always create error memory on rollback** — lessons must be captured
