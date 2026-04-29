# TCS Smart Analyzer 当前实现逻辑说明

## 1. 这份文档的用途

ARCHITECTURE 解释模块边界，这份文档解释“系统现在实际上怎么跑”。

如果你要接手当前项目，这份文档应该回答下面这些问题：

1. 分析一份文件时，运行链路具体怎么走
2. GUI 每个页面当前到底能做什么
3. 用户需要理解哪些配置概念
4. 当前哪些行为是强约束，哪些只是建议

## 2. 单文件分析运行链路

主入口在 src/tcs_smart_analyzer/core/engine.py 的 AnalysisEngine.analyze_file()。

当前真实顺序如下：

1. 同步接口映射文件
2. 读取原始日志文件为 DataFrame；BLF/ASC 会带着当前需要的实际信号名进入按需解码路径，表格类列名会在加载出口统一清理协议尾缀
3. 向 dataframe.attrs 写入 source_path、source_name、source_stem、analysis_profile、generated_at
4. 根据当前 required_raw_input_signals 构建信号映射
5. 标准化原始信号
6. 按派生量依赖顺序计算派生量并写回 normalized_frame
7. 计算所有 KPI 的单值结果与过程曲线
8. 将 KPI 过程曲线写回 normalized_frame 供曲线页使用
9. 基于 KPI_DEFINITION 生成 rule_results
10. 封装为 AnalysisResult 返回给 GUI 或 CLI

## 3. 接口映射逻辑

### 3.1 用户必须知道的事实

- 系统映射表第一列是 raw_input_name，不是 standard_signal。
- 这一列由程序自动汇总，不是用户手工维护。
- 用户只需要填写 actual_signal_name_1..5。
- 当前不再存在 signal_aliases 这种用户需要理解的概念。

### 3.2 系统表结构

- A 列：raw_input_name
- B 列：from
- C-G 列：actual_signal_name_1..5

其中：

- from 是只读列
- 系统行缺参校验从 C 列开始
- 只要 C-G 全空，该行就应立即标红

### 3.3 匹配行为

当前 build_signal_mapping() 会按接口映射表中用户填写的实际信号名逐列匹配原始数据列。文档中不应再把“自动猜测别名”写成主行为。

当前还要注意两点：

- DAT/文本类列名会先去掉类似 \XCP: 1 这类协议尾缀，再进入后续匹配。
- BLF/ASC 总线日志不会再默认解出全部 DBC 信号，而是优先解出当前分析真正需要的候选信号。

## 4. 派生量逻辑

### 4.1 当前定义格式

一个正式派生量文件至少包括：

- DERIVED_SIGNAL_DEFINITION
- CALIBRATION
- calculate_signal(dataframe)

DERIVED_SIGNAL_DEFINITION 中当前重点字段：

- name
- title
- raw_inputs
- derived_inputs
- description
- algorithm_summary

### 4.2 当前行为约束

- 派生量没有 trend_source。
- 派生量写回数据表后的列名就是它自己的 name。
- 曲线页显示派生量时，直接画 calculate_signal() 的返回序列。
- 多个 KPI 共用的中间量应该优先实现为派生量。

### 4.3 连续曲线与水平直线

当前模板约束已经明确：

- 派生量通常输出连续变化曲线。
- 只有当该量明确表达“整个文件的固有标量属性”时，才允许输出全时段恒定的水平直线。
- 未经用户确认，不允许 AI 自作主张把派生量写成水平直线语义。

## 5. KPI 逻辑

### 5.1 当前定义格式

一个正式 KPI 文件至少包括：

- KPI_DEFINITION
- CALIBRATION
- calculate_kpi(dataframe)
- calculate_kpi_series(dataframe)

KPI_DEFINITION 当前重点字段：

- name
- title
- raw_inputs
- derived_inputs
- trend_source
- threshold
- pass_condition
- rule_description
- pass_message
- fail_message

### 5.2 当前硬约束

- trend_source 必须等于 name。
- calculate_kpi_series 是硬约束。
- 曲线页中的 KPI 信号按 KPI name 组织。
- 需要调整的算法参数必须集中写在 CALIBRATION 区块。

### 5.3 规则结果如何生成

当前没有独立 rule_specs 执行链。系统会根据 KPI 结果和 KPI_DEFINITION 中的判定字段自动构造规则结果。

因此当前“规则”对用户的真实含义是：KPI 的判定层。

## 6. GUI 逻辑

### 6.1 主页 / 队列页

当前主页承担四类任务：

1. 选择 KPI 分组并把文件加入队列
2. 管理 DBC 列表
3. 发起分析
4. 查看运行日志

运行日志当前应主要承载：

- 分析结果
- 导出文件路径
- 报错与跳转
- KPI/派生量中的 print 输出

当前已增加：

- 清空按钮
- 每次分析自动清空
- 操作噪音过滤

当前结果生命周期约束：

- 新一轮分析开始时会清空上一轮结果，但保留当前文件队列。
- 结果页和曲线页不应继续展示上一轮分析残留结果。

### 6.2 结果页

结果页当前按“分组标题 -> 文件标题 -> KPI 行”展示。

结果唯一键不是单纯文件路径，而是：

- 文件路径
- KPI 分组

因此同一个文件可以在不同 KPI 分组下并存多套结果。

### 6.3 曲线页

曲线页当前支持：

- 多面板
- 多信号显示
- 横轴联动缩放
- 新增空白面板
- 信号搜索
- 多选拖拽
- 跨面板拖拽转移
- 面板配置自动记忆

当前曲线信号来源分四类：

- 接口信号
- KPI 信号
- 派生量信号
- 自定义信号

当前关键交互约束：

- 新增面板默认应为空，不再自动带默认信号。
- 所有横轴缩放动作都必须保持所有面板 X 轴一致。
- 同一真实文件如果在多个 KPI 分组下执行过，曲线页会聚合展示这些分组产生的 KPI 信号并取并集。
- 曲线缓存当前按结果实例隔离，而不是仅按真实文件路径隔离。
- 曲线布局收尾当前会延后到事件循环下一拍执行，避免在控件尚不可见或尺寸未稳定时提前锁定 plot area。
- 主标签页切到“曲线”时，会主动再次触发 refresh_chart_panels，确保分析在隐藏页完成后首次显示也能正确完成布局。
- 当前曲线页已加入共享光标覆盖层，贯穿所有子框显示统一的光标线。

### 6.4 配置工作台

当前配置工作台至少包括：

- 派生量编辑
- KPI 编辑
- KPI 分组编辑
- 接口映射编辑
- 模板编辑

当前编辑器共同行为：

- Ctrl+S 保存
- Ctrl+F 查找替换
- 未保存星标
- 切换前拦截确认
- 跳转后关键行高亮

当前特殊行为：

- KPI 编辑器双击 derived_inputs 可跳到派生量文件
- KPI 分组页双击 KPI 名称可跳到 KPI 文件
- 接口映射表双击 From 可跳到定义文件
- KPI/派生量编辑器会高亮关键配置行
- CALIBRATION 区块已被纳入高亮范围

## 7. 导出逻辑

当前面向用户的导出只保留：

- HTML 汇总报告
- Word 汇总报告

HTML 与 Word 结构应与结果页一致，且都按分组和文件组织 KPI 行。

## 8. 当前实际插件清单

### 8.1 派生量

- slip_ratio
- tcs_target_slip_ratio_global

当前仓库中已经没有 tcs_active_avg_slip_ratio 正式文件，因此文档、测试和 guide 都不能再把它当作当前存在的派生量。

### 8.2 KPI

- peak_slip_ratio
- max_jerk_mps3
- max_slip_speed
- mean_vehicle_speed_kph
- new_kpi
- new_kpi_1

其中 new_kpi / new_kpi_1 属于用户新增或草稿性质示例，但当前确实会被当作正式 KPI 载入。

## 9. 当前最容易误判的地方

- 误以为系统仍依赖 signal_aliases 自动猜列
- 误以为 rule_specs 目录仍参与执行
- 误以为 trend_source 可以写成任意临时列名
- 误以为派生量可以不写 algorithm_summary 或 CALIBRATION
- 误以为完整测试套件当前是全绿

## 10. 这份文档更新时机

只要以下任一行为发生变化，就必须同步更新本文件：

- 主分析顺序变化
- GUI 页面功能变化
- 编辑器跳转/高亮/保存机制变化
- 曲线拖拽与多面板行为变化
- 接口映射模型变化
- KPI/派生量合同约束变化
