from __future__ import annotations

IS_TEMPLATE = False

import pandas as pd


KPI_DEFINITION = {
    "name": "max_yaw_rate_degps",
    "title": "最大横摆角速度绝对值",
    "raw_inputs": [
        "yaw_rate_degps",  # 横摆角速度，单位 deg/s
    ],
    "derived_inputs": [],
    "trend_source": "max_yaw_rate_degps",
    "unit": "deg/s",
    "description": "全程横摆角速度绝对值的最大值。",
    "algorithm_summary": "对 yaw_rate_degps 取绝对值后求全程最大值；趋势输出为累计最大绝对值。",
    "threshold": 5.0,
    "source": "用户要求默认限值",
    "pass_condition": "value <= threshold",
    "rule_description": "最大横摆角速度绝对值应不大于 5 deg/s。",
    "pass_message": "横摆角速度达标。",
    "fail_message": "横摆角速度超限。",
}

CALIBRATION = {}


def calculate_kpi(dataframe):
    return float(pd.to_numeric(dataframe["yaw_rate_degps"], errors="coerce").abs().max())


def calculate_kpi_series(dataframe):
    return pd.to_numeric(dataframe["yaw_rate_degps"], errors="coerce").abs().cummax()