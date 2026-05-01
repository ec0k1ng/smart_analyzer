from __future__ import annotations

import io
import traceback
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from tcs_smart_analyzer.config.editable_configs import load_formula_signal_definitions, load_kpi_plugins
from tcs_smart_analyzer.core.models import KpiResult, RuleResult


@dataclass(slots=True)
class ConfigExecutionContext:
    owner_kind: str
    owner_name: str
    stage: str
    path: Path
    message: str
    line: int | None = None
    output_lines: list[str] = field(default_factory=list)


class ConfigExecutionError(RuntimeError):
    def __init__(self, context: ConfigExecutionContext, original_exception: Exception) -> None:
        self.context = context
        self.original_exception = original_exception
        super().__init__(context.message)


def _safe_eval(expression: str, local_context: dict[str, object]) -> object:
    import math
    import numpy as np

    return eval(expression, {"__builtins__": {}}, {**local_context, "np": np, "pd": pd, "math": math})


def _extract_plugin_error_line(exc: Exception, plugin_path: Path) -> int | None:
    try:
        resolved_path = plugin_path.resolve()
    except OSError:
        resolved_path = plugin_path
    for frame in reversed(traceback.extract_tb(exc.__traceback__)):
        try:
            frame_path = Path(frame.filename).resolve()
        except OSError:
            frame_path = Path(frame.filename)
        if frame_path == resolved_path:
            return int(frame.lineno)
    return None


def _execute_plugin_callable(
    callable_obj,
    *args,
    owner_kind: str,
    owner_name: str,
    stage: str,
    plugin_path: Path,
    runtime_logger=None,
):  # noqa: ANN001
    output_buffer = io.StringIO()
    try:
        with redirect_stdout(output_buffer), redirect_stderr(output_buffer):
            result = callable_obj(*args)
    except Exception as exc:  # noqa: BLE001
        output_lines = [line.rstrip() for line in output_buffer.getvalue().splitlines() if line.strip()]
        raise ConfigExecutionError(
            ConfigExecutionContext(
                owner_kind=owner_kind,
                owner_name=owner_name,
                stage=stage,
                path=plugin_path,
                message=str(exc) or exc.__class__.__name__,
                line=_extract_plugin_error_line(exc, plugin_path),
                output_lines=output_lines,
            ),
            exc,
        ) from exc

    if callable(runtime_logger):
        for line in [line.rstrip() for line in output_buffer.getvalue().splitlines() if line.strip()]:
            runtime_logger("info", f"[{owner_kind}:{owner_name}:{stage}] {line}")
    return result


def _coerce_kpi_signal_series(
    plugin: dict[str, object],
    dataframe: pd.DataFrame,
    metric_value: float | None,
    runtime_logger=None,
) -> pd.Series | None:
    calculate_kpi_series = plugin.get("calculate_kpi_series")
    if callable(calculate_kpi_series):
        result = _execute_plugin_callable(
            calculate_kpi_series,
            dataframe,
            owner_kind="KPI",
            owner_name=str(plugin.get("definition", {}).get("name", "unnamed_kpi")),
            stage="calculate_kpi_series",
            plugin_path=Path(plugin.get("path") or plugin["definition"].get("module_path", "")),
            runtime_logger=runtime_logger,
        )
        if isinstance(result, pd.Series):
            return pd.to_numeric(result.reindex(dataframe.index), errors="coerce")
        if result is not None:
            return pd.to_numeric(pd.Series(result, index=dataframe.index), errors="coerce")

    definition = plugin["definition"]
    trend_source = str(definition.get("trend_source", "")).strip()
    if trend_source and trend_source != "time_s" and trend_source in dataframe.columns:
        return pd.to_numeric(dataframe[trend_source], errors="coerce").reindex(dataframe.index)

    if dataframe.empty:
        return None
    fill_value = np.nan if metric_value is None else float(metric_value)
    return pd.Series([fill_value] * len(dataframe), index=dataframe.index, dtype=float)


def _normalize_kpi_value(metric_value: object) -> float | None:
    try:
        numeric_value = float(metric_value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(numeric_value):
        return None
    return numeric_value


def _coerce_derived_signal_series(dataframe: pd.DataFrame, result: object) -> pd.Series:
    if isinstance(result, pd.Series):
        return pd.to_numeric(result.reindex(dataframe.index), errors="coerce")
    if np.isscalar(result):
        return pd.Series([float(result)] * len(dataframe), index=dataframe.index, dtype=float)
    return pd.to_numeric(pd.Series(result, index=dataframe.index), errors="coerce")


def attach_derived_signal_columns(
    dataframe: pd.DataFrame,
    kpi_definitions: list[dict[str, object]],
    derived_signal_plugins: list[dict[str, object]],
    runtime_logger=None,
) -> pd.DataFrame:
    if not derived_signal_plugins:
        return dataframe.copy()

    plugin_lookup = {
        str(plugin.get("definition", {}).get("name", "")).strip(): plugin
        for plugin in derived_signal_plugins
        if str(plugin.get("definition", {}).get("name", "")).strip()
    }
    ordered_names: list[str] = []
    visited: set[str] = set()
    visiting: set[str] = set()

    def visit(signal_name: str) -> None:
        if not signal_name or signal_name in visited:
            return
        if signal_name in visiting:
            raise ValueError(f"检测到派生量循环依赖: {signal_name}")
        plugin = plugin_lookup.get(signal_name)
        if plugin is None:
            raise ValueError(f"KPI 依赖了不存在的派生量: {signal_name}")
        visiting.add(signal_name)
        definition = plugin.get("definition", {})
        for dependency_name in definition.get("derived_inputs", []):
            visit(str(dependency_name).strip())
        visiting.remove(signal_name)
        visited.add(signal_name)
        ordered_names.append(signal_name)

    for signal_name in sorted(plugin_lookup):
        visit(signal_name)

    augmented = dataframe.copy()
    for signal_name in ordered_names:
        plugin = plugin_lookup[signal_name]
        result = _execute_plugin_callable(
            plugin["calculate_signal"],
            augmented,
            owner_kind="派生量",
            owner_name=signal_name,
            stage="calculate_signal",
            plugin_path=Path(plugin.get("path") or plugin["definition"].get("module_path", "")),
            runtime_logger=runtime_logger,
        )
        augmented[signal_name] = _coerce_derived_signal_series(augmented, result)
    return augmented


def calculate_global_kpis(
    dataframe: pd.DataFrame,
    settings=None,
    kpi_plugins: list[dict[str, object]] | None = None,
    runtime_logger=None,
) -> list[KpiResult]:
    kpis: list[KpiResult] = []
    for plugin in (kpi_plugins or load_kpi_plugins()):
        definition = plugin["definition"]
        metric_value_raw = _execute_plugin_callable(
            plugin["calculate_kpi"],
            dataframe,
            owner_kind="KPI",
            owner_name=str(definition.get("name", "unnamed_kpi")),
            stage="calculate_kpi",
            plugin_path=Path(plugin.get("path") or definition.get("module_path", "")),
            runtime_logger=runtime_logger,
        )
        metric_value = _normalize_kpi_value(metric_value_raw)
        kpi_name = str(definition.get("name", "unnamed_kpi"))
        threshold_default = definition.get("threshold")
        threshold_value = None if threshold_default is None else float(settings.get_rule_threshold(kpi_name, threshold_default) if settings is not None else threshold_default)
        threshold_source = str(settings.get_rule_threshold_source(kpi_name, str(definition.get("source", "kpi_definition"))) if settings is not None else definition.get("source", "kpi_definition"))
        pass_condition = str(definition.get("pass_condition", "True"))
        evaluation_context = {
            "value": metric_value,
            "threshold": threshold_value,
            "dataframe": dataframe,
            "source_path": str(dataframe.attrs.get("source_path", "")),
            "source_name": str(dataframe.attrs.get("source_name", "")),
            "source_stem": str(dataframe.attrs.get("source_stem", "")),
            "analysis_profile": str(dataframe.attrs.get("analysis_profile", "default")),
            "generated_at": str(dataframe.attrs.get("generated_at", "")),
            "mapped_columns": dict(dataframe.attrs.get("mapped_columns", {})),
        }
        if metric_value is None:
            status = "warning"
            result_label = "未知"
            assessment_message = str(definition.get("unknown_message", "该 KPI 结果为空，当前工况下无法判断。"))
        else:
            passed = bool(_safe_eval(pass_condition, evaluation_context)) if pass_condition else True
            status = "pass" if passed else "fail"
            result_label = "达标" if passed else "未达标"
            assessment_message = str(definition.get("pass_message", "该 KPI 达标") if passed else definition.get("fail_message", "该 KPI 未达标"))
        signal_values = _coerce_kpi_signal_series(plugin, dataframe, metric_value, runtime_logger=runtime_logger)
        kpis.append(
            KpiResult(
                name=kpi_name,
                title=str(definition.get("title", kpi_name)),
                value=metric_value,
                unit=str(definition.get("unit", "")),
                description=str(definition.get("description", "")),
                signal_values=signal_values,
                rule_description=str(definition.get("rule_description", "仅做趋势观测，不设置限制")),
                status=status,
                assessment_message=assessment_message,
                threshold_value=threshold_value,
                threshold_source=threshold_source,
                pass_condition=pass_condition,
                result_label=result_label,
            )
        )
    return kpis


def build_rule_results_from_kpis(kpis: list[KpiResult]) -> list[RuleResult]:
    return [
        RuleResult(
            rule_id=item.name,
            category="kpi_assessment",
            title=item.title,
            status=item.status,
            severity="info" if item.status == "pass" else "medium" if item.status == "warning" else "high",
            measured_value=item.value,
            threshold_value=item.threshold_value,
            unit=item.unit,
            message=item.assessment_message or item.rule_description,
            threshold_source=item.threshold_source,
            confidence=1.0,
        )
        for item in kpis
    ]


def populate_kpi_signal_values(
    dataframe: pd.DataFrame,
    kpis: list[KpiResult],
    group_key: str | None = None,
    kpi_plugins: list[dict[str, object]] | None = None,
) -> list[KpiResult]:
    plugin_lookup = {
        str(plugin.get("definition", {}).get("name", "")).strip(): plugin
        for plugin in (kpi_plugins or load_kpi_plugins(group_key))
        if str(plugin.get("definition", {}).get("name", "")).strip()
    }
    for item in kpis:
        if item.signal_values is not None:
            continue
        plugin = plugin_lookup.get(item.name)
        if plugin is None:
            if dataframe.empty:
                continue
            item.signal_values = pd.Series([float(item.value)] * len(dataframe), index=dataframe.index, dtype=float)
            continue
        item.signal_values = _coerce_kpi_signal_series(plugin, dataframe, float(item.value))
    return kpis


def attach_signal_library_columns(dataframe: pd.DataFrame, kpis: list[KpiResult]) -> pd.DataFrame:
    augmented = dataframe.copy()
    kpi_lookup = {item.name: item.value for item in kpis}
    for item in kpis:
        if item.signal_values is not None:
            augmented[item.name] = pd.to_numeric(item.signal_values.reindex(augmented.index), errors="coerce")
        else:
            augmented[item.name] = float(item.value)
    local_context: dict[str, object] = {column: augmented[column] for column in augmented.columns}
    local_context.update(kpi_lookup)
    for definition in load_formula_signal_definitions():
        try:
            result = _safe_eval(definition["expression"], local_context)
        except Exception:
            continue
        if np.isscalar(result):
            augmented[definition["name"]] = float(result)
        elif isinstance(result, pd.Series):
            augmented[definition["name"]] = result.reindex(augmented.index)
        else:
            augmented[definition["name"]] = pd.Series(result, index=augmented.index)
        local_context[definition["name"]] = augmented[definition["name"]]
    return augmented
