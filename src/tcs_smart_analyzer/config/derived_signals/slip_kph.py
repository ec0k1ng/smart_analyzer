from __future__ import annotations

IS_TEMPLATE = False

import numpy as np
import pandas as pd


DERIVED_SIGNAL_DEFINITION = {
    "name": "slip_kph",
    "title": "打滑量",
    "raw_inputs": [
        "vehicle_speed_kph",  # 车速，单位 kph
        "wheel_speed_fl_kph",  # 左前轮轮速，单位 kph
        "wheel_speed_fr_kph",  # 右前轮轮速，单位 kph
        "wheel_speed_rl_kph",  # 左后轮轮速，单位 kph
        "wheel_speed_rr_kph",  # 右后轮轮速，单位 kph
    ],
    "derived_inputs": [],
    "description": "四轮最大有符号打滑量，定义为轮速与车速之差；驱动打滑为正，制动打滑为负。",
    "algorithm_summary": "按车速符号统一前进/倒车工况，对每个车轮计算 (wheel_speed_kph - vehicle_speed_kph) * sign(vehicle_speed_kph)，再按每个时刻绝对值最大的车轮输出该车轮打滑量。",
}

CALIBRATION = {}


def calculate_signal(dataframe):
    vehicle_speed = pd.to_numeric(dataframe["vehicle_speed_kph"], errors="coerce")
    speed_sign = np.sign(vehicle_speed).replace(0, 1)
    wheel_columns = ["wheel_speed_fl_kph", "wheel_speed_fr_kph", "wheel_speed_rl_kph", "wheel_speed_rr_kph"]
    slip_columns = []

    for column_name in wheel_columns:
        if column_name not in dataframe.columns:
            continue
        wheel_speed = pd.to_numeric(dataframe[column_name], errors="coerce")
        slip_columns.append(((wheel_speed - vehicle_speed) * speed_sign).rename(column_name))

    if not slip_columns:
        return pd.Series(np.nan, index=dataframe.index, dtype=float)

    slip_frame = pd.concat(slip_columns, axis=1)
    abs_slip = slip_frame.abs()
    max_abs = abs_slip.max(axis=1, skipna=True)
    dominant = slip_frame.where(abs_slip.eq(max_abs, axis=0)).bfill(axis=1).iloc[:, 0]
    dominant[max_abs.isna()] = np.nan
    return pd.Series(dominant, index=dataframe.index, dtype=float)