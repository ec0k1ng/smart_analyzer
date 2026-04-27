# 变更记录

## 2026-04-27

### 曲线子框交互与显示修复

- 空子框现在也会创建时间轴和基础坐标轴，不再因为最下面子框无信号而丢失时间轴显示。
- 曲线图在子框尺寸变化时会释放旧的固定 plot area，并重新对齐布局，修复多子框场景下横纵缩放后曲线不随子框变化的问题。
- 共享光标覆盖层改为按所有子框坐标区贯穿计算，不再只在有信号的区域显示，也会在布局变化后自动刷新。
- 子框内信号顺序支持通过鼠标拖拽重排，同面板内调整顺序时不会再被强制追加到末尾。
- 时间轴显示位置已固定为最底部子框，不再跟随“最后一个有信号的子框”漂移。
- 右侧信号表区域取消了过小的最大宽度限制，并把布局重算改为合并刷新，减轻拖动时的卡顿感。
- 光标拖动已限制在 plot area 内，不再能被拖到右侧信号表区域。

### 映射严格性修复

- 当接口映射表为某个标准信号显式填写了真实信号名时，分析链不再回退到标准名/模糊匹配自动兜底。
- 因此 time_s 配成 time1 但文件只有 time 时，现在会按预期报缺失，而不是继续借助自动时间列归一化隐式通过。
- 已彻底删除运行时默认补值信号设计，不再允许 tcs_active_fl 这类信号在缺失时被静默补零。
- accel_pedal_pct 也不再在缺少真实输入时默认补 0；只有存在 torque_request_nm 时才允许由真实信号推导。
- 分析前会强制落盘当前映射表编辑状态，避免“刚改完映射立即分析”仍读取旧值。
- 针对 Excel 重复 time 表头被 pandas 改写为 time.1/time.2 的场景，显式手工映射已改为只允许原始列名精确匹配或清理协议尾缀后的精确匹配，不再把 time1/time2/time3 误判为真实存在。

### 曲线页交互修复补充

- 侧边信号表拖动时，光标覆盖层改为立即刷新，较重的 plot area 对齐则延后防抖执行，降低缩放迟滞和光标拖动失灵概率。

### 回归验证

- pytest tests/test_signal_mapping.py tests/test_loaders.py tests/test_engine_pipeline.py tests/test_editable_configs.py：52 项通过。
- scripts/gui_smoke_check.py：通过，覆盖空末尾子框时间轴、缩放后联动保持、光标贯穿和面板内顺序重排探针。

## 2026-04-24

### 数据加载与总线解码修复

- DAT/表格类列名加载出口新增协议尾缀清理，支持去除类似 \XCP: 1 这类后缀，减少接口映射命中失败。
- BLF 时序拼帧修复 forward fill gap 的索引对齐问题，消除大文件场景下的 pandas 布尔索引不对齐错误。
- BLF/ASC 解码链路改为按当前分析真正需要的实际信号名做预筛选，避免盲目解出全部 DBC 信号。
- 补充 tests/test_loaders.py 回归覆盖，新增 DAT 协议尾缀、BLF gap 对齐和按需解码探针。

### 结果生命周期、曲线页与启动稳定性修复

- 新一轮分析开始时会清空上一轮结果但保留队列，避免二次分析继续展示旧结果。
- 曲线缓存改为按结果实例隔离，避免同一路径文件重分析后复用旧帧。
- 曲线页新增共享光标覆盖层，并把图表布局收尾延后到事件循环下一拍。
- 切到主标签“曲线”时会主动触发图表刷新，以缓解分析在隐藏页完成后首次显示不完整的问题。
- GUI 启动时增加 QApplication 级主窗口强引用，并显式 showNormal/raise_/activateWindow 提升窗口激活稳定性。

### 文档与验证同步

- README、PROJECT_STATUS、VALIDATION、HANDOFF、ENTRYPOINTS、IMPLEMENTATION_LOGIC、TODO、DECISIONS 已同步到当前代码事实。
- 本轮重新执行 pytest tests/test_loaders.py tests/test_engine_pipeline.py，18 项通过。
- 本轮重新执行 scripts/gui_smoke_check.py，13 项探针通过，包含 chart_plot_area_full_enough。

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
