from __future__ import annotations

import ast
import math
from typing import Any

import numpy as np
import pandas as pd


FORMULA_FUNCTION_REFERENCE = [
    {
        "name": "max",
        "description": "取序列最大值。",
        "example": "max(peak_slip_ratio)",
        "rank": 1,
    },
    {
        "name": "mean",
        "description": "取序列平均值。",
        "example": "mean(vehicle_speed)",
        "rank": 2,
    },
    {
        "name": "abs_max",
        "description": "取绝对值后的最大值。",
        "example": "abs_max(max_jerk_mps3)",
        "rank": 3,
    },
    {
        "name": "sum",
        "description": "对序列求和。",
        "example": "sum(tcs_active_time_s)",
        "rank": 4,
    },
    {
        "name": "time_to_first_ge",
        "description": "返回信号首次大于等于阈值的响应时间。",
        "example": "time_to_first_ge(torque_cut_nm, 5.0, time_s)",
        "rank": 5,
    },
    {
        "name": "dominant_frequency",
        "description": "计算序列主频。",
        "example": "dominant_frequency(vehicle_speed, time_s)",
        "rank": 6,
    },
    {
        "name": "missing_rate",
        "description": "返回多个输入信号中的最大缺失率。",
        "example": "missing_rate(wheel_speed_rl, wheel_speed_rr, vehicle_speed)",
        "rank": 7,
    },
    {
        "name": "count",
        "description": "统计元素个数。",
        "example": "count(vehicle_speed)",
        "rank": 8,
    },
    {
        "name": "percentile",
        "description": "计算序列分位值。",
        "example": "percentile(peak_slip_ratio, 95)",
        "rank": 9,
    },
]

COMPARISON_OPERATOR_REFERENCE = [
    {
        "operator": "<=",
        "meaning": "测量值小于等于阈值时判定通过。",
        "example": "max(peak_slip_ratio) <= 0.18",
        "note": "最常用于峰值上限类规则。",
    },
    {
        "operator": ">=",
        "meaning": "测量值大于等于阈值时判定通过。",
        "example": "count(vehicle_speed) >= 1",
        "note": "最常用于数据完整性和计数类规则。",
    },
    {
        "operator": "<",
        "meaning": "测量值严格小于阈值时判定通过。",
        "example": "mean(peak_slip_ratio) < 0.1",
        "note": "适用于严格上界场景。",
    },
    {
        "operator": ">",
        "meaning": "测量值严格大于阈值时判定通过。",
        "example": "first(vehicle_speed) > 0.5",
        "note": "适用于下界判定。",
    },
    {
        "operator": "==",
        "meaning": "测量值与阈值完全相等时判定通过。",
        "example": "count(tcs_active_time_s) == 0",
        "note": "通常只建议用于离散计数。",
    },
]


def _to_series(value: Any) -> pd.Series:
    if isinstance(value, pd.Series):
        return value.astype(float)
    if isinstance(value, np.ndarray):
        return pd.Series(value, dtype=float)
    if isinstance(value, list | tuple):
        return pd.Series(value, dtype=float)
    return pd.Series([value], dtype=float)


def _series_max(value: Any) -> float:
    if isinstance(value, list):
        return float(max(value)) if value else 0.0
    series = _to_series(value)
    return float(series.max()) if not series.empty else 0.0


def _series_min(value: Any) -> float:
    if isinstance(value, list):
        return float(min(value)) if value else 0.0
    series = _to_series(value)
    return float(series.min()) if not series.empty else 0.0


def _series_mean(value: Any) -> float:
    series = _to_series(value)
    return float(series.mean()) if not series.empty else 0.0


def _series_sum(value: Any) -> float:
    series = _to_series(value)
    return float(series.sum()) if not series.empty else 0.0


def _series_abs_max(value: Any) -> float:
    series = _to_series(value)
    return float(series.abs().max()) if not series.empty else 0.0


def _series_std(value: Any) -> float:
    series = _to_series(value)
    return float(series.std()) if not series.empty else 0.0


def _series_count(value: Any) -> float:
    if isinstance(value, list):
        return float(len(value))
    series = _to_series(value)
    return float(series.notna().sum())


def _series_first(value: Any) -> float:
    series = _to_series(value).dropna()
    return float(series.iloc[0]) if not series.empty else 0.0


def _series_last(value: Any) -> float:
    series = _to_series(value).dropna()
    return float(series.iloc[-1]) if not series.empty else 0.0


def _series_percentile(value: Any, percent: float) -> float:
    series = _to_series(value).dropna()
    return float(np.percentile(series, percent)) if not series.empty else 0.0


def _missing_rate(*values: Any) -> float:
    rates = []
    for value in values:
        series = _to_series(value)
        if series.empty:
            rates.append(1.0)
        else:
            rates.append(float(series.isna().mean()))
    return max(rates) if rates else 0.0


def _time_to_first_ge(series: Any, threshold: float, time_s: Any) -> float | None:
    values = _to_series(series)
    time_axis = _to_series(time_s)
    if values.empty or time_axis.empty:
        return None
    mask = values >= threshold
    if not bool(mask.any()):
        return None
    first_index = mask[mask].index[0]
    return float(time_axis.loc[first_index] - time_axis.iloc[0])


def _dominant_frequency(values: Any, sample_time_s: Any) -> float:
    signal = _to_series(values).fillna(0.0).to_numpy(dtype=float)
    sample = _to_series(sample_time_s)
    valid_dt = sample[sample > 0.0]
    if len(signal) < 4 or len(valid_dt) < 4:
        return 0.0

    mean_dt = float(valid_dt.mean())
    demeaned = signal - np.mean(signal)
    if np.allclose(demeaned, 0.0):
        return 0.0

    fft = np.fft.rfft(demeaned)
    freqs = np.fft.rfftfreq(len(demeaned), mean_dt)
    if len(freqs) < 2:
        return 0.0
    dominant_index = int(np.argmax(np.abs(fft[1:])) + 1)
    dominant_frequency = float(freqs[dominant_index])
    return 0.0 if math.isnan(dominant_frequency) else dominant_frequency


ALLOWED_FUNCTIONS = {
    "max": _series_max,
    "min": _series_min,
    "mean": _series_mean,
    "sum": _series_sum,
    "abs_max": _series_abs_max,
    "std": _series_std,
    "count": _series_count,
    "first": _series_first,
    "last": _series_last,
    "percentile": _series_percentile,
    "missing_rate": _missing_rate,
    "time_to_first_ge": _time_to_first_ge,
    "dominant_frequency": _dominant_frequency,
}


class SafeExpressionEvaluator:
    def __init__(self, variables: dict[str, Any]) -> None:
        self.variables = variables

    def evaluate(self, expression: str) -> Any:
        tree = ast.parse(expression, mode="eval")
        return self._eval_node(tree.body)

    def _eval_node(self, node: ast.AST) -> Any:
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            if node.id not in self.variables:
                raise ValueError(f"表达式引用了未定义变量: {node.id}")
            return self.variables[node.id]
        if isinstance(node, ast.List):
            return [self._eval_node(item) for item in node.elts]
        if isinstance(node, ast.Tuple):
            return tuple(self._eval_node(item) for item in node.elts)
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in ALLOWED_FUNCTIONS:
                raise ValueError("表达式调用了不允许的函数。")
            function = ALLOWED_FUNCTIONS[node.func.id]
            args = [self._eval_node(arg) for arg in node.args]
            return function(*args)
        if isinstance(node, ast.BinOp):
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                return left / right
            if isinstance(node.op, ast.Pow):
                return left ** right
            raise ValueError("表达式包含不支持的二元运算。")
        if isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand)
            if isinstance(node.op, ast.USub):
                return -operand
            if isinstance(node.op, ast.UAdd):
                return +operand
            raise ValueError("表达式包含不支持的一元运算。")
        raise ValueError("表达式包含不支持的语法。")


def evaluate_formula(expression: str, variables: dict[str, Any]) -> Any:
    evaluator = SafeExpressionEvaluator(variables)
    return evaluator.evaluate(expression)