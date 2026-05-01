from __future__ import annotations

import math
import re
from collections.abc import Iterable

import numpy as np
import pandas as pd

from tcs_smart_analyzer.config.editable_configs import list_required_raw_input_signals, load_interface_mapping


class SignalMappingError(ValueError):
    pass


MAPPING_EXPRESSION_PREFIX = "expr:"

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


def _expression_can_resolve(expression: str, available_names: set[str], source_column_redirects: dict[str, str] | None = None) -> bool:
    identifiers = _extract_expression_identifiers(expression)
    if not identifiers:
        return False
    redirects = source_column_redirects or {}
    for token in identifiers:
        resolved = False
        for candidate in [token, *(_expression_token_candidates(token)[1:])]:
            redirected = redirects.get(candidate)
            if candidate in available_names or (redirected is not None and redirected in available_names):
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
    for source_name, target_name in dict(dataframe.attrs.get("source_column_redirects", {})).items():
        source_text = str(source_name).strip()
        target_text = str(target_name).strip()
        if not source_text.isidentifier() or target_text not in dataframe.columns:
            continue
        if source_text not in context:
            context[source_text] = pd.to_numeric(dataframe[target_text], errors="coerce")
    context.update({"np": np, "pd": pd, "math": math})
    return context


def _evaluate_mapping_expression(dataframe: pd.DataFrame, expression: str) -> pd.Series:
    result = eval(expression, {"__builtins__": {}}, _build_expression_context(dataframe))
    if np.isscalar(result):
        return pd.Series([float(result)] * len(dataframe), index=dataframe.index, dtype=float)
    if isinstance(result, pd.Series):
        return pd.to_numeric(result.reindex(dataframe.index), errors="coerce")
    return pd.to_numeric(pd.Series(result, index=dataframe.index), errors="coerce")


def _preferred_signal_names(entry: dict[str, object]) -> list[str]:
    preferred_names: list[str] = []
    manual_column = str(entry.get("manual_column", "")).strip()
    if manual_column:
        preferred_names.append(manual_column)
    for actual_name in entry.get("actual_names", []):
        normalized_name = str(actual_name).strip()
        if normalized_name and normalized_name not in preferred_names:
            preferred_names.append(normalized_name)
    return preferred_names


def resolve_requested_signal_names(required_signals: Iterable[str] | None = None) -> list[str]:
    interface_mapping = load_interface_mapping()
    candidate_names: list[str] = []
    for raw_name in required_signals or list_required_raw_input_signals():
        standard_name = str(raw_name).strip()
        if not standard_name:
            continue
        entry = interface_mapping.get(standard_name, {})
        for candidate in _preferred_signal_names(entry):
            if _is_mapping_expression(candidate):
                for token in _extract_expression_identifiers(candidate):
                    normalized_token = str(token).strip()
                    if normalized_token and normalized_token not in candidate_names:
                        candidate_names.append(normalized_token)
                continue
            normalized_candidate = str(candidate).strip()
            if normalized_candidate and normalized_candidate not in candidate_names:
                candidate_names.append(normalized_candidate)
    return candidate_names


def describe_mapping_candidates(required_signals: Iterable[str] | None = None) -> dict[str, list[str]]:
    interface_mapping = load_interface_mapping()
    candidate_map: dict[str, list[str]] = {}
    for raw_name in required_signals or list_required_raw_input_signals():
        standard_name = str(raw_name).strip()
        if not standard_name:
            continue
        preferred_names = _preferred_signal_names(interface_mapping.get(standard_name, {}))
        if preferred_names:
            candidate_map[standard_name] = preferred_names
    return candidate_map


def build_signal_mapping(
    columns: Iterable[str],
    required_signals: Iterable[str] | None = None,
    source_column_redirects: dict[str, str] | None = None,
    source_columns_before_time_normalization: Iterable[str] | None = None,
) -> dict[str, str]:
    column_list = list(columns)
    exact_lookup = {str(column).strip(): column for column in column_list}
    original_column_list = list(source_columns_before_time_normalization or column_list)
    original_lookup = {str(column).strip(): str(column).strip() for column in original_column_list}
    redirects = {str(source).strip(): str(target).strip() for source, target in (source_column_redirects or {}).items() if str(source).strip() and str(target).strip()}
    available_names = set(exact_lookup)

    mapping: dict[str, str] = {}
    interface_mapping = load_interface_mapping()
    candidate_names: list[str] = []
    for name in [*interface_mapping.keys(), *(required_signals or [])]:
        normalized_name = str(name).strip()
        if normalized_name and normalized_name not in candidate_names:
            candidate_names.append(normalized_name)

    for standard_name in candidate_names:
        entry = interface_mapping.get(standard_name, {})
        preferred_names = _preferred_signal_names(entry)

        matched = False
        for preferred_name in preferred_names:
            exact_pref = str(preferred_name).strip()
            if _is_mapping_expression(exact_pref):
                if _expression_can_resolve(exact_pref, available_names, redirects):
                    mapping[standard_name] = f"{MAPPING_EXPRESSION_PREFIX}{exact_pref.removeprefix(MAPPING_EXPRESSION_PREFIX)}"
                    matched = True
                    break
                continue
            original_column = original_lookup.get(exact_pref)
            if original_column is None:
                continue
            redirected_column = redirects.get(original_column)
            if redirected_column is not None and redirected_column in exact_lookup:
                matched = True
                mapping[standard_name] = exact_lookup[redirected_column]
                break
            matched_column = exact_lookup.get(original_column)
            if matched_column is not None:
                mapping[standard_name] = matched_column
                matched = True
                break

    required_list = list(required_signals or list_required_raw_input_signals())
    missing = [signal for signal in required_list if signal not in mapping]
    if missing:
        raise SignalMappingError(
            "缺少关键字段，无法开始 TCS 分析: " + ", ".join(missing)
        )

    return mapping


def list_source_columns_for_mapping(mapping: dict[str, str], source_column_redirects: dict[str, str] | None = None) -> list[str]:
    redirects = {str(source).strip(): str(target).strip() for source, target in (source_column_redirects or {}).items() if str(source).strip() and str(target).strip()}
    inverse_redirects = {target: source for source, target in redirects.items()}
    source_columns: list[str] = []
    for mapped_value in mapping.values():
        normalized_value = str(mapped_value).strip()
        if not normalized_value:
            continue
        if normalized_value.startswith(MAPPING_EXPRESSION_PREFIX):
            expression = normalized_value[len(MAPPING_EXPRESSION_PREFIX) :]
            for token in _extract_expression_identifiers(expression):
                source_name = inverse_redirects.get(token, token)
                if source_name and source_name not in source_columns:
                    source_columns.append(source_name)
            continue
        source_name = inverse_redirects.get(normalized_value, normalized_value)
        if source_name not in source_columns:
            source_columns.append(source_name)
    return source_columns


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
