# TCS Smart Analyzer 交接说明

## 1. 接手入口顺序

进入仓库后按下面顺序建立上下文，不要先凭记忆猜实现：

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
14. docs/CHANGELOG.md

## 2. 当前发布阶段

- 当前代码状态可以视为发布候选版本，包版本仍是 1.2.0。
- 本轮核心目标已从“补功能”转为“收口文档、清理噪音、准备发布”。
- 安装程序标准构建入口仍是 scripts/build_installer.ps1，最终发布目录仍是 installer_release/。
- 本轮尚未重新构建安装程序，因此当前仓库状态是“代码和文档已收口，待执行发布构建”。

## 3. 当前真实产品模型

- 当前只聚焦 TCS 打滑控制分析。
- 当前主结果模型是“文件级 KPI + 判定结果 + 曲线复核”，不再维护旧事件窗口叙事。
- 用户只需要理解 raw_inputs 与接口映射表中填写的实际信号名。
- 当前规则展示来自 KPI 文件中的 threshold、pass_condition、rule_description 等字段，不再把独立 rule_specs 写成主执行入口。

## 4. 本轮已经落地的关键变化

### 4.1 数据加载与映射链路

- DAT、MDF、MF4 已补上与 CSV/Excel 一致的“先探测列/通道，再确认映射，再按需读取”的两段式链路。
- DAT 会优先尝试测量文件解析，再回退到文本表格解析；文本 DAT 与 INCA DAT 都支持按命中列过滤读取。
- MDF/MF4 支持按 selected_source_columns 过滤通道，减少无关读取。
- BLF/ASC 的详细日志已明确写出“按需 DBC 解码，不会展开全部总线信号”，避免误解为全量解码。
- 显式接口映射仍保持严格模式，不再静默回退到标准名或模糊匹配。

### 4.2 GUI 与模板编辑

- 派生量与 KPI 下拉列表顺序已调整为“示例在前，其余按 name 字母序”。
- 详细模式与导出格式切换都改成无蓝点的文本勾选样式。
- 曲线页在没有分析结果时也允许添加和保留信号，只显示占位内容，不阻断配置。
- 模板编辑器已具备：未保存标记、Ctrl+S 保存、Jinja 语法校验、错误高亮、打开模板目录、新建草稿模板。
- 模板选择已收敛到模板编辑区下拉框，不再保留重复且无效的“当前模板”行。

### 4.3 HTML / Word 报告

- 报告上下文已经统一为 grouped_results，按“KPI 分组 -> 数据名称 -> KPI 列表”组织。
- HTML 默认模板、demo 模板和示例模板都已支持左侧固定目录、分组/文件层级、曲线快照和收起/展开目录。
- HTML 正文已改成居中且不随目录显隐左右偏移。
- Word 报告第一页已改成真实目录内容，不再显示“右键更新域以生成目录”占位提示。
- Word 正文已使用 Heading 1 / Heading 2 承载分组与文件层级，导航窗格可直接反映层级结构。
- Word 与 HTML 都会插入基于曲线工作表 1 的截图预览，截图保留多子框、时间轴、纵轴刻度和颜色一致的图例名称。

### 4.4 Word 目录跳转修复

- Word 目录项已改为内部 hyperlink + bookmark 方案。
- 书签插入位置已调整到段落属性之后，避免 Word 自动修复 XML 顺序导致跳转错位。
- 分组与文件锚点都已改成更短的安全格式，避免文件级锚点过长导致跳回标题行。
- 目录可跳转文本已移除下划线样式。

## 5. 当前最重要的技术事实

- 接口映射系统表第一列是 raw_input_name，第二列是 from，第三列起才是用户填写的实际信号名。
- 正式派生量目录仍在 src/tcs_smart_analyzer/config/derived_signals/，正式 KPI 目录仍在 src/tcs_smart_analyzer/config/kpi_specs/。
- chart_view_state.json 继续作为曲线页工作表与子框布局记忆文件。
- 报告模板目录是 src/tcs_smart_analyzer/config/report_templates/，当前模板已包含可编辑 HTML 示例和 demo 模板。
- Word 报告的曲线快照依赖 Qt/SVG 离屏渲染；CLI 或测试环境必须允许惰性初始化 QGuiApplication。

## 6. 当前已验证到什么程度

### 6.1 已验证

- 已实际执行 pytest tests/test_signal_mapping.py tests/test_loaders.py tests/test_engine_pipeline.py tests/test_editable_configs.py tests/test_rule_settings.py tests/test_exporters.py，76 项全部通过。
- GUI 离屏冒烟脚本 scripts/gui_smoke_check.py 已通过，最近一次结果为 20 / 20。
- src/tcs_smart_analyzer/ui/main_window.py、src/tcs_smart_analyzer/reporting/exporters.py、src/tcs_smart_analyzer/core/engine.py、src/tcs_smart_analyzer/data/loaders.py、src/tcs_smart_analyzer/config/editable_configs.py 的 py_compile 已通过。
- Word 目录 hyperlink、bookmark、短锚点长度和书签顺序都有自动化断言覆盖。

### 6.2 仍建议在发版前手工确认

- 用真实 Word 客户端打开一份新导出的 docx，手工点一次首页目录中的分组和数据名称。
- 用浏览器打开 HTML 报告，确认左侧目录、截图和正文布局与预期一致。
- 如本次需要交付安装包，再执行一次安装程序构建与安装后打开验证。

## 7. 当前明确已清理的仓库噪音

- 已删除根目录里的 pytest_exporters_failure.txt 失败残留文件。
- 交接、状态、验证、待办、变更记录与根 README 已同步到当前事实，不再保留“旧测试阻塞仍是主问题”的描述。

## 8. 当前不要再踩的坑

1. 不要再把 signal_aliases 写成当前主映射机制。
2. 不要再把 rule_specs 写成当前主执行入口。
3. 不要再把 Word 目录跳转理解为传统 TOC 域；当前实现是内部 hyperlink + bookmark。
4. 不要再把 DAT 写成“只支持文本 DAT”；当前事实包含测量文件优先解析与文本回退。
5. 不要再把“导出模板只是简单表格”写进任何文档；当前报告已经包含目录、分组结构和曲线截图。

## 9. 下一位如果继续推进，优先做什么

1. 执行一次发布前完整回归和手工导出验收。
2. 若本次要交付安装包，运行 scripts/build_installer.ps1 并验证 installer_release/ 产物。
3. 若后续还有功能开发，再补真实 BLF/MF4 + DBC 和真实 INCA DAT 的样本级工程回归。
