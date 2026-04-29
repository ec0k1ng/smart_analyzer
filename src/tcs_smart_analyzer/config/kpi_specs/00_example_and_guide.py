GUIDE_TEXT = """KPI 示例与详细讲解

用途：
1. 这是 UI 下拉菜单中的第一个选项，用于给用户查看新版 KPI 格式。
2. 这不是实际执行 KPI，分析引擎会自动跳过该文件。
3. 现在不再单独维护规则文件。每一项 KPI 自己同时定义“数值如何算”和“结果如何判定”。

给 AI 的格式化要求：
请为 TCS Smart Analyzer 生成一个 KPI Python 文件，严格按下面格式输出，不要解释：

from __future__ import annotations

IS_TEMPLATE = False

KPI_DEFINITION = {
    "name": "唯一KPI名称，例如 max_slip_kph。必须使用英文，因为它会作为KPI信号名参与依赖、绘图和结果索引",
    "title": "KPI标题。请使用中文，供界面标签、结果表和报告展示",
    "raw_inputs": [
        "time_s",  # 示例：时间轴，单位 s
        "vehicle_speed_kph",  # 示例：车速，单位 kph
    ],
    "derived_inputs": ["如果依赖派生量，在这里列出，例如 slip_kph"],
    "trend_source": "必须与 name 完全一致，例如 max_slip_kph。曲线界面的 KPI 信号只认 KPI 自己的 name",
    "unit": "单位",
    "description": "说明这个 KPI 算出来代表什么",
    "algorithm_summary": "用文字概述算法思路、关键公式和边界处理方式",
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
- raw_inputs 里的标准输入名称应带单位，例如 vehicle_speed_kph、wheel_speed_fl_kph、yaw_rate_degps。
- raw_inputs 建议逐行书写并在右侧补注释，明确物理意义与单位。
- calculate_kpi(dataframe)：功能实现字段，负责用 Python 算出 KPI 数值。
- calculate_kpi_series(dataframe)：必填字段，必须返回与数据长度一致的连续过程曲线，供曲线界面实时检查 KPI 算法过程和峰值位置。
- algorithm_summary：必填字段，用一句到几句中文讲清楚算法核心逻辑、关键公式和边界处理。
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
- 当前清单中的每一行都已压缩展示；连字符后面的说明优先取算法概述，没有算法概述时才回退到 description。
- derived_inputs 不会直接参与接口映射，但它引用的派生量 raw_inputs 也会自动进入接口映射来源统计。

当前可用派生量清单：
1. abs_target_slip_kph - ABS全局目标打滑量 - 对所有 ABS 激活区间内的 -|slip_kph| 按时间差做加权平均，输出负值目标打滑量标量。
2. slip_kph - 打滑量 - 按车速符号统一前进/倒车工况，对每个车轮计算 (wheel_speed_kph - vehicle_speed_kph) * sign(vehicle_speed_kph)，再按每个时刻绝对值最大的车轮输出该车轮打滑量。
3. tcs_target_slip_kph - TCS全局目标打滑量 - 对所有 TCS 激活区间内的 |slip_kph| 按时间差做加权平均，输出单个目标打滑量标量。

当前接口映射表中的标准输入量：
1. time_s - 时间轴，单位 s。
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
"""

IS_TEMPLATE = True
