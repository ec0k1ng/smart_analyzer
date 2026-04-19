# 变更记录

## 2026-04-17

### V1.2 安装程序同步升级

- 安装程序版本同步升级到 V1.2，并按标准脚本重新构建 installer_release/自动化数据分析工具安装程序 V1.2.exe。
- 安装器界面继续优化为更明确的分步式向导，左侧步骤高亮与当前页同步刷新。
- 安装程序发布目录继续只保留当前版本产物，不再混放旧版本安装包。

### 曲线页与 DAT 兼容修复

- 修复曲线页无光标模式仍残留双光标假象的问题，关闭光标后会强制清空状态并重绘。
- 修复曲线子框关闭按钮定位，按钮改为跟随整个子框尺寸变化并保持在右上角。
- 放宽信号名称区域宽度限制，支持根据当前面板内容自动扩展并在多子框之间同步宽度。
- DAT 读取流程改为优先尝试测量文件解析，再回退到文本 DAT 解析，不再仅依赖空字节启发式判断。
- 补充并通过加载器回归测试，覆盖 DAT 测量文件回退路径。

## 2026-04-15

### 安装程序方案修正

- 安装程序改为包含完整应用目录而非单独主 exe，当前配置文件会随安装包一并交付。
- 安装器新增安装目录选择过程，并支持创建桌面与开始菜单快捷方式。
- 发布名称统一调整为“自动化数据分析工具”。
- 项目规则改为仅在用户明确提出发布需求时才生成安装程序，不再要求每次变更同步构建。

## 2026-04-14

### V1.1 发布基线

- 项目版本从 0.1.0 提升到 1.1.0，建立 V1.1 作为后续安装程序升级基线。
- 新增 scripts/build_installer.ps1，统一 PyInstaller 安装程序构建流程。
- 新增 scripts/packaging/installer_bootstrap.py，用于生成可安装到本机用户目录的安装程序。
- 新增 installer_release/ 作为项目内唯一安装程序发布目录，并约束该目录只保留当前安装程序。

### 文件名与界面修正

- KPI 与派生量加载链新增文件名自动纠偏逻辑，历史错名文件会按 definition.name 自动收敛。
- KPI 保存流程继续收紧，确保编辑器保存后物理文件名与 KPI 名称保持一致。
- 曲线子框进一步去边框，仅保留分界线，提高曲线显示面积。

## 2026-04-12

### 文档体系重构

- 重写根 README，移除 signal_aliases 自动映射等旧叙事，明确当前阅读顺序和系统边界。
- 重写 docs/README.md，建立完整文档导航。
- 重写 docs/PROJECT_PLAYBOOK.md，明确文档治理和交接标准。
- 重写 docs/REQUIREMENTS.md，按当前实现重新定义需求、边界和验收口径。
- 重写 docs/ARCHITECTURE.md，按当前代码重述模块边界与运行层次。
- 新增 docs/IMPLEMENTATION_LOGIC.md，专门解释当前真实工作流与 GUI 行为。
- 重写 docs/PROJECT_STATUS.md、docs/TODO.md、docs/VALIDATION.md、docs/HANDOFF.md、docs/ENTRYPOINTS.md。
- 重写 docs/RULES.md、docs/DECISIONS.md、docs/ROADMAP.md、docs/需求说明书.txt。

### 当前事实修正

- 明确当前用户输入模型是 raw_inputs + 手工接口映射实际信号名。
- 明确当前正式派生量不包含 tcs_active_avg_slip_ratio。
- 明确当前规则判定由 KPI 文件收敛生成，不再把独立 rule_specs 写成主执行入口。
- 明确当前完整 unittest 不是全绿，文档不再沿用“全部通过”的旧结论。

### 代码修复

- 修复 src/tcs_smart_analyzer/config/kpi_specs/new_kpi_1.py 中对 slip_ratio_renamed 的错误依赖引用。
- 修复 src/tcs_smart_analyzer/config/derived_signals/tcs_target_slip_ratio_global.py 中对 slip_ratio_renamed 的错误依赖引用。
- 以上修复解除 AnalysisEngine 初始化时的派生量依赖阻断。
