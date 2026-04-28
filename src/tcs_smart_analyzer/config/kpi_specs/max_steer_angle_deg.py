from __future__ import annotations

IS_TEMPLATE = False

import pandas as pd


KPI_DEFINITION = {
    "name": "max_steer_angle_deg",
    "title": "最大方向盘转角绝对值",
    "raw_inputs": [
        "steering_wheel_angle_deg",  # 方向盘转角，单位 deg
    ],
    "derived_inputs": [],
    "trend_source": "max_steer_angle_deg",
    "unit": "deg",
    "description": "全程方向盘转角绝对值的最大值。",
    "algorithm_summary": "对 steering_wheel_angle_deg 取绝对值后求全程最大值；趋势输出为累计最大绝对值。",
    "threshold": 15.0,
    "source": "用户要求默认限值",
    "pass_condition": "value <= threshold",
    "rule_description": "最大方向盘转角绝对值应不大于 15 deg。",
    "pass_message": "方向盘转角达标。",
    "fail_message": "方向盘转角超限。",
}

CALIBRATION = {}


def calculate_kpi(dataframe):
    return float(pd.to_numeric(dataframe["steering_wheel_angle_deg"], errors="coerce").abs().max())


def calculate_kpi_series(dataframe):
    return pd.to_numeric(dataframe["steering_wheel_angle_deg"], errors="coerce").abs().cummax()