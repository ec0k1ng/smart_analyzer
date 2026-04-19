# TCS Smart Analyzer 交接说明

## 1. 接手入口顺序

进入仓库后不要先猜代码，也不要先翻单个 Python 文件。请按下面顺序接手：

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

## 2. 当前你要先知道什么

### 2.1 当前真实产品模型

- 当前只做 TCS 打滑控制分析。
- 当前主结果是文件级 KPI 与其判定结果，不再是旧版事件窗口模型。
- 当前用户只需要理解 raw_inputs 与接口映射表中的实际信号名。
- 当前规则判定由 KPI 文件本身生成，不再依赖独立 rule_specs 运行链。

### 2.2 当前最重要的技术事实

- 接口映射系统表第一列是 raw_input_name，第二列是 from，第三列起才是用户填写的实际信号名。
- 当前仓库正式派生量只有两个：slip_ratio、tcs_target_slip_ratio_global。
- 当前仓库已经没有 tcs_active_avg_slip_ratio 正式文件。
- 当前正式 KPI 文件名必须与 KPI_DEFINITION["name"] 一致，当前正式 KPI 包含 vehicle_shake_intensity 和 tcs_max_control_time。
- 当前安装程序唯一输出目录为 installer_release/，标准构建脚本为 scripts/build_installer.ps1。
- 当前发布基线已是 V1.2，对应包版本 1.2.0。
- 当前 DAT 读取链路会先尝试按测量文件解析，再回退到文本表格解析。
- 当前曲线页子框信号表宽度支持自动扩展并在同一工作表内同步。

## 3. 当前已验证到什么程度

### 3.1 已验证

- 主分析链、入口位置、配置目录和导出路径已经核对。
- 文档矩阵已经按当前代码和工作区状态重写。
- 当前完整 unittest 已执行，得到真实结果：42 项中 2 失败、8 错误，其余通过。
- tests.test_loaders 已重新执行，11 项全部通过。
- V1.2 安装程序已按标准脚本重新构建。

### 3.2 未重新验证

- 本轮没有重新执行 GUI 离屏冒烟。
- 本轮没有重新执行真实总线样本验证。
- 本轮没有拿用户真实 INCA DAT 样本做最终兼容确认。

## 4. 当前最可能踩坑的地方

1. 误以为 signal_aliases 仍是主逻辑。
2. 误以为 rule_specs 目录仍参与执行。
3. 误以为 trend_source 可以写成任意临时列名。
4. 误以为当前测试套件是全绿。
5. 误以为 tcs_active_avg_slip_ratio 仍然存在。
6. 误以为接口映射表的第一列和第二列都可由用户编辑。

## 5. 当前阻塞与临时规避方案

### 阻塞 1：测试基线仍引用旧派生量

现象：

- test_editable_configs、test_engine_pipeline 等测试仍引用 tcs_active_avg_slip_ratio。

规避方案：

- 接手前先接受“当前代码事实优先于旧测试”。
- 如果要继续开发，优先修测试基线，再扩功能。

### 阻塞 2：导出相关测试与当前映射状态存在偏差

现象：

- 部分导出测试会在 build_signal_mapping 阶段因为关键字段缺失而失败。

规避方案：

- 优先检查测试是否显式准备了当前接口映射前置条件。

### 阻塞 3：真实 INCA DAT 变体仍缺样本闭环

现象：

- 代码已新增 DAT 测量文件优先解析路径，但仓库内仍没有用户真实 INCA DAT 样本可做最终确认。

规避方案：

- 若用户继续反馈 DAT 失败，优先索取失败样本或最小可复现片段。
- 不要再把 DAT 支持写死成“仅文本 DAT”，当前事实已不是这样。

## 6. 当前新增/关键文件说明

- docs/IMPLEMENTATION_LOGIC.md：当前真实实现逻辑与 GUI 工作流说明
- src/tcs_smart_analyzer/config/interface_mapping.xlsx：接口映射主文件
- src/tcs_smart_analyzer/config/chart_view_state.json：曲线页面板配置记忆文件
- src/tcs_smart_analyzer/config/kpi_groups.json：KPI 分组定义文件
- scripts/gui_smoke_check.py：GUI 离屏冒烟脚本
- scripts/build_installer.ps1：安装程序标准构建脚本
- installer_release/：当前版本安装程序唯一发布目录

## 7. 建议下一位优先做什么

1. 先修测试，让测试基线与当前派生量/KPI 清单一致。
2. 再做 BLF/MF4 + DBC 与真实 INCA DAT 的样本回归。
3. 最后再开始新的功能开发。

## 8. 当前已过时说法与正确事实

- 旧说法：系统主要靠别名自动猜列。
  正确事实：当前对用户可见的主模型是 raw_inputs + 手工接口映射名。

- 旧说法：rule_specs 是当前规则入口。
  正确事实：当前用户可见判定逻辑来自 KPI 文件。

- 旧说法：当前测试已经全部通过。
  正确事实：当前完整 unittest 不是全绿，详见 PROJECT_STATUS.md。

- 旧说法：tcs_active_avg_slip_ratio 是当前正式派生量之一。
  正确事实：当前仓库中已不存在该正式文件。
