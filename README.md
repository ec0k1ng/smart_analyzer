# TCS Smart Analyzer

离线运行的 TCS 打滑控制数据分析桌面工具。当前项目已经具备“导入数据、接口映射、派生量计算、KPI 计算、结果审阅、曲线核查、HTML/Word 汇总导出”的完整闭环，但仍处于持续工程化阶段，文档和代码都必须按当前事实维护，不允许再依赖旧会话记忆或历史设计猜测。

## 先看哪里

新接手人员请按下面顺序阅读：

1. docs/PROJECT_PLAYBOOK.md
2. docs/REQUIREMENTS.md
3. docs/PROJECT_STATUS.md
4. docs/TODO.md
5. docs/VALIDATION.md
6. docs/HANDOFF.md
7. docs/ARCHITECTURE.md
8. docs/IMPLEMENTATION_LOGIC.md
9. docs/ENTRYPOINTS.md
10. docs/RULES.md
11. docs/DECISIONS.md
12. docs/ROADMAP.md

docs/README.md 给出了完整文档导航和阅读说明。

## 当前产品边界

- 当前只聚焦 TCS 打滑控制分析。
- 当前主结果模型是“文件级 KPI + 规则判定”，不再维护旧版事件/工况窗口结果模型。
- 规则执行不再依赖独立 rule_specs 运行链，当前用户可见判定由 KPI 文件中的 threshold、pass_condition、rule_description 等字段生成。
- 用户视角只保留两层输入概念：
  - KPI/派生量文件中的 raw_inputs 名称
  - 接口映射表中用户手工填写的实际信号名
- 不再使用 signal_aliases 之类的“自动猜原始列名”概念。

## 当前能力概览

- 支持 CSV、Excel、文本 DAT、MAT、MDF、MF4、BLF 输入。
- 支持通过 DBC 解码 BLF 与总线类 MDF/MF4。
- 支持 Excel 接口映射表，系统信号自动汇总，用户手工维护实际列名。
- 支持独立 Python 文件形式的派生量和 KPI 插件。
- 支持 KPI 分组，同一路径文件可以按不同分组重复分析。
- 支持 GUI 工作台内编辑派生量、KPI、报告模板和接口映射。
- 支持曲线页多面板、信号搜索、多选拖拽、跨面板转移、横轴联动缩放。
- 支持运行日志、错误跳转、算法 print 输出收集。
- 支持 HTML 与 Word 汇总报告导出。
- 支持外部 JSON 分析配置覆盖阈值、来源和启停状态。

## 当前真实配置模型

- 派生量目录：src/tcs_smart_analyzer/config/derived_signals/
- KPI 目录：src/tcs_smart_analyzer/config/kpi_specs/
- 接口映射：src/tcs_smart_analyzer/config/interface_mapping.xlsx
- KPI 分组：src/tcs_smart_analyzer/config/kpi_groups.json
- 曲线视图记忆：src/tcs_smart_analyzer/config/chart_view_state.json
- 报告模板目录：src/tcs_smart_analyzer/config/report_templates/
- DBC 目录：src/tcs_smart_analyzer/config/can_databases/

所有正式 KPI 文件都必须提供：

- KPI_DEFINITION
- calculate_kpi(dataframe)
- calculate_kpi_series(dataframe)
- trend_source == name
- 可调标定集中在 CALIBRATION

所有正式派生量文件都必须提供：

- DERIVED_SIGNAL_DEFINITION
- description
- algorithm_summary
- calculate_signal(dataframe)
- 可调标定集中在 CALIBRATION

## 快速开始

```powershell
cd "c:\Users\Ecoking\Desktop\smart_analyzer\smart_analyzer"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m pip install -e .[gui]
tcs-smart-analyzer
```

只跑 CLI 或测试：

```powershell
python -m pip install -e .
```

需要 MDF/MF4 与 BLF 支持：

```powershell
python -m pip install -e .[mdf]
```

CLI 样例：

```powershell
tcs-smart-analyzer-cli --input .\sample_data\tcs_demo.csv --output-dir .\outputs
tcs-smart-analyzer-cli --input .\sample_data\tcs_demo.csv --output-dir .\outputs --config .\sample_data\analysis_profile_example.json
```

## 当前已知事实

- 本机当前验证解释器路径：c:/Users/Ecoking/Desktop/smart_analyzer/smart_analyzer/.venv/Scripts/python.exe
- sample_data/tcs_demo.csv 是主样例输入
- tests/test_dat_tcs.xlsx 是真实 Excel 样例
- 当前最近一次聚焦回归验证为：pytest tests/test_loaders.py tests/test_engine_pipeline.py，18 项通过
- 当前最近一次 GUI 离屏冒烟已通过，且包含曲线页 plot area 完整性探针 chart_plot_area_full_enough
- 曲线页首次显示完整性问题已在真实机器上完成复核确认，当前保留的延后布局收尾与切到曲线页主动刷新逻辑视为正式修复链路
- GUI 离屏冒烟脚本在 scripts/gui_smoke_check.py

## 不要再写进文档的旧说法

- 不要再写“自动别名猜测是主映射方式”
- 不要再写“独立 rule_specs 是当前执行入口”
- 不要再写“trend_source 可以随便填成临时列名”
- 不要再写“派生量不需要 algorithm_summary / CALIBRATION”

## 文档矩阵

- docs/REQUIREMENTS.md：需求、边界、验收口径
- docs/ARCHITECTURE.md：模块边界和系统设计
- docs/IMPLEMENTATION_LOGIC.md：当前真实功能逻辑与关键工作流
- docs/ENTRYPOINTS.md：入口、配置、外部文件、导出物
- docs/PROJECT_STATUS.md：当前事实、阻塞、已知问题
- docs/TODO.md：后续优先级
- docs/VALIDATION.md：当前验证方式与结果
- docs/HANDOFF.md：下一位接手者的快速上手与风险提示
- docs/RULES.md：当前 KPI 判定口径与规则治理要求
- docs/DECISIONS.md：关键决策记录
- docs/ROADMAP.md：后续阶段路线
- docs/CHANGELOG.md：文档与功能的阶段性变化记录
