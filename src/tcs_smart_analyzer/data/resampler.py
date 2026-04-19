from __future__ import annotations

import numpy as np
import pandas as pd


def detect_and_resample(dataframe: pd.DataFrame, time_column: str = "time_s") -> pd.DataFrame:
    if dataframe.empty or time_column not in dataframe.columns:
        return dataframe

    time_series = pd.to_numeric(dataframe[time_column], errors="coerce")
    if time_series.isna().all():
        return dataframe

    time_diff = time_series.diff().dropna()
    if time_diff.empty or (time_diff <= 0).all():
        return dataframe

    positive_diffs = time_diff[time_diff > 0]
    if positive_diffs.empty:
        return dataframe

    median_dt = float(positive_diffs.median())
    if median_dt <= 0:
        return dataframe

    min_dt = float(positive_diffs.quantile(0.05))
    max_dt = float(positive_diffs.quantile(0.95))

    if max_dt <= min_dt * 3.0:
        return dataframe

    needs_resample = False
    value_columns = [col for col in dataframe.columns if col != time_column]
    column_sample_rates: dict[str, float] = {}

    for col in value_columns:
        col_valid = dataframe[col].notna()
        if col_valid.sum() < 3:
            continue
        valid_indices = col_valid[col_valid].index
        col_times = time_series.loc[valid_indices]
        col_diffs = col_times.diff().dropna()
        col_pos_diffs = col_diffs[col_diffs > 0]
        if col_pos_diffs.empty:
            continue
        col_median_dt = float(col_pos_diffs.median())
        column_sample_rates[col] = col_median_dt
        if abs(col_median_dt - median_dt) > median_dt * 0.3:
            needs_resample = True

    if not needs_resample:
        return dataframe

    target_dt = min(column_sample_rates.values()) if column_sample_rates else median_dt
    target_dt = max(target_dt, 0.0001)

    t_start = float(time_series.iloc[0])
    t_end = float(time_series.iloc[-1])
    max_points = 2_000_000
    n_points = int((t_end - t_start) / target_dt) + 1
    if n_points > max_points:
        target_dt = (t_end - t_start) / max_points
        n_points = max_points

    unified_time = np.linspace(t_start, t_end, n_points)
    result = pd.DataFrame({time_column: unified_time})

    original_time = time_series.values.astype(float)

    for col in value_columns:
        col_values = pd.to_numeric(dataframe[col], errors="coerce").values.astype(float)
        valid_mask = ~np.isnan(col_values) & ~np.isnan(original_time)

        if valid_mask.sum() < 2:
            result[col] = np.nan
            continue

        valid_times = original_time[valid_mask]
        valid_values = col_values[valid_mask]

        sort_order = np.argsort(valid_times)
        valid_times = valid_times[sort_order]
        valid_values = valid_values[sort_order]

        _, unique_idx = np.unique(valid_times, return_index=True)
        valid_times = valid_times[unique_idx]
        valid_values = valid_values[unique_idx]

        if len(valid_times) < 2:
            result[col] = valid_values[0] if len(valid_values) > 0 else np.nan
            continue

        result[col] = np.interp(unified_time, valid_times, valid_values)

        result.loc[unified_time < valid_times[0], col] = np.nan
        result.loc[unified_time > valid_times[-1], col] = np.nan

    for key, value in dataframe.attrs.items():
        result.attrs[key] = value

    return result
