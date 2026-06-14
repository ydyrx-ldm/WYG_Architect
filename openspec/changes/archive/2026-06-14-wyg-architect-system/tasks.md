## 1. 目录结构初始化

- [x] 1.1 创建 wyg-space/ 根目录及子目录: knowledge/, knowledge-map/, file-map/, memory/
- [x] 1.2 创建 knowledge-map/nodes/ 和 knowledge-map/relations/ 子目录
- [x] 1.3 创建 memory/errors/ 子目录
- [x] 1.4 创建 7 域知识库目录: knowledge/{pm,ba,sa,rr,dev,cr,te}/ 及各域 references/ 子目录
- [x] 1.5 创建 .codebuddy/rules/ 目录

## 2. Agent Rule 文件

- [x] 2.1 创建 PM rule (.codebuddy/rules/pm.mdc): 任务拆解方法论、进度管理、风险识别、GitHub同步硬约束
- [x] 2.2 创建 BA rule (.codebuddy/rules/ba.mdc): 需求分析方法论、验收标准定义、优先级排序
- [x] 2.3 创建 SA rule (.codebuddy/rules/sa.mdc): 架构决策记录(ADR)、技术选型框架、接口设计规范、备选方案
- [x] 2.4 创建 RR rule (.codebuddy/rules/rr.mdc): 准入检查清单(执行快速+用户友好硬约束, 性能/稳定/功耗占位)、通过/不通过判定
- [x] 2.5 创建 DEV rule (.codebuddy/rules/dev.mdc): 编码/内容规范、模块组织原则、规格遵从
- [x] 2.6 创建 CR rule (.codebuddy/rules/cr.mdc): 评审检查清单、意见分类(必须修改/建议/认可)、准确性验证
- [x] 2.7 创建 TE rule (.codebuddy/rules/te.mdc): 测试策略、模拟执行方法、问题识别、回退目标推荐

## 3. Agent Memory 初始化

- [x] 3.1 创建 7 个 Agent 记忆文件: memory/{pm,ba,sa,rr,dev,cr,te}-memory.yaml (初始为空结构)
- [x] 3.2 创建 memory/errors/ 目录的 README 说明文件

## 4. 知识库内容

- [x] 4.1 创建 PM 知识库: knowledge/pm/project-management.md + references/{cases,patterns,signals}.md
- [x] 4.2 创建 BA 知识库: knowledge/ba/requirements-analysis.md + references/{cases,patterns,signals}.md
- [x] 4.3 创建 SA 知识库: knowledge/sa/architecture-design.md + references/{cases,patterns,signals}.md
- [x] 4.4 创建 RR 知识库: knowledge/rr/readiness-criteria.md + references/{cases,patterns,signals}.md
- [x] 4.5 创建 DEV 知识库: knowledge/dev/coding-standards.md + references/{cases,patterns,signals}.md
- [x] 4.6 创建 CR 知识库: knowledge/cr/review-checklist.md + references/{cases,patterns,signals}.md
- [x] 4.7 创建 TE 知识库: knowledge/te/testing-strategy.md + references/{cases,patterns,signals}.md

## 5. 知识地图基础设施

- [x] 5.1 创建 knowledge-map/index.yaml 初始索引文件 (空结构)
- [x] 5.2 定义知识节点 YAML schema: id, type, description, created_at, updated_at
- [x] 5.3 定义关联关系 YAML schema: from(id+type), to(id+type), relation, confidence, source, created_at, context
- [x] 5.4 定义关联类型枚举: part_of, depends_on, affects, refines, contradicts, exemplifies, generalizes, conflicts_with, requires, sequence

## 6. 文件地图

- [x] 6.1 创建 file-map/index.yaml 初始文件 (空结构，待项目文件创建后自动填充)

## 7. WYG 架构师上帝视角

- [x] 7.1 定义 WYG 架构师请求分发行为: 接收用户需求 → 原样分发给 PM
- [x] 7.2 定义 WYG 架构师输出汇总行为: 收集7路Agent输出 → 标注角色名 → 返回用户
- [x] 7.3 创建 WYG 架构师 rule 占位文件 (标注 TBD)

## 8. GitHub 同步

- [x] 8.1 初始化 WYG 项目的 Git 仓库 (如尚未初始化)
- [x] 8.2 配置 GitHub 远程仓库 (需要用户提供 GitHub 仓库地址)
- [x] 8.3 在 PM rule 中写入 GitHub 同步硬约束: 每个本地更新必须同步
- [x] 8.4 首次全量同步: 将所有已创建文件 push 到 GitHub (依赖 8.2)
