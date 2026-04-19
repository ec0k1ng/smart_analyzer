# TCS Smart Analyzer 项目治理手册

## 1. 目标

本手册用于保证项目在长期维护、多人接手、跨会话协作的情况下仍能保持连续性。标准不是“尽量少丢信息”，而是“任何接手者进入仓库后，按照文档顺序就能理解目标、边界、架构、实现、现状、风险和下一步”。

## 2. 文档层级

项目文档分为六层，缺一不可：

1. 入口层
   README.md
2. 治理层
   docs/PROJECT_PLAYBOOK.md
3. 需求层
   docs/REQUIREMENTS.md
4. 事实层
   docs/PROJECT_STATUS.md、docs/TODO.md、docs/VALIDATION.md
5. 设计层
   docs/ARCHITECTURE.md、docs/IMPLEMENTATION_LOGIC.md、docs/ENTRYPOINTS.md、docs/RULES.md、docs/DECISIONS.md、docs/ROADMAP.md
6. 交接层
   docs/HANDOFF.md、docs/templates/

## 3. 强制规则

1. 任何功能开发完成后，必须同步更新 docs/PROJECT_STATUS.md。
2. 任何当前阶段需求、验收标准、输出格式、用户工作流发生变化，必须同步更新 docs/REQUIREMENTS.md。
3. 任何待办优先级变化、遗留问题变化，必须同步更新 docs/TODO.md。
4. 任何验证命令、测试结果、人工检查口径变化，必须同步更新 docs/VALIDATION.md。
5. 任何入口文件、配置目录、导出产物、外部依赖路径变化，必须同步更新 docs/ENTRYPOINTS.md。
6. 任何真实工作流、GUI 行为、配置机制、运行链路发生变化，必须同步更新 docs/IMPLEMENTATION_LOGIC.md。
7. 任何架构调整、模块职责变化、依赖策略变化，必须更新 docs/ARCHITECTURE.md。
8. 任何规则新增、规则删除、阈值变更、规则适用范围调整，必须更新 docs/RULES.md。
9. 任何关键设计取舍，必须在 docs/DECISIONS.md 中新增一条决策记录。
10. 任何阶段性完成项，必须在 docs/CHANGELOG.md 中追加记录。
11. 任何准备结束一次开发会话时，必须检查 docs/HANDOFF.md 是否需要更新。
12. 任何代码改动都必须至少同步检查 docs/REQUIREMENTS.md、docs/PROJECT_STATUS.md、docs/TODO.md、docs/VALIDATION.md、docs/CHANGELOG.md、docs/HANDOFF.md。
13. 不允许把需求、限制、阻塞、验证结果只留在聊天记录里而不落盘。
14. 如果代码与文档不一致，以代码当前行为为事实基础，但必须在本次开发结束前修正文档。
15. 任何新增的配置文件、模板文件、Excel 辅助文件或用户操作入口，都必须写入 docs/HANDOFF.md 和 docs/ENTRYPOINTS.md。
16. 用户提出的开发需求，默认按“一次性闭环完成”执行，除非用户明确要求只做讨论或存在真实阻塞。
17. 未完成状态下不应中途停在“已分析但未落地”的阶段；必须尽可能继续做到实现、验证、文档同步和交接说明更新。
18. 每次完成变更后，结尾必须概述本次所有主要改动，并明确列出本次同步更新了哪些交接类文档。
19. 每次完成变更后，必须清理所有与软件功能无关的临时产物，包括测试报告、缓存文件、__pycache__、.pyc 等。

## 4. 接手顺序

任何新接手人员进入项目后，必须按以下顺序阅读：

1. README.md
2. docs/PROJECT_PLAYBOOK.md
3. docs/REQUIREMENTS.md
4. docs/PROJECT_STATUS.md
5. docs/TODO.md
6. docs/VALIDATION.md
7. docs/HANDOFF.md
8. docs/ARCHITECTURE.md
9. docs/IMPLEMENTATION_LOGIC.md
10. docs/ENTRYPOINTS.md
11. docs/RULES.md
12. docs/DECISIONS.md
13. docs/ROADMAP.md

## 5. 开发完成定义

一次开发只有同时满足以下条件，才允许标记为完成：

1. 代码改动已进入工作区。
2. 已完成最小必要验证，并将结果写入 docs/PROJECT_STATUS.md 与 docs/VALIDATION.md。
3. 与本次改动相关的文档已同步更新。
4. 如果本次改动影响后续接手，docs/HANDOFF.md 已更新。
5. 如果本次改动新增了按钮、文件格式、配置目录、外部依赖或使用约定，docs/HANDOFF.md 与 docs/ENTRYPOINTS.md 必须新增说明。
6. 如果本次改动改变了规则、阈值、架构、真实工作流或优先级，对应文档已同步更新。
7. 如果用户在本轮提出的是成组需求，默认要在同一轮中持续推进并尽量一次性交付，而不是拆成半成品停下。
8. 结束回复中必须包含“本次改动概述”和“交接类文档同步情况”。
9. 验证完成后，工作区内不应残留与软件功能无关的测试产物或缓存文件。

## 6. 状态文档写法

docs/PROJECT_STATUS.md 只能写以下几类内容：

- 已完成事实
- 当前阻塞
- 已知问题
- 已验证结果
- 下一阶段优先级

禁止在该文件中写愿景类空话。

## 7. 交接文档写法

docs/HANDOFF.md 必须包含：

1. 当前接手入口顺序
2. 当前已验证到什么程度
3. 当前最可能踩坑的地方
4. 当前阻塞和临时规避方案
5. 建议下一位开发者优先做什么
6. 本轮新增配置文件、Excel 文件和入口按钮说明
7. 本轮验证命令与结果
8. 当前已过时说法与替换后的正确事实

## 8. 最低交接标准

如果下一位接手者无法直接从仓库文档回答以下问题，说明交接尚未完成：

1. 项目当前解决什么问题
2. 当前已经做到什么程度
3. 当前主要技术债是什么
4. 当前哪些输入格式和插件机制可用
5. 当前主分析链怎么运行
6. 运行和验证方式是什么
7. 新增 KPI、派生量、映射配置应该去哪里改
8. GUI 中哪些按钮和页面对应哪些外部文件
