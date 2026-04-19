GUIDE_TEXT = """KPI 示例与详细讲解

用途：
1. 这是 UI 下拉菜单中的第一个选项，用于给用户查看新版 KPI 格式。
2. 这不是实际执行 KPI，分析引擎会自动跳过该文件。
3. 现在不再单独维护规则文件。每一项 KPI 自己同时定义“数值如何算”和“结果如何判定”。

当前可用派生量清单：
1. slip_ratio
   描述：四轮最大打滑率，驱动打滑恒为正，制动打滑恒为负，自动适应前进/倒车工况。
   算法概述：以|vehicle_speed|为参考（下限0.5 kph），计算各轮(wheel_speed - vehicle_speed) / |vehicle_speed|，并根据车速符号对结果取同号修正：当vehicle_speed<0时，结果乘以-1，确保驱动打滑始终为正，制动打滑始终为负。取四轮绝对值最大值后还原符号。

2. tcs_target_slip_ratio_global
   描述：整个数据文件中所有TCS激活期间的时间加权平均打滑率，作为该数据文件的固有属性。全时段以恒定直线显示，供KPI作为稳定目标。
   算法概述：以四个TCS激活标志的逻辑或确定激活区间；收集所有激活区间内的 slip_ratio 与时间差，计算全局时间加权平均值；返回一个与数据等长的序列，每个元素均为该全局平均值。若缺失必要信号则返回全NaN。

给 AI 的格式化要求：
请为 TCS Smart Analyzer 生成一个 KPI Python 文件，严格按下面格式输出，不要解释：

from __future__ import annotations

IS_TEMPLATE = False

KPI_DEFINITION = {
    "name": "唯一KPI名称，例如 peak_slip_ratio。必须使用英文，因为它会作为KPI信号名参与依赖、绘图和结果索引",
    "title": "KPI标题。请使用中文，供界面标签、结果表和报告展示",
    "raw_inputs": ["这里列出 KPI 自己直接依赖的标准输入信号名"],
    "derived_inputs": ["如果依赖派生量，在这里列出，例如 slip_ratio"],
    "trend_source": "必须与 name 完全一致，例如 peak_slip_ratio。曲线界面的 KPI 信号只认 KPI 自己的 name",
    "unit": "单位",
    "description": "说明这个 KPI 算出来代表什么",
    "threshold": 0.0,
    "source": "阈值来源说明",
    "pass_condition": "value <= threshold",
    "rule_description": "说明该 KPI 需要满足什么条件才算达标",
    "pass_message": "该 KPI 达标时显示的话",
    "fail_message": "该 KPI 未达标时显示的话",
}

CALIBRATION = {
    "calibration_name": 0.0,  # 所有可调标定量统一集中在这里；请使用 snake_case，并在右侧写清楚注释
}

def calculate_kpi(dataframe):
    return 0.0

def calculate_kpi_series(dataframe):
    return dataframe["某个连续过程序列"]

说明：
- 对用户来说，raw_inputs 是唯一需要维护的输入声明；接口映射表第一列会自动由所有 KPI 和派生量的 raw_inputs 汇总同步，不需要再额外维护另一份“必需信号清单”。
- calculate_kpi(dataframe)：功能实现字段，负责用 Python 算出 KPI 数值。
- calculate_kpi_series(dataframe)：必填字段，必须返回与数据长度一致的连续过程曲线，供曲线界面实时检查 KPI 算法过程和峰值位置。
- 不要输出 DISPLAY_NAME，也不要把用户新建 KPI 文件写成 IS_TEMPLATE = True；这两个字段只属于系统示例文件，不属于实际 KPI 定义。
- 如果多个 KPI 共用同一个中间量，应优先把它抽成派生量，并在 derived_inputs 中显式声明依赖。
- 如果某个中间量只被当前 KPI 使用，也可以继续直接写在 KPI 文件内，保持算法透明可改。
- trend_source 不是可选项，必须填写为 KPI_DEFINITION["name"] 本身；曲线界面展示 KPI 过程时，读取的是 KPI 名称对应的连续序列。
- 如果想在曲线里看到 RMS 包络、累计最大值、滑窗结果等过程，就应在 calculate_kpi_series 中直接返回该过程序列；不要把 trend_source 写成其它临时列名。
- 所有可调算法参数都应集中放在 CALIBRATION 区块，放在 KPI_DEFINITION 之后、函数之前；不要把标定量零散写在文件顶部和函数内部。
- CALIBRATION 里的键名请使用 snake_case，并尽量把物理意义、工况或单位写进名字；每个条目右侧都要写中文注释。
- pass_condition：通过判断字段，使用 Python 表达式；可直接引用 value、threshold、dataframe、np、pd、math、source_path、source_name、source_stem、analysis_profile、generated_at、mapped_columns。
- rule_description：展示给工程人员看的规则描述。
- dataframe 是标准化后的分析数据表，里面既包含原始标准信号，也包含当前分析所需、已经按依赖顺序算好的派生量。
- dataframe.attrs["source_name"]：当前分析文件名，例如 demo.csv。
- dataframe.attrs["source_stem"]：当前分析文件名去掉扩展名后的值，例如 demo。
- dataframe.attrs["source_path"]：当前分析文件绝对路径字符串。
- dataframe.attrs["analysis_profile"]：当前分析配置名称。
- dataframe.attrs["generated_at"]：本次分析生成时间。
- dataframe.attrs["mapped_columns"]：标准信号到实际信号名的映射字典。
- 若你要让 AI 同时设计 KPI 与报告模板，还要明确告诉它：报告模板阶段可额外使用 report_title、metadata、kpis、rules、results、files、file_count 等变量。
- raw_inputs 会自动进入接口映射 Excel 第一列来源统计，所以一定要写全。
- derived_inputs 不会直接参与接口映射，但它引用的派生量 raw_inputs 也会自动进入接口映射来源统计。
"""

IS_TEMPLATE = True
