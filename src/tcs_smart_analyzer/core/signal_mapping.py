from __future__ import annotations

import re
from collections.abc import Iterable

import pandas as pd

from tcs_smart_analyzer.config.editable_configs import list_required_raw_input_signals, load_interface_mapping


class SignalMappingError(ValueError):
    pass


TIME_AXIS_ALIASES = {
    "time",
    "timestamps",
    "timestamp",
    "time[s]",
    "time(s)",
    "times",
    "ts",
    "time [s]",
    "time (s)",
    "t [s]",
    "t(s)",
    "t[s]",
    "zeit",
    "zeit [s]",
    "zeit(s)",
    "zeit[s]",
    "time_stamp",
    "timestamp_s",
    "elapsed_time",
    "t",
}


def _clean_column_name(name: str) -> str:
    cleaned = str(name).strip()
    cleaned = re.sub(r"\s*[\\/]\s*[A-Za-z][\w .-]*:\s*[-+]?\d+\s*$", "", cleaned)
    cleaned = re.sub(r"\s*\[.*?\]", "", cleaned)
    cleaned = re.sub(r"\s*\((?:s|ms|kph|km/h|m/s|m/s2|m/s²|rad/s|rpm|nm|bar|°|deg|%|g)\)\s*$", "", cleaned, flags=re.IGNORECASE)
    if "::" in cleaned:
        cleaned = cleaned.rsplit("::", 1)[-1]
    if "." in cleaned:
        last_part = cleaned.rsplit(".", 1)[-1]
        if last_part and not last_part[0].isdigit():
            cleaned = last_part
    return cleaned.strip()


def _strip_unit_suffix(name: str) -> str:
    cleaned = re.sub(r"\s*\[.*?\]\s*$", "", name)
    cleaned = re.sub(r"\s*\(.*?\)\s*$", "", cleaned)
    return cleaned.strip()


def _is_time_axis_alias(name: str) -> bool:
    normalized = str(name).strip().lower()
    if normalized in TIME_AXIS_ALIASES:
        return True
    return _strip_unit_suffix(normalized) in TIME_AXIS_ALIASES


def resolve_requested_signal_names(required_signals: Iterable[str] | None = None) -> list[str]:
    interface_mapping = load_interface_mapping()
    candidate_names: list[str] = []
    for raw_name in required_signals or list_required_raw_input_signals():
        standard_name = str(raw_name).strip()
        if not standard_name:
            continue
        entry = interface_mapping.get(standard_name, {})
        actual_names = list(entry.get("actual_names", []))
        manual_column = entry.get("manual_column", "")
        aliases = list(entry.get("aliases", []))
        for candidate in [manual_column, *actual_names, standard_name, *aliases]:
            cleaned_candidate = _clean_column_name(str(candidate).strip())
            if cleaned_candidate and cleaned_candidate not in candidate_names:
                candidate_names.append(cleaned_candidate)
    return candidate_names


def _levenshtein_distance(s1: str, s2: str) -> int:
    if len(s1) < len(s2):
        return _levenshtein_distance(s2, s1)
    if not s2:
        return len(s1)
    prev_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            cost = 0 if c1 == c2 else 1
            curr_row.append(min(curr_row[j] + 1, prev_row[j + 1] + 1, prev_row[j] + cost))
        prev_row = curr_row
    return prev_row[-1]


def build_signal_mapping(columns: Iterable[str], required_signals: Iterable[str] | None = None) -> dict[str, str]:
    column_list = list(columns)
    normalized_lookup = {normalize_name(column): column for column in column_list}
    exact_lookup = {str(column).strip(): column for column in column_list}

    cleaned_lookup: dict[str, str] = {}
    exact_cleaned_lookup: dict[str, str] = {}
    for column in column_list:
        cleaned = _clean_column_name(column)
        if cleaned and cleaned not in exact_cleaned_lookup:
            exact_cleaned_lookup[cleaned] = column
        norm_cleaned = normalize_name(cleaned)
        if norm_cleaned and norm_cleaned not in cleaned_lookup:
            cleaned_lookup[norm_cleaned] = column

    mapping: dict[str, str] = {}
    interface_mapping = load_interface_mapping()
    candidate_names: list[str] = []
    for name in [*interface_mapping.keys(), *(required_signals or [])]:
        normalized_name = str(name).strip()
        if normalized_name and normalized_name not in candidate_names:
            candidate_names.append(normalized_name)

    for standard_name in candidate_names:
        entry = interface_mapping.get(standard_name, {})
        preferred_names = list(entry.get("actual_names", []))
        manual_column = entry.get("manual_column", "")
        aliases = list(entry.get("aliases", []))
        explicit_names = [str(name).strip() for name in [manual_column, *preferred_names] if str(name).strip()]
        strict_manual_mapping = bool(explicit_names)
        if manual_column and manual_column not in preferred_names:
            preferred_names = [manual_column, *preferred_names]
        if not strict_manual_mapping:
            fallback_names = [standard_name, *aliases]
            for fallback_name in fallback_names:
                if fallback_name and fallback_name not in preferred_names:
                    preferred_names.append(fallback_name)

        matched = False
        for preferred_name in preferred_names:
            exact_pref = str(preferred_name).strip()
            if strict_manual_mapping:
                matched_column = exact_lookup.get(exact_pref)
                if matched_column is not None:
                    mapping[standard_name] = matched_column
                    matched = True
                    break
                cleaned_pref = _clean_column_name(exact_pref)
                matched_column = exact_cleaned_lookup.get(cleaned_pref)
                if matched_column is not None:
                    mapping[standard_name] = matched_column
                    matched = True
                    break
                if standard_name == "time_s" and "time_s" in exact_lookup and _is_time_axis_alias(exact_pref):
                    mapping[standard_name] = exact_lookup["time_s"]
                    matched = True
                    break
                continue
            norm_pref = normalize_name(preferred_name)
            matched_column = normalized_lookup.get(norm_pref)
            if matched_column is not None:
                mapping[standard_name] = matched_column
                matched = True
                break

        if not matched and not strict_manual_mapping:
            for preferred_name in preferred_names:
                norm_pref = normalize_name(preferred_name)
                matched_column = cleaned_lookup.get(norm_pref)
                if matched_column is not None:
                    mapping[standard_name] = matched_column
                    matched = True
                    break

        if not matched and not strict_manual_mapping:
            norm_std = normalize_name(standard_name)
            for norm_col, actual_col in cleaned_lookup.items():
                if norm_std in norm_col or norm_col in norm_std:
                    if len(norm_std) >= 4 and len(norm_col) >= 4:
                        mapping[standard_name] = actual_col
                        matched = True
                        break

        if not matched and not strict_manual_mapping and len(normalize_name(standard_name)) >= 5:
            norm_std = normalize_name(standard_name)
            best_match: str | None = None
            best_distance = 3
            for norm_col, actual_col in cleaned_lookup.items():
                if abs(len(norm_col) - len(norm_std)) > 3:
                    continue
                dist = _levenshtein_distance(norm_std, norm_col)
                if dist < best_distance:
                    best_distance = dist
                    best_match = actual_col
            if best_match is not None:
                mapping[standard_name] = best_match

    required_list = list(required_signals or list_required_raw_input_signals())
    explicit_missing: list[str] = []
    for standard_name in candidate_names:
        if standard_name in mapping:
            continue
        entry = interface_mapping.get(standard_name, {})
        manual_column = str(entry.get("manual_column", "")).strip()
        actual_names = [str(name).strip() for name in entry.get("actual_names", []) if str(name).strip()]
        if manual_column or actual_names:
            explicit_missing.append(standard_name)
    missing = [signal for signal in required_list if signal not in mapping]
    for signal in explicit_missing:
        if signal not in missing:
            missing.append(signal)
    if "tcs_active" in missing and any(name in mapping for name in ["tcs_active_fl", "tcs_active_fr", "tcs_active_rl", "tcs_active_rr"]):
        missing = [signal for signal in missing if signal != "tcs_active"]
    if missing:
        raise SignalMappingError(
            "缺少关键字段，无法开始 TCS 分析: " + ", ".join(missing)
        )

    return mapping


def normalize_signals(dataframe: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    normalized = pd.DataFrame()
    for standard_name, source_column in mapping.items():
        normalized[standard_name] = pd.to_numeric(dataframe[source_column], errors="coerce")

    wheel_tcs_columns = [name for name in ["tcs_active_fl", "tcs_active_fr", "tcs_active_rl", "tcs_active_rr"] if name in normalized]
    if "tcs_active" not in normalized and wheel_tcs_columns:
        normalized["tcs_active"] = normalized[wheel_tcs_columns].fillna(0.0).any(axis=1).astype(float)
    if "tcs_active" in normalized:
        for wheel_column in ["tcs_active_fl", "tcs_active_fr", "tcs_active_rl", "tcs_active_rr"]:
            if wheel_column not in normalized:
                normalized[wheel_column] = pd.to_numeric(normalized["tcs_active"], errors="coerce")

    if "accel_pedal_pct" not in normalized:
        torque_request = normalized.get("torque_request_nm")
        if torque_request is not None:
            max_abs = float(torque_request.abs().max()) if not torque_request.empty else 0.0
            if max_abs > 0.0:
                normalized["accel_pedal_pct"] = (torque_request / max_abs).clip(lower=0.0, upper=1.0) * 100.0

    return normalized.sort_values("time_s").dropna(subset=["time_s"]).reset_index(drop=True)


def normalize_name(name: str) -> str:
    return "".join(character.lower() for character in str(name) if character.isalnum())
