from __future__ import annotations

IS_TEMPLATE = False

import numpy as np
import pandas as pd


KPI_DEFINITION = {
    "name": "mean_full_throttle_accel_mps2",
    "title": "全油门平均纵向加速度",
    "raw_inputs": [
        "accel_pedal_pct",  # 油门开度，单位 %
        "longitudinal_accel_mps2",  # 纵向加速度，单位 m/s^2
    ],
    "derived_inputs": [],
    "trend_source": "mean_full_throttle_accel_mps2",
    "unit": "m/s^2",
    "description": "油门开度大于阈值期间的平均纵向加速度。",
    "algorithm_summary": "用油门开度阈值筛出全油门样本，对这些样本的 longitudinal_accel_mps2 求平均；趋势输出为全油门样本的累计平均值。",
    "threshold": 4.0,
    "source": "用户要求默认限值",
    "pass_condition": "value >= threshold",
    "rule_description": "全油门过程期间的平均纵向加速度应不小于 4 m/s^2。",
    "pass_message": "全油门平均纵向加速度达标。",
    "fail_message": "全油门平均纵向加速度不足。",
}

CALIBRATION = {
    "full_throttle_threshold_pct": 90.0,  # 认定为全油门的开度阈值
}


def _full_throttle_mask(dataframe):
    pedal = pd.to_numeric(dataframe["accel_pedal_pct"], errors="coerce")
    return pedal >= CALIBRATION["full_throttle_threshold_pct"]


def calculate_kpi(dataframe):
    accel = pd.to_numeric(dataframe["longitudinal_accel_mps2"], errors="coerce")
    mask = _full_throttle_mask(dataframe)
    if not mask.any():
        return float("nan")
    return float(accel[mask].mean())


def calculate_kpi_series(dataframe):
    accel = pd.to_numeric(dataframe["longitudinal_accel_mps2"], errors="coerce")
    mask = _full_throttle_mask(dataframe)
    selected_accel = accel.where(mask, 0.0)
    running_sum = selected_accel.cumsum()
    running_count = mask.astype(int).cumsum().replace(0, np.nan)
    return running_sum / running_count