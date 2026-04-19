from __future__ import annotations

import numpy as np
from scipy import signal

IS_TEMPLATE = False

KPI_DEFINITION = {
    "name": "vehicle_shake_intensity",
    "title": "车辆抖动强度",
    "raw_inputs": ["longitudinal_accel_mps2"],
    "derived_inputs": [],
    "trend_source": "vehicle_shake_intensity",
    "unit": "m/s²",
    "description": "基于纵向加速度的加权均方根值，评价车辆行驶过程中的纵向抖动程度，参考ISO 2631-1人体振动舒适性评价方法。",
    "threshold": 0.315,
    "source": "ISO 2631-1:1997/Amd 1:2010 中关于纵向振动舒适性边界（略感不舒适阈值）",
    "pass_condition": "value <= threshold",
    "rule_description": "车辆抖动强度应不大于人体可接受的纵向振动舒适阈值0.315 m/s²。",
    "pass_message": "抖动强度在人体舒适范围内。",
    "fail_message": "抖动强度超过人体舒适阈值，可能引起不适。",
}

CALIBRATION = {
    "filter_low_hz": 0.4,  # ISO 2631-1 纵向加权滤波的低截止频率
    "filter_high_hz": 100.0,  # ISO 2631-1 纵向加权滤波的高截止频率上限
    "nyquist_margin_ratio": 0.99,  # 逼近奈奎斯特频率时保留的安全余量
    "rms_window_s": 1.0,  # 过程曲线采用的 RMS 滑动时间窗长度
}

def _design_wk_filter(fs):
    """设计ISO 2631-1 Wk纵向加权滤波器，根据采样频率自动调整截止频率"""
    nyq = fs / 2.0
    # 理想通带：0.4 Hz ~ 100 Hz，但必须小于奈奎斯特频率
    low = CALIBRATION["filter_low_hz"]
    high = min(CALIBRATION["filter_high_hz"], nyq * CALIBRATION["nyquist_margin_ratio"])  # 留出少量余量避免边界问题
    if low >= high:
        # 采样率过低，无法进行有效滤波，返回一个全通滤波器（无滤波）
        sos = np.array([[1.0, 0.0, 0.0, 1.0, 0.0, 0.0]])
        return sos
    sos = signal.butter(4, [low, high], btype='band', fs=fs, output='sos')
    return sos

def calculate_kpi(dataframe):
    ax = dataframe["longitudinal_accel_mps2"].values
    if len(dataframe) < 2:
        return float(np.nan)

    # 计算采样频率（假设索引为等间隔时间序列）
    dt = dataframe.index[1] - dataframe.index[0]
    fs = 1.0 / dt

    # 设计滤波器
    sos = _design_wk_filter(fs)
    filtered = signal.sosfilt(sos, ax)

    # 计算加权加速度均方根值
    rms = np.sqrt(np.mean(filtered ** 2))
    return float(rms)

def calculate_kpi_series(dataframe):
    ax = dataframe["longitudinal_accel_mps2"].values
    if len(dataframe) < 2:
        return np.full(len(dataframe), np.nan)

    dt = dataframe.index[1] - dataframe.index[0]
    fs = 1.0 / dt

    # 设计滤波器
    sos = _design_wk_filter(fs)
    filtered = signal.sosfilt(sos, ax)

    # 1秒滑动窗RMS包络
    window_size = int(CALIBRATION["rms_window_s"] * fs)
    if window_size < 1:
        window_size = 1
    window = np.ones(window_size) / window_size
    squared = filtered ** 2
    rms_series = np.sqrt(np.convolve(squared, window, mode='same'))

    return rms_series