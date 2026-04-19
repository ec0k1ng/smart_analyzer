from __future__ import annotations

IS_TEMPLATE = False

import pandas as pd
import numpy as np

DERIVED_SIGNAL_DEFINITION = {
    "name": "slip_ratio",
    "title": "打滑率",
    "raw_inputs": ["wheel_speed_fl", "wheel_speed_fr", "wheel_speed_rl", "wheel_speed_rr", "vehicle_speed"],
    "derived_inputs": [],
    "description": "四轮最大打滑率，驱动打滑恒为正，制动打滑恒为负，自动适应前进/倒车工况。",
    "algorithm_summary": "以|vehicle_speed|为参考（下限0.5 kph），计算各轮(wheel_speed - vehicle_speed) / |vehicle_speed|，并根据车速符号对结果取同号修正：当vehicle_speed<0时，结果乘以-1，确保驱动打滑始终为正，制动打滑始终为负。取四轮绝对值最大值后还原符号。",
}

CALIBRATION = {
    "reference_speed_floor_kph": 0.5,  # 参考车速绝对值下限，避免低速或静止时分母过小
    "missing_slip_fill_value": 0.0,  # 单轮 slip_ratio 缺失时的补充值，保证最终序列连续
}

def calculate_signal(dataframe):
    # 参考车速绝对值下限，避免低速分母过小
    ref_speed_abs = pd.to_numeric(dataframe["vehicle_speed"], errors="coerce").abs().clip(lower=CALIBRATION["reference_speed_floor_kph"])
    vehicle_speed = pd.to_numeric(dataframe["vehicle_speed"], errors="coerce")
    
    # 车速符号：前进为正，倒车为负，静止时默认视为前进状态
    speed_sign = np.sign(vehicle_speed).replace(0, 1).values
    
    wheel_columns = ["wheel_speed_fl", "wheel_speed_fr", "wheel_speed_rl", "wheel_speed_rr"]
    slip_columns = []
    
    for col in wheel_columns:
        if col not in dataframe.columns:
            continue
        wheel = pd.to_numeric(dataframe[col], errors="coerce")
        # 原始滑转率公式（未修正符号）
        slip_raw = (wheel - vehicle_speed) / ref_speed_abs
        # 关键修正：若车速为负，则将整个滑转率取反，使得物理意义统一
        slip_corrected = slip_raw * speed_sign
        slip_columns.append(slip_corrected.fillna(CALIBRATION["missing_slip_fill_value"]))
    
    if not slip_columns:
        return pd.Series(0.0, index=dataframe.index, dtype=float)
    
    slip_frame = pd.concat(slip_columns, axis=1)
    # 取绝对值最大的轮，并还原其符号（保留正负号信息）
    # 替代已弃用的 lookup 方法：取每行绝对值最大的索引，再取对应值
    abs_slip = slip_frame.abs()
    max_abs_idx = abs_slip.idxmax(axis=1)
    
    # 通过索引取对应值（兼容所有 pandas 版本）
    max_slip = slip_frame.lookup(max_abs_idx.index, max_abs_idx.values) if hasattr(slip_frame, 'lookup') else pd.Series(
        [slip_frame.iloc[i, slip_frame.columns.get_loc(col)] for i, col in max_abs_idx.items()],
        index=max_abs_idx.index
    )
    
    return pd.Series(max_slip, index=dataframe.index, dtype=float).fillna(CALIBRATION["missing_slip_fill_value"])