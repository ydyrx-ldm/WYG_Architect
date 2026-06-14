## 1. WYG 架构师 Rule 更新

- [x] 1.1 在 `.codebuddy/rules/wyg-architect.mdc` 中新增 `/WYG` 指令处理逻辑：当用户输入以 `/WYG` 开头时，触发编排打印 + 意图识别 + 阶段路由；`/WYG` 是独立新指令，与 `/opsx:*` 并列共存，不替换任何一个
- [x] 1.2 在编排打印模板中增加 `/WYG` 指令的触发说明，明确用户输入格式为 `/WYG {需求描述}`
- [x] 1.3 在意图识别中增加默认路由规则：无明确阶段信号时默认从 explore 开始
- [x] 1.4 在输入识别示例中增加 `/WYG` 相关的正例和反例，明确 `/WYG` 与 `/opsx:*` 的区别

## 2. WYG 架构师知识库更新

- [x] 2.1 在 `wyg-space/wyg-architect.md` 中新增 `/WYG` 指令文档：指令格式、意图识别规则、编排打印流程，明确与 `/opsx:*` 的关系
- [x] 2.2 在 `wyg-space/wyg-architect.md` 中新增阶段路由表，明确每个阶段触发的 Agent 编队

## 3. Specs 同步

- [x] 3.1 将 `openspec/changes/wyg-command/specs/wyg-command/spec.md` 的内容同步到 `openspec/specs/wyg-command/spec.md`（新建）
- [x] 3.2 将 `openspec/changes/wyg-command/specs/wyg-god-view/spec.md` 的 delta 合并到 `openspec/specs/wyg-god-view/spec.md`
- [x] 3.3 将 `openspec/changes/wyg-command/specs/agent-pipeline/spec.md` 的 delta 合并到 `openspec/specs/agent-pipeline/spec.md`

## 4. 验证

- [x] 4.1 验证 `/WYG` 指令在 WYG 架构师 Rule 中正确定义为独立新指令
- [x] 4.2 验证 `/WYG` 与 `/opsx:*` 指令并列共存，互不影响
- [x] 4.3 验证编排打印模板包含完整流水线信息
- [x] 4.4 验证意图识别规则覆盖所有 4 个阶段 + 默认路由
- [x] 4.5 验证知识库文档与 Rule 一致
