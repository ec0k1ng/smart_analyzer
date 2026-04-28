from __future__ import annotations

IS_TEMPLATE = False

import numpy as np
import pandas as pd


KPI_DEFINITION = {
    "name": "mean_full_brake_decel_mps2",
    "title": "全制动平均纵向减速度",
    "raw_inputs": [
        "brake_depth_pct",  # 制动深度，单位 %
        "longitudinal_accel_mps2",  # 纵向加速度，单位 m/s^2
    ],
    "derived_inputs": [],
    "trend_source": "mean_full_brake_decel_mps2",
    "unit": "m/s^2",
    "description": "全制动期间的平均纵向减速度，输出值保持为负。",
    "algorithm_summary": "用制动深度阈值筛出全制动样本，对这些样本的 longitudinal_accel_mps2 求平均；结果保持纵向减速度的负值，趋势输出为全制动样本的累计平均值。",
    "threshold": -4.0,
    "source": "用户要求默认限值",
    "pass_condition": "value <= threshold",
    "rule_description": "全制动过程期间的平均纵向减速度应不高于 -4 m/s^2。",
    "pass_message": "全制动平均纵向减速度达标。",
    "fail_message": "全制动平均纵向减速度不足。",
}

CALIBRATION = {
    "full_brake_depth_threshold_pct": 90.0,
}


def _full_brake_mask(dataframe):
    brake_depth = pd.to_numeric(dataframe["brake_depth_pct"], errors="coerce")
    return brake_depth >= CALIBRATION["full_brake_depth_threshold_pct"]


def calculate_kpi(dataframe):
    accel = pd.to_numeric(dataframe["longitudinal_accel_mps2"], errors="coerce")
    mask = _full_brake_mask(dataframe)
    if not mask.any():
        return float("nan")
    return float(accel[mask].mean())


def calculate_kpi_series(dataframe):
    accel = pd.to_numeric(dataframe["longitudinal_accel_mps2"], errors="coerce")
    mask = _full_brake_mask(dataframe)
    selected_accel = accel.where(mask, 0.0)
    running_sum = selected_accel.cumsum()
    running_count = mask.astype(int).cumsum().replace(0, np.nan)
    return running_sum / running_count