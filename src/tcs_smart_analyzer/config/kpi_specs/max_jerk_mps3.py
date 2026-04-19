from __future__ import annotations

IS_TEMPLATE = False

import pandas as pd
import numpy as np

# 可选依赖：如果没有安装 scipy，滤波功能将自动禁用
try:
    from scipy.signal import butter, filtfilt
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

KPI_DEFINITION = {
    "name": "max_jerk_mps3",
    "title": "最大纵向冲击度",
    "raw_inputs": ["time_s", "longitudinal_accel_mps2"],
    "derived_inputs": [],
    "trend_source": "max_jerk_mps3",
    "unit": "m/s^3",
    "description": "全程最大纵向冲击度（可选滤波后）",
    "threshold": 8.0,
    "source": "migrated_from_stb_001",
    "pass_condition": "value <= threshold",
    "rule_description": "最大纵向冲击度应控制在8mps3以内。",
    "pass_message": "纵向冲击度正常",
    "fail_message": "纵向冲击度偏大，建议复核舒适性",
}

CALIBRATION = {
    "enable_lowpass_filter": True,  # 是否启用低通滤波，建议在噪声较大时保持开启
    "lowpass_cutoff_hz": 3.0,  # 低通截止频率，人体对纵向 jerk 敏感范围通常在 2-3 Hz
    "min_sample_interval_s": 1e-6,  # 时间差分下限，避免 dt 过小导致 jerk 爆炸
}


def _lowpass_filter(data: pd.Series, time_s: pd.Series, cutoff_hz: float) -> pd.Series:
    """
    对信号应用零相位低通滤波。
    若 scipy 不可用或数据不足，则返回原数据。
    """
    if not SCIPY_AVAILABLE:
        print("警告: scipy 未安装，滤波已禁用，Jerk 结果将包含高频噪声。")
        return data
    if len(data) < 9:   # 数据太短无法设计滤波器
        return data

    # 计算平均采样频率
    dt = time_s.diff().median()
    if pd.isna(dt) or dt <= 0:
        return data
    fs = 1.0 / dt

    # 奈奎斯特频率
    nyquist = 0.5 * fs
    if cutoff_hz >= nyquist:
        cutoff_hz = nyquist * 0.99

    # 设计二阶巴特沃斯低通滤波器
    b, a = butter(N=2, Wn=cutoff_hz / nyquist, btype='low')
    # 使用 filtfilt 实现零相位滤波（不引入相位滞后）
    filtered = filtfilt(b, a, data.to_numpy())
    return pd.Series(filtered, index=data.index)


def _jerk_series(dataframe: pd.DataFrame) -> pd.Series:
    """
    计算纵向冲击度 (Jerk) 时间序列。
    包含：排序、滤波、鲁棒差分。
    """
    # 1. 复制并确保按时间排序
    df = dataframe[["time_s", "longitudinal_accel_mps2"]].copy()
    df = df.sort_values("time_s").reset_index(drop=True)

    # 2. 转换为数值类型
    time_s = pd.to_numeric(df["time_s"], errors="coerce")
    accel = pd.to_numeric(df["longitudinal_accel_mps2"], errors="coerce")

    # 3. 剔除无效行
    valid = time_s.notna() & accel.notna()
    time_s = time_s[valid]
    accel = accel[valid]

    if len(time_s) < 2:
        return pd.Series([0.0], index=dataframe.index[:1])

    # 4. 可选滤波（对加速度信号进行低通）
    if CALIBRATION["enable_lowpass_filter"]:
        accel = _lowpass_filter(accel, time_s, CALIBRATION["lowpass_cutoff_hz"])

    # 5. 计算时间间隔 Δt
    dt = time_s.diff().fillna(0.0)
    # 将过小的时间间隔替换为最小保护值，避免 Jerk 爆炸
    dt = dt.clip(lower=CALIBRATION["min_sample_interval_s"])

    # 6. 计算加速度差分 Δa
    da = accel.diff()

    # 7. 计算 Jerk = Δa / Δt
    jerk = da / dt
    # 替换无穷大和 NaN
    jerk = jerk.replace([float("inf"), float("-inf")], np.nan).fillna(0.0)

    # 8. 将结果映射回原始索引（保持与输入 dataframe 长度一致）
    result = pd.Series(index=dataframe.index, dtype=float)
    result.loc[valid[valid].index] = jerk.values
    result = result.fillna(0.0)

    return result


def calculate_kpi(dataframe: pd.DataFrame) -> float:
    """返回全程最大纵向冲击度（绝对值）"""
    jerk = _jerk_series(dataframe)
    return float(jerk.abs().max())


def calculate_kpi_series(dataframe: pd.DataFrame) -> pd.Series:
    """返回纵向冲击度绝对值的累计最大值（用于趋势图）"""
    jerk = _jerk_series(dataframe)
    return jerk.abs().cummax()


# ================== 使用示例 ==================
if __name__ == "__main__":
    # 构造一段模拟的加减速数据（带噪声）
    t = np.linspace(0, 10, 1001)  # 1000 Hz 采样
    a = np.sin(2 * np.pi * 0.5 * t) * 2.0   # 0.5 Hz 正弦加速度，幅值 2 m/s²
    a += np.random.normal(0, 0.05, size=len(t))  # 添加高斯噪声

    df_test = pd.DataFrame({
        "time_s": t,
        "longitudinal_accel_mps2": a
    })

    jerk_series = _jerk_series(df_test)
    max_jerk = calculate_kpi(df_test)
    print(f"最大纵向冲击度: {max_jerk:.2f} m/s³")

    # 对比滤波与未滤波的效果（强制关闭滤波）
    filter_enabled = CALIBRATION["enable_lowpass_filter"]
    CALIBRATION["enable_lowpass_filter"] = False
    max_jerk_no_filter = calculate_kpi(df_test)
    CALIBRATION["enable_lowpass_filter"] = filter_enabled
    print(f"未滤波时最大 Jerk: {max_jerk_no_filter:.2f} m/s³ (通常大很多)")