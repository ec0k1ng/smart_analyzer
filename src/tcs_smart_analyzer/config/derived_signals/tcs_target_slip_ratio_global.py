from __future__ import annotations

IS_TEMPLATE = False

import pandas as pd
import numpy as np

DERIVED_SIGNAL_DEFINITION = {
    "name": "tcs_target_slip_ratio_global",
    "title": "TCS全局目标打滑率",
    "raw_inputs": ["tcs_active_fl", "tcs_active_fr", "tcs_active_rl", "tcs_active_rr", "time_s"],
    "derived_inputs": ["slip_ratio"],
    "description": "整个数据文件中所有TCS激活期间的时间加权平均打滑率，作为该数据文件的固有属性。全时段以恒定直线显示，供KPI作为稳定目标。",
    "algorithm_summary": "以四个TCS激活标志的逻辑或确定激活区间；收集所有激活区间内的 slip_ratio 与时间差，计算全局时间加权平均值；返回一个与数据等长的序列，每个元素均为该全局平均值。若缺失必要信号则返回全NaN。",
}

CALIBRATION = {
    "minimum_time_diff_s": 0.0,  # 计算时间加权平均前，对 time_s 差分施加的下限
}

def calculate_signal(dataframe):
    # 1. TCS激活标志收集
    tcs_cols = ["tcs_active_fl", "tcs_active_fr", "tcs_active_rl", "tcs_active_rr"]
    available_tcs = [c for c in tcs_cols if c in dataframe.columns]
    if not available_tcs:
        return pd.Series(np.nan, index=dataframe.index, dtype=float)

    tcs_active = dataframe[available_tcs].any(axis=1).astype(bool)

    if tcs_active.sum() == 0:
        return pd.Series(np.nan, index=dataframe.index, dtype=float)

    # 2. 依赖列检查
    if "slip_ratio" not in dataframe.columns or "time_s" not in dataframe.columns:
        return pd.Series(np.nan, index=dataframe.index, dtype=float)

    slip = pd.to_numeric(dataframe["slip_ratio"], errors="coerce")
    time_s = pd.to_numeric(dataframe["time_s"], errors="coerce")

    # 3. 时间差计算（用于加权平均）
    time_diffs = time_s.diff().fillna(CALIBRATION["minimum_time_diff_s"]).clip(lower=CALIBRATION["minimum_time_diff_s"])

    # 4. 筛选激活段内的有效数据点
    valid_mask = tcs_active & slip.notna() & (time_diffs > 0)
    if not valid_mask.any():
        return pd.Series(np.nan, index=dataframe.index, dtype=float)

    # 5. 计算全局时间加权平均打滑率
    weights = time_diffs[valid_mask]
    values = slip[valid_mask]
    global_avg = np.average(values, weights=weights)

    # 6. 返回全时间轴恒定值序列（水平直线）
    return pd.Series(global_avg, index=dataframe.index, dtype=float)