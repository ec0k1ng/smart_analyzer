from __future__ import annotations

import numpy as np
from scipy import signal

IS_TEMPLATE = False


KPI_DEFINITION = {
    "name": "shake_rms_mps2",
    "title": "车辆抖动强度",
    "raw_inputs": [
        "longitudinal_accel_mps2",  # 纵向加速度，单位 m/s^2
    ],
    "derived_inputs": [],
    "trend_source": "shake_rms_mps2",
    "unit": "m/s^2",
    "description": "基于纵向加速度的加权均方根值，评价车辆纵向抖动程度。",
    "algorithm_summary": "对纵向加速度做带通滤波后计算均方根值作为全局抖动强度；趋势输出为固定时间窗内的滑动 RMS。",
    "threshold": 0.315,
    "source": "ISO 2631-1:1997/Amd 1:2010",
    "pass_condition": "value <= threshold",
    "rule_description": "车辆抖动强度应不大于 0.315 m/s^2。",
    "pass_message": "抖动强度在舒适范围内。",
    "fail_message": "抖动强度超过舒适阈值。",
}

CALIBRATION = {
    "filter_low_hz": 0.4,  # 带通滤波下限频率，单位 Hz，用于滤除极低频姿态变化。
    "filter_high_hz": 100.0,  # 带通滤波上限频率，单位 Hz，用于抑制高频噪声。
    "nyquist_margin_ratio": 0.99,  # 高通上限相对奈奎斯特频率的安全裕度，避免截止频率贴边失稳。
    "rms_window_s": 1.0,  # 趋势曲线滑动 RMS 窗长，单位 s。
}


def _design_wk_filter(sample_rate_hz):
    nyquist_hz = sample_rate_hz / 2.0
    low_hz = CALIBRATION["filter_low_hz"]
    high_hz = min(CALIBRATION["filter_high_hz"], nyquist_hz * CALIBRATION["nyquist_margin_ratio"])
    if low_hz >= high_hz:
        return np.array([[1.0, 0.0, 0.0, 1.0, 0.0, 0.0]])
    return signal.butter(4, [low_hz, high_hz], btype="band", fs=sample_rate_hz, output="sos")


def calculate_kpi(dataframe):
    accel = dataframe["longitudinal_accel_mps2"].values
    if len(dataframe) < 2:
        return float("nan")
    delta_t = dataframe.index[1] - dataframe.index[0]
    sample_rate_hz = 1.0 / delta_t
    filtered = signal.sosfilt(_design_wk_filter(sample_rate_hz), accel)
    return float(np.sqrt(np.mean(filtered ** 2)))


def calculate_kpi_series(dataframe):
    accel = dataframe["longitudinal_accel_mps2"].values
    if len(dataframe) < 2:
        return np.full(len(dataframe), np.nan)
    delta_t = dataframe.index[1] - dataframe.index[0]
    sample_rate_hz = 1.0 / delta_t
    filtered = signal.sosfilt(_design_wk_filter(sample_rate_hz), accel)
    window_size = max(1, int(CALIBRATION["rms_window_s"] * sample_rate_hz))
    window = np.ones(window_size) / window_size
    squared = filtered ** 2
    return np.sqrt(np.convolve(squared, window, mode="same"))