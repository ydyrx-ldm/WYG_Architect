## ADDED Requirements

### Requirement: WYG unified command entry
The system SHALL provide a `/WYG` command as a new independent command that coexists with existing opsx commands (`/opsx:explore`, `/opsx:propose`, `/opsx:apply`, `/opsx:archive`). The `/WYG` command SHALL NOT replace any existing opsx command. When a user inputs `/WYG {requirement description}`, the WYG Architect SHALL automatically identify the user's intent, route to the correct opsx phase, and orchestrate the 7 Agents through the full pipeline. Users can still use `/opsx:*` commands individually for manual single-phase operations.

#### Scenario: User submits requirement via /WYG
- **WHEN** user inputs `/WYG 帮我设计一个埋点系统`
- **THEN** WYG Architect SHALL identify intent as "propose", print the pipeline orchestration table, and route to the propose phase (SA★ + PM + RR)

#### Scenario: User submits vague requirement via /WYG
- **WHEN** user inputs `/WYG 系统太慢了`
- **THEN** WYG Architect SHALL identify intent as "explore", print the pipeline orchestration table, and route to the explore phase (BA★ + SA)

#### Scenario: User submits bug fix via /WYG
- **WHEN** user inputs `/WYG 修复支付回调漏单问题`
- **THEN** WYG Architect SHALL identify intent as "apply", print the pipeline orchestration table, and route to the apply phase (DEV★ + CR + TE)

#### Scenario: User submits completion summary via /WYG
- **WHEN** user inputs `/WYG 项目上线完成了`
- **THEN** WYG Architect SHALL identify intent as "archive", print the pipeline orchestration table, and route to the archive phase (PM★)

#### Scenario: /WYG coexists with opsx commands
- **WHEN** user uses `/opsx:explore` or any other opsx command
- **THEN** the opsx command SHALL work as before, `/WYG` does not interfere with or replace it

### Requirement: Pipeline orchestration printing
The WYG Architect SHALL print a complete pipeline orchestration table before executing any phase. The table MUST show all 4 phases, the leading Agent (★), supporting Agents, gates, and deliverables for each phase. The table MUST also indicate the current phase and participating Agents.

#### Scenario: Orchestration table printed on /WYG invocation
- **WHEN** user inputs `/WYG {any requirement}`
- **THEN** WYG Architect SHALL print a table with columns: Phase | ★ Lead | Support | Gate | Deliverable, showing all 4 phases, and indicate the current phase and participating Agents

### Requirement: Intent-based phase routing
The WYG Architect SHALL route user requirements to the correct opsx phase based on keyword matching in the user input. The routing rules SHALL be: vague/"调研""了解""看看" → explore; "设计""方案""怎么做" → propose; "实现""开发""修复""跑一下" → apply; "完成了""总结""复盘" → archive. If no clear phase signal is detected, the default SHALL be explore.

#### Scenario: Default to explore when no clear signal
- **WHEN** user inputs `/WYG 用户行为分析`
- **THEN** WYG Architect SHALL route to explore phase as the default

#### Scenario: Wrong command correction
- **WHEN** user inputs `/WYG` with intent clearly matching a different phase than expected
- **THEN** WYG Architect SHALL suggest the correct phase and ask for confirmation

### Requirement: Serial execution with gates
The `/WYG` command SHALL execute phases in strict serial order: explore → propose → apply → archive. Gates (RR, CR, TE) SHALL NOT be bypassed. If a gate fails, the pipeline SHALL roll back to the appropriate upstream Agent.

#### Scenario: Gate enforcement
- **WHEN** RR does not approve a proposal during propose phase
- **THEN** the pipeline SHALL NOT proceed to apply phase, and SHALL roll back to SA

#### Scenario: Full pipeline execution
- **WHEN** all gates pass at each phase
- **THEN** the pipeline SHALL proceed through explore → propose → apply → archive in order
