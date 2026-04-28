from __future__ import annotations

IS_TEMPLATE = False

import numpy as np
import pandas as pd


DERIVED_SIGNAL_DEFINITION = {
    "name": "tcs_target_slip_kph",
    "title": "TCS全局目标打滑量",
    "raw_inputs": [
        "time_s",  # 时间轴，单位 s
        "tcs_active_fl",  # 左前轮TCS激活标志
        "tcs_active_fr",  # 右前轮TCS激活标志
        "tcs_active_rl",  # 左后轮TCS激活标志
        "tcs_active_rr",  # 右后轮TCS激活标志
    ],
    "derived_inputs": ["slip_kph"],
    "description": "全文件 TCS 激活阶段的时间加权平均绝对打滑量，作为 TCS 全局目标打滑量单值。",
    "algorithm_summary": "对所有 TCS 激活区间内的 |slip_kph| 按时间差做加权平均，输出单个目标打滑量标量。",
}

CALIBRATION = {
    "minimum_time_diff_s": 0.0,  # 时间差下限
}


def calculate_signal(dataframe):
    tcs_columns = ["tcs_active_fl", "tcs_active_fr", "tcs_active_rl", "tcs_active_rr"]
    active_columns = [column_name for column_name in tcs_columns if column_name in dataframe.columns]
    if not active_columns or "slip_kph" not in dataframe.columns or "time_s" not in dataframe.columns:
        return float("nan")

    tcs_active = dataframe[active_columns].any(axis=1).astype(bool)
    if not tcs_active.any():
        return float("nan")

    slip = pd.to_numeric(dataframe["slip_kph"], errors="coerce").abs()
    time_s = pd.to_numeric(dataframe["time_s"], errors="coerce")
    time_diffs = time_s.diff().fillna(CALIBRATION["minimum_time_diff_s"]).clip(lower=CALIBRATION["minimum_time_diff_s"])
    valid_mask = tcs_active & slip.notna() & (time_diffs > 0)
    if valid_mask.any():
        return float(np.average(slip[valid_mask], weights=time_diffs[valid_mask]))
    fallback_mask = tcs_active & slip.notna()
    if not fallback_mask.any():
        return float("nan")
    return float(slip[fallback_mask].mean())