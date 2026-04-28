from __future__ import annotations

import math
import re
from collections.abc import Iterable

import numpy as np
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

MAPPING_EXPRESSION_PREFIX = "expr:"

STANDARD_SIGNAL_ALIASES = {
    "vehicle_speed_kph": ["vehicle_speed"],
    "wheel_speed_fl_kph": ["wheel_speed_fl"],
    "wheel_speed_fr_kph": ["wheel_speed_fr"],
    "wheel_speed_rl_kph": ["wheel_speed_rl"],
    "wheel_speed_rr_kph": ["wheel_speed_rr"],
    "yaw_rate_degps": ["yawrate"],
}

COMPATIBILITY_SIGNAL_ALIASES = {
    "vehicle_speed": "vehicle_speed_kph",
    "wheel_speed_fl": "wheel_speed_fl_kph",
    "wheel_speed_fr": "wheel_speed_fr_kph",
    "wheel_speed_rl": "wheel_speed_rl_kph",
    "wheel_speed_rr": "wheel_speed_rr_kph",
    "yawrate": "yaw_rate_degps",
}

_EXPRESSION_IDENTIFIER_PATTERN = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")


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


def _is_mapping_expression(candidate: str) -> bool:
    text = str(candidate).strip()
    if not text:
        return False
    if text.startswith(MAPPING_EXPRESSION_PREFIX):
        return True
    return any(operator in text for operator in ["+", "-", "*", "/"])


def _extract_expression_identifiers(expression: str) -> list[str]:
    reserved = {"np", "pd", "math", "True", "False", "None", "and", "or", "not"}
    identifiers: list[str] = []
    for token in _EXPRESSION_IDENTIFIER_PATTERN.findall(str(expression)):
        if token in reserved or token.isdigit() or token in identifiers:
            continue
        identifiers.append(token)
    return identifiers


def _expression_token_candidates(token: str) -> list[str]:
    candidates = [token]
    cleaned = _clean_column_name(token)
    if cleaned and cleaned not in candidates:
        candidates.append(cleaned)
    return candidates


def _expression_can_resolve(expression: str, exact_lookup: dict[str, str], exact_cleaned_lookup: dict[str, str], cleaned_lookup: dict[str, str]) -> bool:
    identifiers = _extract_expression_identifiers(expression)
    if not identifiers:
        return False
    for token in identifiers:
        resolved = False
        for candidate in _expression_token_candidates(token):
            if candidate in exact_lookup or candidate in exact_cleaned_lookup or normalize_name(candidate) in cleaned_lookup:
                resolved = True
                break
        if not resolved:
            return False
    return True


def _build_expression_context(dataframe: pd.DataFrame) -> dict[str, object]:
    context: dict[str, object] = {}
    for column in dataframe.columns:
        series = pd.to_numeric(dataframe[column], errors="coerce")
        exact_name = str(column).strip()
        if exact_name.isidentifier() and exact_name not in context:
            context[exact_name] = series
        cleaned_name = _clean_column_name(exact_name)
        if cleaned_name.isidentifier() and cleaned_name not in context:
            context[cleaned_name] = series
    context.update({"np": np, "pd": pd, "math": math})
    return context


def _evaluate_mapping_expression(dataframe: pd.DataFrame, expression: str) -> pd.Series:
    result = eval(expression, {"__builtins__": {}}, _build_expression_context(dataframe))
    if np.isscalar(result):
        return pd.Series([float(result)] * len(dataframe), index=dataframe.index, dtype=float)
    if isinstance(result, pd.Series):
        return pd.to_numeric(result.reindex(dataframe.index), errors="coerce")
    return pd.to_numeric(pd.Series(result, index=dataframe.index), errors="coerce")


def _iter_preferred_signal_names(standard_name: str, manual_column: str, actual_names: list[str], aliases: list[str]) -> list[str]:
    preferred_names = list(actual_names)
    if manual_column and manual_column not in preferred_names:
        preferred_names = [manual_column, *preferred_names]
    for fallback_name in [standard_name, *aliases, *STANDARD_SIGNAL_ALIASES.get(standard_name, [])]:
        if fallback_name and fallback_name not in preferred_names:
            preferred_names.append(fallback_name)
    return preferred_names


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
        for candidate in [manual_column, *actual_names, standard_name, *aliases, *STANDARD_SIGNAL_ALIASES.get(standard_name, [])]:
            if _is_mapping_expression(candidate):
                for token in _extract_expression_identifiers(candidate):
                    cleaned_token = _clean_column_name(token)
                    if cleaned_token and cleaned_token not in candidate_names:
                        candidate_names.append(cleaned_token)
                continue
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
        manual_column = entry.get("manual_column", "")
        aliases = list(entry.get("aliases", []))
        preferred_names = list(entry.get("actual_names", []))
        explicit_names = [str(name).strip() for name in [manual_column, *preferred_names] if str(name).strip()]
        strict_manual_mapping = bool(explicit_names)
        if not strict_manual_mapping:
            preferred_names = _iter_preferred_signal_names(standard_name, manual_column, preferred_names, aliases)
        elif manual_column and manual_column not in preferred_names:
            preferred_names = [manual_column, *preferred_names]

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
                if _is_mapping_expression(exact_pref) and _expression_can_resolve(exact_pref, exact_lookup, exact_cleaned_lookup, cleaned_lookup):
                    mapping[standard_name] = f"{MAPPING_EXPRESSION_PREFIX}{exact_pref.removeprefix(MAPPING_EXPRESSION_PREFIX)}"
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
    abs_bundle = ["abs_active", "abs_active_fl", "abs_active_fr", "abs_active_rl", "abs_active_rr"]
    if "abs_active" in missing and any(name in mapping for name in ["abs_active_fl", "abs_active_fr", "abs_active_rl", "abs_active_rr"]):
        missing = [signal for signal in missing if signal != "abs_active"]
    if any(name in mapping for name in abs_bundle):
        if "abs_active" in mapping:
            missing = [signal for signal in missing if signal not in ["abs_active_fl", "abs_active_fr", "abs_active_rl", "abs_active_rr"]]
    else:
        missing = [signal for signal in missing if signal not in abs_bundle]
    if missing:
        raise SignalMappingError(
            "缺少关键字段，无法开始 TCS 分析: " + ", ".join(missing)
        )

    return mapping


def normalize_signals(dataframe: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    normalized = pd.DataFrame()
    for standard_name, source_column in mapping.items():
        if str(source_column).startswith(MAPPING_EXPRESSION_PREFIX):
            normalized[standard_name] = _evaluate_mapping_expression(dataframe, str(source_column)[len(MAPPING_EXPRESSION_PREFIX) :])
        else:
            normalized[standard_name] = pd.to_numeric(dataframe[source_column], errors="coerce")

    for alias_name, canonical_name in COMPATIBILITY_SIGNAL_ALIASES.items():
        if canonical_name in normalized and alias_name not in normalized:
            normalized[alias_name] = pd.to_numeric(normalized[canonical_name], errors="coerce")

    wheel_tcs_columns = [name for name in ["tcs_active_fl", "tcs_active_fr", "tcs_active_rl", "tcs_active_rr"] if name in normalized]
    if "tcs_active" not in normalized and wheel_tcs_columns:
        normalized["tcs_active"] = normalized[wheel_tcs_columns].fillna(0.0).any(axis=1).astype(float)
    if "tcs_active" in normalized:
        for wheel_column in ["tcs_active_fl", "tcs_active_fr", "tcs_active_rl", "tcs_active_rr"]:
            if wheel_column not in normalized:
                normalized[wheel_column] = pd.to_numeric(normalized["tcs_active"], errors="coerce")

    wheel_abs_columns = [name for name in ["abs_active_fl", "abs_active_fr", "abs_active_rl", "abs_active_rr"] if name in normalized]
    if "abs_active" not in normalized and wheel_abs_columns:
        normalized["abs_active"] = normalized[wheel_abs_columns].fillna(0.0).any(axis=1).astype(float)
    if "abs_active" in normalized:
        for wheel_column in ["abs_active_fl", "abs_active_fr", "abs_active_rl", "abs_active_rr"]:
            if wheel_column not in normalized:
                normalized[wheel_column] = pd.to_numeric(normalized["abs_active"], errors="coerce")

    if "accel_pedal_pct" not in normalized:
        torque_request = normalized.get("torque_request_nm")
        if torque_request is not None:
            max_abs = float(torque_request.abs().max()) if not torque_request.empty else 0.0
            if max_abs > 0.0:
                normalized["accel_pedal_pct"] = (torque_request / max_abs).clip(lower=0.0, upper=1.0) * 100.0

    return normalized.sort_values("time_s").dropna(subset=["time_s"]).reset_index(drop=True)


def normalize_name(name: str) -> str:
    return "".join(character.lower() for character in str(name) if character.isalnum())
