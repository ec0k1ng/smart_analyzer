from __future__ import annotations

IS_TEMPLATE = False

import pandas as pd


KPI_DEFINITION = {
    "name": "max_slip_speed",
    "title": "最大打滑量",
    "raw_inputs": ["wheel_speed_fl", "wheel_speed_fr", "wheel_speed_rl", "wheel_speed_rr", "vehicle_speed"],
    "derived_inputs": [],
    "trend_source": "max_slip_speed",
    "unit": "kph",
    "description": "全程四轮轮速与车速之差的绝对值的最大值，反映车轮最大打滑速度差",
    "threshold": 30.0,
    "source": "工程标定经验值",
    "pass_condition": "value <= threshold",
    "rule_description": "最大打滑量应不大于30 kph。",
    "pass_message": "最大打滑量在限值内",
    "fail_message": "最大打滑量超限",
}

CALIBRATION = {
    "empty_output_fill_value_kph": 0.0,  # 当前文件没有可用轮速时，给趋势曲线返回的兜底值
}


def _slip_speed_per_wheel(dataframe):
    vehicle_speed = pd.to_numeric(dataframe["vehicle_speed"], errors="coerce")
    wheel_cols = ["wheel_speed_fl", "wheel_speed_fr", "wheel_speed_rl", "wheel_speed_rr"]
    slip_frames = []

    for col in wheel_cols:
        if col not in dataframe.columns:
            continue
        wheel_speed = pd.to_numeric(dataframe[col], errors="coerce")
        diff = (wheel_speed - vehicle_speed).abs()
        slip_frames.append(pd.DataFrame({f"slip_speed_{col}": diff}))

    if not slip_frames:
        return pd.DataFrame({"slip_speed_none": CALIBRATION["empty_output_fill_value_kph"]}, index=dataframe.index)

    return pd.concat(slip_frames, axis=1)


def calculate_kpi(dataframe):
    slip_df = _slip_speed_per_wheel(dataframe)
    return float(slip_df.max().max())


def calculate_kpi_series(dataframe):
    slip_df = _slip_speed_per_wheel(dataframe)
    return slip_df.max(axis=1).cummax()