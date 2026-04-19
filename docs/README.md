# 文档导航

本目录的目标不是“留几份说明”，而是让任何接手者在不询问前人的情况下，快速建立当前项目的完整心智模型。

## 推荐阅读顺序

1. PROJECT_PLAYBOOK.md
2. REQUIREMENTS.md
3. PROJECT_STATUS.md
4. TODO.md
5. VALIDATION.md
6. HANDOFF.md
7. ARCHITECTURE.md
8. IMPLEMENTATION_LOGIC.md
9. ENTRYPOINTS.md
10. RULES.md
11. DECISIONS.md
12. ROADMAP.md
13. CHANGELOG.md

## 各文档职责

- PROJECT_PLAYBOOK.md：文档治理与交接规则
- REQUIREMENTS.md：当前阶段需求、边界、验收标准
- PROJECT_STATUS.md：当前事实、阻塞、已知问题、验证现状
- TODO.md：优先级明确的后续事项
- VALIDATION.md：当前可执行的验证方式、命令和结果解释
- HANDOFF.md：给下一位接手者的快速接管说明
- ARCHITECTURE.md：模块边界、系统结构、依赖关系
- IMPLEMENTATION_LOGIC.md：当前真实工作流、GUI 行为、运行逻辑、配置机制
- ENTRYPOINTS.md：所有入口、配置文件、导出文件、脚本位置
- RULES.md：KPI 判定逻辑、阈值来源和规则治理要求
- DECISIONS.md：关键设计决策与废弃决策
- ROADMAP.md：阶段演进路线
- CHANGELOG.md：重要变更记录
- 需求说明书.txt：中文自然语言总览版需求摘要，给非开发读者快速浏览

## 维护原则

- 如果代码和文档冲突，以代码当前行为为事实基础，但必须在当前变更中把文档修正到一致。
- 不允许把“当前功能逻辑实现”只留在聊天记录里。
- 如果新增入口、配置文件、工作流或约束，至少要同步更新 README、ENTRYPOINTS、PROJECT_STATUS、HANDOFF。
