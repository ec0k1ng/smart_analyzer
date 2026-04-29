# 自动化数据分析工具 当前状态

## 1. 当前阶段结论

项目当前处于“主闭环可用、最近一轮聚焦回归已通过、接口映射与打滑量算法已升级、真实桌面环境曲线页问题已完成收口确认”的阶段。

当前必须以以下事实为准：

- 数据加载层最近已经补上 DAT 列名协议尾缀清理、BLF/ASC 按需解码和 BLF 索引对齐修复。
- 结果与曲线层最近已经补上“新一轮分析清空旧结果”“按结果实例缓存曲线帧”“共享光标覆盖线”“延后布局收尾”和“切到曲线页主动刷新”。
- 最近一次实际执行的验证不是旧的 42 项 unittest 统计，而是当前聚焦回归和 GUI 离屏冒烟。
- 曲线页首次显示不完整问题已在真实机器上完成回归确认，当前可视为已收口问题。

## 2. 当前已完成事实

### 2.1 分析闭环

- 已具备 CSV、Excel、DAT、MAT、MDF、MF4、BLF、ASC 输入能力。
- 已具备接口映射 Excel 驱动的标准化链路。
- 已具备派生量 -> KPI -> 规则结果 -> 报告导出的完整链路。
- 已具备 HTML 与 Word 汇总导出。
- 已具备 GUI 与 CLI 双入口。

### 2.2 当前数据加载层事实

- DAT/表格类列名在加载出口会统一清理，支持去除类似 \XCP: 1 这类协议后缀。
- 所有支持的数据类型当前都会优先只保留当前分析真正需要的接口映射信号，其余数据不再进入后续处理。
- BLF 时序拼帧中 forward fill gap 的布尔掩码与时间索引已统一，已修复大文件场景下的 pandas 索引不对齐错误。

### 2.3 当前 GUI 能力

- 已支持文件入队、按 KPI 分组分析、结果查看、曲线查看、DBC 管理。
- 已支持派生量、KPI、模板、接口映射的内嵌编辑。
- 已支持运行日志清空、错误跳转、算法 print 输出收集。
- 已支持曲线页多面板、多信号拖拽、跨面板转移、横轴联动缩放。
- 已支持共享光标覆盖线、同工作表信号表宽度同步、切到曲线页主动重刷图表。
- 已支持空子框显示时间轴、子框尺寸变化后曲线随布局重算、共享光标贯穿所有子框、子框内信号拖拽重排。
- 已支持新一轮分析开始时清空旧结果但保留队列，避免二次分析继续展示第一次的结果。
- 已支持 GUI 启动时显式激活主窗口，并在 QApplication 上保留主窗口强引用。

### 2.4 当前配置模型

- 当前正式派生量目录：src/tcs_smart_analyzer/config/derived_signals/
- 当前正式 KPI 目录：src/tcs_smart_analyzer/config/kpi_specs/
- 当前接口映射主文件：src/tcs_smart_analyzer/config/interface_mapping.xlsx
- 当前 KPI 分组主文件：src/tcs_smart_analyzer/config/kpi_groups.json
- 当前曲线视图记忆文件：src/tcs_smart_analyzer/config/chart_view_state.json
- 当前接口映射支持直接填写公式表达式，例如 time_ms*0.001。

### 2.5 当前映射链路事实

- 如果接口映射表为某个标准信号显式填写了真实信号名，当前分析会严格按该名字匹配，不再回退到标准名或模糊近似匹配。
- 当前标准输入命名已开始收敛到带单位风格，例如 vehicle_speed_kph、wheel_speed_fl_kph、yaw_rate_degps；time_s 固定作为第一行系统信号存在。
- time_s 仍然保留加载器层的通用时间列归一化能力，但该能力不再绕过用户显式填写的 time_s 映射。
- 运行时默认补值信号设计已删除，缺失真实信号时不再静默补零。
- 分析前会强制保存当前映射表编辑状态，避免界面上的最新修改未参与本次分析。

## 2.6 当前算法事实

- 现有 slip_ratio 派生量的业务语义已经切换为“打滑量”，按轮速与车速差计算。
- 现有 tcs_target_slip_ratio_global 派生量的业务语义已经切换为“全局目标打滑量”，输出单值标量。
- 当前新增有效 KPI 包括：最大横摆角速度绝对值、最大方向盘转角绝对值、全油门平均纵向加速度。

## 3. 当前阻塞

### 3.1 完整测试基线状态未在本轮重刷

当前状态：

- 本轮重新执行的是聚焦回归：tests/test_loaders.py 与 tests/test_engine_pipeline.py。
- 旧文档中“42 项 unittest、2 失败、8 错误”的统计不再视为本轮最新事实。

当前缺口：

- 如果后续要继续做较大功能开发，仍建议重新刷新完整测试基线并同步文档。

## 4. 当前已知问题

- 当前仓库不再存在 tcs_active_avg_slip_ratio 文件，任何仍引用它的文档、测试或假设都视为过时信息。

## 5. 当前发布状态

- 当前发布版本基线仍为 V1.2，对应包版本 1.2.0。
- 当前用户发布名称为“自动化数据分析工具”。
- 项目内安装程序唯一输出目录为 installer_release/。
- 标准安装程序构建脚本为 scripts/build_installer.ps1。
- 本轮没有重新构建安装程序。

## 6. 当前验证现状

### 6.1 本轮已实际执行

- 已执行 pytest tests/test_signal_mapping.py tests/test_loaders.py tests/test_engine_pipeline.py，27 项全部通过。
- 已执行 pytest tests/test_signal_mapping.py tests/test_loaders.py tests/test_engine_pipeline.py tests/test_editable_configs.py，52 项全部通过。
- 已执行 scripts/gui_smoke_check.py，并通过空末尾子框时间轴、缩放后联动、光标贯穿和信号重排等探针。
- 已执行 py_compile 检查 main_window.py、engine.py、loaders.py、signal_mapping.py，无语法错误。

### 6.2 本轮未重新执行

- 本轮未重新执行完整 pytest/unittest 全量基线。
- 本轮未重新执行真实 BLF/MF4 样本验证。
- 本轮未拿用户真实 INCA DAT 样本做最终兼容确认。

## 7. 当前接手建议

如果下一位接手者要继续推进，优先级建议如下：

1. 先刷新完整测试基线，替换掉旧文档中的历史 unittest 统计。
2. 然后补真实总线数据样本回归，尤其是 BLF/MF4 + DBC 和真实 INCA DAT。
3. 最后继续补齐更大体量文件的性能基线与加载耗时观测。
