# 自动化数据分析工具 当前状态

## 1. 当前阶段结论

项目当前处于“功能闭环已形成，但测试基线与文档刚完成重新收口”的阶段。对接手者来说，最大的变化不是代码从零开始，而是必须先接受以下事实：

- 当前主产品已经可用
- 当前文档体系已补齐
- 当前完整测试套件不是全绿
- 当前一部分历史描述和历史测试仍停留在旧模型，需要后续继续清理

## 2. 当前已完成事实

### 2.1 分析闭环

- 已具备 CSV、Excel、DAT、MAT、MDF、MF4、BLF 输入能力。
- 已具备接口映射 Excel 驱动的标准化链路。
- 已具备派生量 -> KPI -> 规则结果 -> 报告导出的完整链路。
- 已具备 HTML 与 Word 汇总导出。
- 已具备 GUI 与 CLI 双入口。
- 已完成 V1.2 安装程序构建链路，installer_release/ 下保留当前安装包产物。

### 2.2 当前 GUI 能力

- 已支持文件入队、按 KPI 分组分析、结果查看、曲线查看、DBC 管理。
- 已支持派生量、KPI、模板、接口映射的内嵌编辑。
- 已支持运行日志清空、错误跳转、算法 print 输出收集。
- 已支持曲线页多面板、多信号拖拽、跨面板转移、横轴联动缩放。
- 已修复曲线页无光标模式残留光标假象、子框关闭按钮跟随缩放、长信号名显示受限问题。
- 已支持编辑器关键行高亮、Ctrl+S 保存、Ctrl+F 查找替换和跳转。

### 2.3 当前配置模型

- 当前正式派生量目录：src/tcs_smart_analyzer/config/derived_signals/
- 当前正式 KPI 目录：src/tcs_smart_analyzer/config/kpi_specs/
- 当前接口映射主文件：src/tcs_smart_analyzer/config/interface_mapping.xlsx
- 当前 KPI 分组主文件：src/tcs_smart_analyzer/config/kpi_groups.json
- 当前曲线视图记忆文件：src/tcs_smart_analyzer/config/chart_view_state.json

### 2.4 当前正式插件清单

当前派生量：

- slip_ratio
- tcs_target_slip_ratio_global

当前 KPI：

- peak_slip_ratio
- max_jerk_mps3
- max_slip_speed
- mean_vehicle_speed_kph
- vehicle_shake_intensity
- tcs_max_control_time

## 3. 当前阻塞

### 3.1 测试基线与当前实现不一致

当前完整 unittest 套件执行结果为：

- 总计 42 项
- 失败 2 项
- 错误 8 项
- 其余通过

当前主要失败原因：

1. 测试仍引用已不存在的派生量 tcs_active_avg_slip_ratio。
2. 与派生量清单动态展示相关的断言仍按旧清单编写。
3. 部分导出测试依赖的接口映射前置条件与当前仓库状态不一致，触发关键字段缺失错误。

### 3.2 真实样本回归仍不够

- BLF/MDF/MF4 + DBC 链路仍缺少足够真实工程样本回归。
- INCA DAT 已新增“测量文件优先、文本回退”的兼容路径，但仍缺少用户真实样本做最终变体确认。
- 当前文档已如实记录这一点，但代码层面仍需后续补样本验证。

## 4. 当前已知问题

- 文档已收敛为当前事实，但测试基线还没有完全同步到当前实现。
- 当前仓库不再存在 tcs_active_avg_slip_ratio 文件，任何仍引用它的文档、测试或假设都视为过时信息。

## 5. 当前发布状态

- 当前发布版本基线已提升到 V1.2，对应包版本 1.2.0。
- 当前用户发布名称为“自动化数据分析工具”。
- 项目内安装程序唯一输出目录为 installer_release/。
- 标准安装程序构建脚本为 scripts/build_installer.ps1。
- 本轮已按用户要求重新构建安装程序，并同步 installer_release/ 当前版本产物。
- installer_release/ 目录按规则只保留当前版本安装程序，不保留临时构建文件。
- 发布安装程序时，安装包必须包含完整应用目录与当前配置文件，并提供安装目录选择过程。

## 6. 当前验证现状

### 6.1 已实际执行

- 已执行完整 unittest discover，结果如上。
- 已执行 tests.test_loaders，11 项全部通过。
- 已确认 CLI 与 GUI 入口文件位置、配置目录和主要工作流。
- 已系统校对 docs 目录与当前代码结构的一致性。
- 已按标准脚本重建 V1.2 安装程序。

### 6.2 本轮未重新执行

- 本轮未重新执行 GUI 离屏冒烟脚本。
- 本轮未重新执行真实 BLF/MF4 样本验证。
- 本轮未拿用户真实 INCA DAT 样本做最终兼容确认。

## 7. 当前接手建议

如果下一位接手者要继续推进，优先级建议如下：

1. 先修复测试基线与当前实现不一致的问题。
2. 再补真实总线数据样本回归，尤其是 BLF/MF4 + DBC 和真实 INCA DAT。
3. 然后再进入人工复核闭环或更复杂 GUI 能力。
