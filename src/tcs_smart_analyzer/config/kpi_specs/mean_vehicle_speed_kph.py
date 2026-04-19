from __future__ import annotations

IS_TEMPLATE = False

import pandas as pd


KPI_DEFINITION = {
    "name": "mean_vehicle_speed_kph",
    "title": "平均车速",
    "raw_inputs": ["vehicle_speed"],
    "derived_inputs": [],
    "trend_source": "mean_vehicle_speed_kph",
    "unit": "kph",
    "description": "平均车速",
    "threshold": 0.0,
    "source": "reference_only",
    "pass_condition": "True",
    "rule_description": "该项为试验背景信息，不单独设置达标阈值。",
    "pass_message": "背景指标，仅供参考",
    "fail_message": "背景指标，仅供参考",
}

CALIBRATION = {
    "missing_speed_fill_value_kph": 0.0,  # 均值过程曲线中车速缺失时的补充值
}


def calculate_kpi(dataframe):
    return float(dataframe["vehicle_speed"].mean()) if not dataframe.empty else 0.0


def calculate_kpi_series(dataframe):
    if dataframe.empty:
        return pd.Series(dtype=float)
    vehicle_speed = pd.to_numeric(dataframe["vehicle_speed"], errors="coerce")
    sample_index = pd.Series(range(1, len(vehicle_speed) + 1), index=vehicle_speed.index, dtype=float)
    return vehicle_speed.fillna(CALIBRATION["missing_speed_fill_value_kph"]).cumsum() / sample_index
