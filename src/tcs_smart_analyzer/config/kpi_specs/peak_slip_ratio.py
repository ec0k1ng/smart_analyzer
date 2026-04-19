from __future__ import annotations

IS_TEMPLATE = False

import pandas as pd


KPI_DEFINITION = {
    "name": "peak_slip_ratio",
    "title": "峰值打滑率",
    "raw_inputs": [],
    "derived_inputs": ["slip_ratio"],
    "trend_source": "peak_slip_ratio",
    "unit": "ratio",
    "description": "全程打滑率派生量的最大值。",
    "threshold": 0.18,
    "source": "migrated_from_perf_001",
    "pass_condition": "value <= threshold",
    "rule_description": "峰值打滑率应不大于标定阈值，避免打滑控制能力不足。",
    "pass_message": "峰值打滑率在目标范围内",
    "fail_message": "峰值打滑率超限",
}

CALIBRATION = {
    "missing_slip_fill_value": 0.0,  # slip_ratio 缺失时的补充值，避免累计峰值曲线中断
}


def calculate_kpi(dataframe):
    slip_ratio = pd.to_numeric(dataframe["slip_ratio"], errors="coerce")
    return float(slip_ratio.fillna(CALIBRATION["missing_slip_fill_value"]).max()) if not dataframe.empty else 0.0


def calculate_kpi_series(dataframe):
    slip_ratio = pd.to_numeric(dataframe["slip_ratio"], errors="coerce").fillna(CALIBRATION["missing_slip_fill_value"])
    return slip_ratio.cummax()
