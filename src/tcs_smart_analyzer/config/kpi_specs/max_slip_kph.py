from __future__ import annotations

IS_TEMPLATE = False

import pandas as pd


KPI_DEFINITION = {
    "name": "max_slip_kph",
    "title": "最大打滑量",
    "raw_inputs": [],
    "derived_inputs": ["slip_kph"],
    "trend_source": "max_slip_kph",
    "unit": "kph",
    "description": "全程绝对打滑量的最大值。",
    "algorithm_summary": "对 slip_kph 取绝对值后求全程最大值；趋势输出为绝对打滑量的累计最大值。",
    "threshold": 30.0,
    "source": "工程标定经验值",
    "pass_condition": "value <= threshold",
    "rule_description": "最大打滑量应不大于 30 kph。",
    "pass_message": "最大打滑量在限值内。",
    "fail_message": "最大打滑量超限。",
}

CALIBRATION = {}


def calculate_kpi(dataframe):
    if "slip_kph" not in dataframe.columns:
        return float("nan")
    return float(pd.to_numeric(dataframe["slip_kph"], errors="coerce").abs().max())


def calculate_kpi_series(dataframe):
    if "slip_kph" not in dataframe.columns:
        return pd.Series(float("nan"), index=dataframe.index, dtype=float)
    return pd.to_numeric(dataframe["slip_kph"], errors="coerce").abs().cummax()