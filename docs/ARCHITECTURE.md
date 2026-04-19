# TCS Smart Analyzer 架构设计

## 1. 架构目标

当前架构的核心目标不是“堆出功能”，而是保证以下四点长期成立：

1. 分析链路对工程师可解释
2. 用户可通过配置文件和 Python 插件持续扩展
3. GUI、CLI、导出使用同一套分析结果模型
4. 后续接手者可以基于文档快速理解当前真实实现

## 2. 当前总体结构

系统按以下层次组织：

1. data：加载原始日志文件
2. config：维护可编辑配置、模板、接口映射和运行时定义装载
3. core：完成信号映射、标准化、派生量计算、KPI 计算、规则结果生成
4. reporting：导出 HTML/Word 汇总报告
5. ui：桌面 GUI 工作台
6. cli：无界面批处理入口

当前已经不再使用“独立规则执行链 + 黑盒公共特征层”的旧架构。用户可见的判定逻辑统一收敛在 KPI 文件中。

## 3. 关键模块边界

### 3.1 输入层

- 文件：src/tcs_smart_analyzer/data/loaders.py
- 职责：按后缀读取 CSV、Excel、文本 DAT、MAT、MDF、MF4、BLF
- 外部依赖：
  - 核心：pandas、numpy、scipy
  - 可选：asammdf、cantools、python-can

设计约束：

- BLF 与总线类 MDF/MF4 依赖 DBC 解码。
- 二进制 DAT 当前不支持。
- 加载层只负责把文件变成 DataFrame，不负责业务语义解释。

### 3.2 配置与定义装载层

- 文件：src/tcs_smart_analyzer/config/editable_configs.py
- 职责：
  - 装载 KPI/派生量 Python 插件
  - 维护接口映射 Excel
  - 维护 KPI 分组
  - 维护曲线视图记忆
  - 生成和刷新 guide/template 内容
  - 做静态校验与部分运行时合同校验

当前配置边界：

- 正式 KPI 定义目录：src/tcs_smart_analyzer/config/kpi_specs/
- 正式派生量目录：src/tcs_smart_analyzer/config/derived_signals/
- rule_specs 目录当前不参与执行，只保留为历史兼容入口
- legacy JSON 文件保留为废弃说明，不再是主运行入口

### 3.3 信号映射与标准化层

- 文件：src/tcs_smart_analyzer/core/signal_mapping.py
- 职责：
  - 将原始列映射到标准信号
  - 校验关键字段
  - 对可选字段补默认值
  - 输出统一标准化 DataFrame

当前设计要点：

- 用户只理解 raw_inputs 和接口映射表中的实际信号名。
- 当前不再保留 signal_aliases 主逻辑。
- 接口映射优先按用户填写的 actual_signal_name_1..5 逐列匹配。
- 缺失关键字段时立即阻断分析。

### 3.4 派生量层

- 文件：src/tcs_smart_analyzer/core/features.py
- 定义来源：src/tcs_smart_analyzer/config/derived_signals/
- 职责：
  - 按 derived_inputs 拓扑顺序计算派生量
  - 将派生量列写回标准化 DataFrame
  - 让多个 KPI 共享中间序列

当前设计要点：

- 派生量是共享中间量，不是黑盒特征缓存。
- 派生量文件必须自解释，至少有 description、algorithm_summary、CALIBRATION。
- 派生量直接决定曲线页中对应信号的显示曲线。

### 3.5 KPI 层

- 文件：src/tcs_smart_analyzer/core/features.py
- 定义来源：src/tcs_smart_analyzer/config/kpi_specs/
- 职责：
  - 执行 calculate_kpi(dataframe)
  - 执行 calculate_kpi_series(dataframe)
  - 产出 KpiResult
  - 为后续规则结果与曲线页提供统一输入

当前设计要点：

- KPI 文件同时承担“计算 + 判定”双重职责。
- KPI 过程曲线是硬约束。
- trend_source 必须等于 KPI name。
- 单 KPI 专用算法保留在 KPI 文件中，不再外提为不透明公共逻辑。

### 3.6 规则结果层

- 文件：src/tcs_smart_analyzer/core/features.py
- 职责：将 KPI 结果转换为 RuleResult

当前规则模型：

- 判定逻辑来自 KPI_DEFINITION 的 threshold、pass_condition、rule_description 等字段。
- 不再依赖独立 rule_specs 执行链。
- 规则结果不再绑定旧版事件窗口模型。

### 3.7 编排层

- 文件：src/tcs_smart_analyzer/core/engine.py
- 核心职责：
  - 同步接口映射
  - 加载运行时定义
  - 调用加载器、映射器、派生量计算、KPI 计算、规则转换
  - 产出 AnalysisResult

它是 GUI 与 CLI 共用的唯一主分析入口。

### 3.8 展示与导出层

- GUI：src/tcs_smart_analyzer/ui/main_window.py
- CLI：src/tcs_smart_analyzer/cli.py
- 导出：src/tcs_smart_analyzer/reporting/exporters.py

设计原则：

- GUI、CLI、导出共用 AnalysisResult 上下文。
- HTML 与 Word 导出结构对齐 GUI 结果页。
- 曲线页优先展示真实序列，而不是最终常数值。

## 4. 当前关键数据模型

### 4.1 AnalysisResult

AnalysisResult 是 GUI、CLI、导出的统一结果容器，包含：

- context
- kpis
- rule_results
- normalized_frame

### 4.2 normalized_frame

normalized_frame 是当前最关键的运行期数据表，按顺序承载：

1. 标准化原始信号
2. 派生量列
3. KPI 过程曲线列

### 4.3 结果唯一键

GUI 当前按“真实文件路径 + KPI 分组”组织结果，因此同一个文件可以在多个分组下分别保存结果。

## 5. 当前真实扩展点

### 5.1 用户可编辑扩展点

- KPI Python 文件
- 派生量 Python 文件
- 报告模板
- 接口映射 Excel
- KPI 分组 JSON
- 外部分析配置 JSON

### 5.2 不建议用户直接改动的区域

- core/ 下主分析编排
- ui/ 下主窗口框架
- reporting/ 下导出上下文结构

## 6. 当前架构风险与技术债

- 当前完整测试套件并不全绿，部分测试仍引用已移除的派生量与旧映射假设。
- BLF/MDF/MF4 总线解码仍缺少足够真实工程样本回归。
- GUI 功能很多，但还没有人工复核闭环。
- 文档刚完成系统性梳理，后续若再改工作流，必须同步维护 IMPLEMENTATION_LOGIC 与 ENTRYPOINTS。

## 7. 当前推荐演进方向

1. 先把测试基线修回与当前代码一致。
2. 再补真实样本回归，尤其是 DBC 解码链路。
3. 然后再进入人工复核、标记和更复杂交互能力。
