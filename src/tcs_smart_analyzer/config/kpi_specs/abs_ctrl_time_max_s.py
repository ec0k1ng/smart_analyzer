from __future__ import annotations

IS_TEMPLATE = False

import numpy as np
import pandas as pd


KPI_DEFINITION = {
    "name": "abs_ctrl_time_max_s",
    "title": "ABS最大控滑时间",
    "raw_inputs": [
        "time_s",  # 时间轴，单位 s
        "abs_active_fl",  # 左前轮ABS激活标志
        "abs_active_fr",  # 右前轮ABS激活标志
        "abs_active_rl",  # 左后轮ABS激活标志
        "abs_active_rr",  # 右后轮ABS激活标志
    ],
    "derived_inputs": ["slip_kph", "abs_target_slip_kph"],
    "trend_source": "abs_ctrl_time_max_s",
    "unit": "s",
    "description": "ABS 单次激活后，从激活开始到绝对打滑量稳定进入目标带内的最大时长。",
    "algorithm_summary": "逐段扫描 ABS 激活区间，比较 |slip_kph| 与目标打滑量加容差的稳定带，找到首次持续保持稳定的时刻作为该段控滑时间，再取各段最大值。",
    "threshold": 1.5,
    "source": "ABS标定规范默认限值",
    "pass_condition": "value <= threshold",
    "rule_description": "所有 ABS 激活事件中，控滑时间最大值应不超过 1.5 s。",
    "pass_message": "ABS 最大控滑时间达标。",
    "fail_message": "ABS 最大控滑时间超标。",
}

CALIBRATION = {
    "stability_tolerance_kph": 1.0,  # 稳定带容差
    "stable_hold_duration_s": 0.1,  # 进入目标带后的保持时长
}


def calculate_kpi(dataframe):
    series = calculate_kpi_series(dataframe)
    if series.empty or series.isna().all():
        return float("nan")
    return float(series.max())


def calculate_kpi_series(dataframe):
    target_column = "abs_target_slip_kph"
    if target_column not in dataframe.columns or "slip_kph" not in dataframe.columns or "time_s" not in dataframe.columns:
        return pd.Series(np.nan, index=dataframe.index, dtype=float)
    target_slip = float(dataframe[target_column].iloc[0]) if len(dataframe) > 0 else np.nan
    if np.isnan(target_slip):
        return pd.Series(np.nan, index=dataframe.index, dtype=float)

    active_columns = [column_name for column_name in ["abs_active_fl", "abs_active_fr", "abs_active_rl", "abs_active_rr"] if column_name in dataframe.columns]
    if not active_columns:
        return pd.Series(np.nan, index=dataframe.index, dtype=float)

    active_mask = dataframe[active_columns].any(axis=1).astype(bool).values
    time_s = pd.to_numeric(dataframe["time_s"], errors="coerce").values
    slip = pd.to_numeric(dataframe["slip_kph"], errors="coerce").abs().values
    active_diff = np.diff(active_mask.astype(int), prepend=0)
    starts = np.where(active_diff == 1)[0]
    ends = np.where(active_diff == -1)[0]
    if active_mask[-1]:
        ends = np.append(ends, len(active_mask))

    result = np.zeros(len(dataframe), dtype=float)
    stable_upper = abs(target_slip) + CALIBRATION["stability_tolerance_kph"]
    hold_duration = CALIBRATION["stable_hold_duration_s"]
    for start, end in zip(starts[: len(ends)], ends[: len(starts)]):
        if end <= start:
            continue
        seg_time = time_s[start:end]
        seg_slip = slip[start:end]
        rel_time = seg_time - seg_time[0]
        control_time = rel_time[-1]
        for index, slip_value in enumerate(seg_slip):
            if np.isnan(slip_value) or slip_value > stable_upper:
                continue
            hold_end_time = seg_time[index] + hold_duration
            hold_mask = (seg_time >= seg_time[index]) & (seg_time <= hold_end_time)
            if np.all(seg_slip[hold_mask] <= stable_upper):
                control_time = rel_time[index]
                break
        result[start:end] = np.minimum(rel_time, control_time)
    return pd.Series(result, index=dataframe.index, dtype=float)