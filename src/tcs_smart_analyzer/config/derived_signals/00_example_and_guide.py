GUIDE_TEXT = '''派生量示例与详细讲解

用途：
1. 这是 UI 下拉菜单中的第一个选项，用于给用户查看派生量格式。
2. 这不是实际执行派生量，分析引擎会自动跳过该文件。
3. 派生量用于承载多个 KPI 共用、且希望只计算一次的中间序列。

当前可用派生量清单：
1. slip_ratio
   描述：四轮最大打滑率，驱动打滑恒为正，制动打滑恒为负，自动适应前进/倒车工况。
   算法概述：以|vehicle_speed|为参考（下限0.5 kph），计算各轮(wheel_speed - vehicle_speed) / |vehicle_speed|，并根据车速符号对结果取同号修正：当vehicle_speed<0时，结果乘以-1，确保驱动打滑始终为正，制动打滑始终为负。取四轮绝对值最大值后还原符号。

2. tcs_target_slip_ratio_global
   描述：整个数据文件中所有TCS激活期间的时间加权平均打滑率，作为该数据文件的固有属性。全时段以恒定直线显示，供KPI作为稳定目标。
   算法概述：以四个TCS激活标志的逻辑或确定激活区间；收集所有激活区间内的 slip_ratio 与时间差，计算全局时间加权平均值；返回一个与数据等长的序列，每个元素均为该全局平均值。若缺失必要信号则返回全NaN。

给 AI 的格式化要求：
请为 TCS Smart Analyzer 生成一个派生量 Python 文件，严格按下面格式输出，不要解释：

from __future__ import annotations

IS_TEMPLATE = False

import pandas as pd

DERIVED_SIGNAL_DEFINITION = {
    "name": "唯一派生量名称，例如 slip_ratio。必须使用英文，因为它会作为信号名参与依赖声明、绘图和计算引用",
    "title": "派生量标题。请使用中文，供界面标签、下拉框和结果说明展示",
    "raw_inputs": ["这里列出直接依赖的标准输入信号名"],
    "derived_inputs": ["如果依赖其他派生量，在这里列出，可为空"],
    "description": "说明这个派生量代表什么，以及哪些 KPI 会复用它",
    "algorithm_summary": "用文字概述算法思路、关键公式和边界处理方式",
}

CALIBRATION = {
    "calibration_name": 0.0,  # 所有可调标定量统一集中在这里；请使用 snake_case，并在右侧写清楚注释
}

def calculate_signal(dataframe):
    return pd.Series(...)

说明：
- 对用户来说，raw_inputs 就是唯一需要维护的输入声明；接口映射表第一列会自动由所有 KPI 和派生量的 raw_inputs 汇总同步，不需要再额外维护另一份“必需信号清单”。
- 派生量通常应输出一个与数据长度一致、随时间连续变化的过程曲线；只有当该量明确表示“整个文件的固有标量属性”时，才允许返回全时段同一数值的水平直线。
- 如果你认为派生量应该输出水平直线，必须先和用户确认它到底是“单值标量属性”还是“实时连续变化量”；未确认前不允许自作主张。
- calculate_signal(dataframe) 必须返回一个与数据长度一致的序列，曲线界面会直接按 DERIVED_SIGNAL_DEFINITION["name"] 显示这条派生量曲线。
- 和 KPI 不同，派生量不需要 trend_source，也不需要额外再写一个 calculate_kpi_series；calculate_signal(dataframe) 的返回值本身就是曲线来源。
- 派生量没有单独的 trend_source 字段；它写回分析数据表后的列名，就是 DERIVED_SIGNAL_DEFINITION["name"] 本身，所以 name 必须稳定、唯一、可直接用于绘图。
- 派生量只负责输出一个与数据长度一致的序列，供多个 KPI 复用。
- 派生量会在单个文件分析过程中只计算一次，然后写回分析数据表。
- 如果多个 KPI 共用一个中间量，应优先建派生量，不要在多个 KPI 文件里重复算。
- raw_inputs 会自动进入接口映射 Excel 第一列来源统计，所以一定要写全。
- derived_inputs 用于声明派生量之间的依赖，分析引擎会按依赖顺序自动计算。
- 所有可调算法参数都应集中放在 CALIBRATION 区块，放在定义区后、函数前；不要把标定量零散写在文件各处。
- CALIBRATION 里的键名请使用 snake_case，并尽量把物理意义、工况或单位写进名字；每个条目右侧都要写中文注释。
- 如果派生量依赖其他派生量，请把被依赖项完整写进 derived_inputs，格式与 KPI 文件中的 derived_inputs 保持一致。
- 如果某个派生量只在局部工况下有业务意义，建议在 description 和 algorithm_summary 里写清楚非有效区间是返回 0.0、保持上一值、NaN 还是其它占位值；这不是硬编码格式要求，但最好提前讲明，避免曲线含义不清。
'''

IS_TEMPLATE = True
