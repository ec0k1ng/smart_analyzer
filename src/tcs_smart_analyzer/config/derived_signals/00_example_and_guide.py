GUIDE_TEXT = '''派生量示例与详细讲解

用途：
1. 这是 UI 下拉菜单中的第一个选项，用于给用户查看派生量格式。
2. 这不是实际执行派生量，分析引擎会自动跳过该文件。
3. 派生量用于承载多个 KPI 共用、且希望只计算一次的中间序列。

给 AI 的格式化要求：
请为 TCS Smart Analyzer 生成一个派生量 Python 文件，严格按下面格式输出，不要解释：

from __future__ import annotations

IS_TEMPLATE = False

import pandas as pd

DERIVED_SIGNAL_DEFINITION = {
    "name": "唯一派生量名称，例如 slip_kph。必须使用英文，因为它会作为信号名参与依赖声明、绘图和计算引用",
    "title": "派生量标题。请使用中文，供界面标签、下拉框和结果说明展示",
    "raw_inputs": [
        "time_s",  # 示例：时间轴，单位 s
        "vehicle_speed_kph",  # 示例：车速，单位 kph
    ],
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
- raw_inputs 里的标准输入名称应带单位，例如 vehicle_speed_kph、yaw_rate_degps；布尔状态量保持语义名即可。
- raw_inputs 建议逐行书写并在右侧补注释，明确物理意义与单位，避免接口映射和算法理解歧义。
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
- 当前清单中的每一行都已压缩展示；连字符后面的说明优先取算法概述，没有算法概述时才回退到 description。
- 如果某个派生量只在局部工况下有业务意义，建议在 description 和 algorithm_summary 里写清楚非有效区间是返回 0.0、保持上一值、NaN 还是其它占位值；这不是硬编码格式要求，但最好提前讲明，避免曲线含义不清。

当前可用派生量清单：
1. abs_target_slip_kph - ABS全局目标打滑量 - 对所有 ABS 激活区间内的 -|slip_kph| 按时间差做加权平均，输出负值目标打滑量标量。
2. slip_kph - 打滑量 - 按车速符号统一前进/倒车工况，对每个车轮计算 (wheel_speed_kph - vehicle_speed_kph) * sign(vehicle_speed_kph)，再按每个时刻绝对值最大的车轮输出该车轮打滑量。
3. tcs_target_slip_kph - TCS全局目标打滑量 - 对所有 TCS 激活区间内的 |slip_kph| 按时间差做加权平均，输出单个目标打滑量标量。

当前接口映射表中的标准输入量：
1. time_s - 时间轴，单位 s，必须配置且固定排在第一行。
2. abs_active_fl - 左前轮 ABS 激活标志，布尔/0-1。
3. abs_active_fr - 右前轮 ABS 激活标志，布尔/0-1。
4. abs_active_rl - 左后轮 ABS 激活标志，布尔/0-1。
5. abs_active_rr - 右后轮 ABS 激活标志，布尔/0-1。
6. accel_pedal_pct - 油门开度，单位 %。
7. brake_depth_pct - 制动深度，单位 %。
8. longitudinal_accel_mps2 - 纵向加速度，单位 m/s^2。
9. steering_wheel_angle_deg - 方向盘转角，单位 deg。
10. tcs_active_fl - 左前轮 TCS 激活标志，布尔/0-1。
11. tcs_active_fr - 右前轮 TCS 激活标志，布尔/0-1。
12. tcs_active_rl - 左后轮 TCS 激活标志，布尔/0-1。
13. tcs_active_rr - 右后轮 TCS 激活标志，布尔/0-1。
14. vehicle_speed_kph - 车速，单位 kph。
15. wheel_speed_fl_kph - 左前轮轮速，单位 kph。
16. wheel_speed_fr_kph - 右前轮轮速，单位 kph。
17. wheel_speed_rl_kph - 左后轮轮速，单位 kph。
18. wheel_speed_rr_kph - 右后轮轮速，单位 kph。
19. yaw_rate_degps - 横摆角速度，单位 deg/s。
'''

IS_TEMPLATE = True
