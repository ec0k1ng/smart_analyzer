# TCS Smart Analyzer 入口与外部文件说明

## 1. 程序入口

### GUI

- 主模块：src/tcs_smart_analyzer/main.py
- 主窗口：src/tcs_smart_analyzer/ui/main_window.py
- 安装后命令：tcs-smart-analyzer

### CLI

- CLI 模块：src/tcs_smart_analyzer/cli.py
- 安装后命令：tcs-smart-analyzer-cli

## 2. 关键配置入口

- KPI 目录：src/tcs_smart_analyzer/config/kpi_specs/
- 派生量目录：src/tcs_smart_analyzer/config/derived_signals/
- 报告模板目录：src/tcs_smart_analyzer/config/report_templates/
- 接口映射主文件：src/tcs_smart_analyzer/config/interface_mapping.xlsx
- KPI 分组文件：src/tcs_smart_analyzer/config/kpi_groups.json
- 曲线视图记忆文件：src/tcs_smart_analyzer/config/chart_view_state.json
- DBC 目录：src/tcs_smart_analyzer/config/can_databases/
- 外部分析配置：用户自定义 JSON 文件，由 CLI 的 --config 或 GUI 中加载的 AnalysisSettings 使用

## 3. 当前仍存在但属于旧兼容入口的文件

- src/tcs_smart_analyzer/config/interface_mapping.json
- src/tcs_smart_analyzer/config/kpi_definitions.json
- src/tcs_smart_analyzer/config/rule_definitions.json
- src/tcs_smart_analyzer/config/rule_specs/

这些对象当前不应被写成主运行入口，只能视为历史兼容或废弃说明。

## 4. GUI 中用户能直接操作的外部对象

- 派生量文件：配置工作台中的派生量编辑页
- KPI 文件：配置工作台中的 KPI 编辑页
- KPI 分组：配置工作台中的 KPI 分组页
- 接口映射：配置工作台中的接口映射页
- 报告模板：配置工作台中的模板编辑页
- DBC 文件：主页右侧 DBC 管理区

## 5. 当前导出物

- HTML 汇总报告：输出目录中的 *_summary.html
- Word 汇总报告：输出目录中的 *_summary.docx

当前面向用户的默认导出不再强调 Excel 或 JSON。

## 6. 测试与脚本入口

- 单元测试目录：tests/
- GUI 离屏冒烟脚本：scripts/gui_smoke_check.py
- 主样例数据：sample_data/tcs_demo.csv
- 真实 Excel 样例：tests/test_dat_tcs.xlsx

## 7. 当前维护注意事项

- 曲线视图状态保存在 chart_view_state.json，修改面板/信号记忆逻辑时必须同步考虑该文件。
- 接口映射系统表的 from 列是只读来源列，双击跳转逻辑依赖它的格式。
- new_kpi.py 与 new_kpi_1.py 当前会被当作正式 KPI 插件参与运行时加载。
