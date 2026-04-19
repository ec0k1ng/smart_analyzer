from __future__ import annotations

IS_TEMPLATE = False

import numpy as np
import pandas as pd

KPI_DEFINITION = {
    "name": "tcs_max_control_time",
    "title": "TCS最大控滑时间",
    "raw_inputs": ["tcs_active_fl", "tcs_active_fr", "tcs_active_rl", "tcs_active_rr", "time_s"],
    "derived_inputs": ["slip_ratio", "tcs_target_slip_ratio_global"],
    "trend_source": "tcs_max_control_time",
    "unit": "s",
    "description": "TCS单次激活后，从激活开始到打滑率稳定在全局目标打滑率附近所经历的最大时长。",
    "threshold": 1.5,
    "source": "TCS标定规范：控滑过程应在1.5秒内完成",
    "pass_condition": "value <= threshold",
    "rule_description": "所有TCS激活事件中，控滑时间最大值应不超过1.5秒。",
    "pass_message": "TCS最大控滑时间达标。",
    "fail_message": "TCS最大控滑时间超标，请检查控滑响应。",
}

CALIBRATION = {
    "stability_tolerance": 0.02,  # 判定打滑率已稳定在目标值附近的允许偏差（绝对值）
}

def calculate_kpi(dataframe):
    series = calculate_kpi_series(dataframe)
    if series.empty or series.isna().all():
        return np.nan
    return series.max()

def calculate_kpi_series(dataframe):
    # 检查依赖列
    target_col = "tcs_target_slip_ratio_global"
    if target_col not in dataframe.columns:
        return pd.Series(np.nan, index=dataframe.index, dtype=float)
    global_target = float(dataframe[target_col].iloc[0]) if len(dataframe) > 0 else np.nan
    if np.isnan(global_target):
        return pd.Series(np.nan, index=dataframe.index, dtype=float)

    tcs_cols = ["tcs_active_fl", "tcs_active_fr", "tcs_active_rl", "tcs_active_rr"]
    available_tcs = [c for c in tcs_cols if c in dataframe.columns]
    if not available_tcs:
        return pd.Series(np.nan, index=dataframe.index, dtype=float)

    tcs_active = dataframe[available_tcs].any(axis=1).astype(bool).values

    if "time_s" not in dataframe.columns or "slip_ratio" not in dataframe.columns:
        return pd.Series(np.nan, index=dataframe.index, dtype=float)

    time_s = pd.to_numeric(dataframe["time_s"], errors="coerce").values
    slip = dataframe["slip_ratio"].values

    # 分段检测：TCS激活区间
    active_int = tcs_active.astype(int)
    diff_arr = np.diff(active_int, prepend=0)
    starts = np.where(diff_arr == 1)[0]
    ends = np.where(diff_arr == -1)[0]

    # 若末尾仍处于激活状态，补充结束边界
    if active_int[-1] == 1:
        ends = np.append(ends, len(active_int))

    # 确保边界配对
    min_len = min(len(starts), len(ends))
    starts = starts[:min_len]
    ends = ends[:min_len]

    # 过滤长度大于0的有效段
    valid_segments = [(s, e) for s, e in zip(starts, ends) if e > s]
    if not valid_segments:
        return pd.Series(np.zeros(len(dataframe)), index=dataframe.index, dtype=float)

    result = np.zeros(len(dataframe), dtype=float)
    tolerance = CALIBRATION["stability_tolerance"]

    for start, end in valid_segments:
        seg_time = time_s[start:end]
        seg_slip = slip[start:end]
        rel_time = seg_time - seg_time[0]

        # 稳定判定：打滑率 <= 目标值 + 容差
        stable_condition = seg_slip <= (global_target + tolerance)
        if np.any(stable_condition):
            stable_idx = np.argmax(stable_condition)
        else:
            stable_idx = len(seg_slip) - 1
        control_time = rel_time[stable_idx]

        # 段内计时递增，到达稳定时间后保持
        timer = np.minimum(rel_time, control_time)
        result[start:end] = timer

    return pd.Series(result, index=dataframe.index, dtype=float)