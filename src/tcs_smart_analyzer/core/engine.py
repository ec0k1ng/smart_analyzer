from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from tcs_smart_analyzer import __version__
from tcs_smart_analyzer.config.analysis_settings import AnalysisSettings, load_analysis_settings
from tcs_smart_analyzer.config.editable_configs import (
    ConfigValidationIssue,
    get_config_file_paths,
    load_derived_signal_definitions,
    load_derived_signal_plugins,
    load_kpi_definitions,
    load_kpi_plugins,
    sync_interface_mapping_file,
)
from tcs_smart_analyzer.core.features import (
    attach_derived_signal_columns,
    attach_signal_library_columns,
    build_rule_results_from_kpis,
    calculate_global_kpis,
)
from tcs_smart_analyzer.core.models import AnalysisContext, AnalysisResult
from tcs_smart_analyzer.core.signal_mapping import MAPPING_EXPRESSION_PREFIX, build_signal_mapping, describe_mapping_candidates, list_source_columns_for_mapping, normalize_signals, resolve_requested_signal_names
from tcs_smart_analyzer.data.loaders import SUPPORTED_FILE_TYPES, inspect_timeseries_file_columns, load_timeseries_file
from tcs_smart_analyzer.data.resampler import detect_and_resample


class AnalysisEngine:
    def __init__(self, settings: AnalysisSettings | None = None, kpi_group_key: str | None = None, runtime_logger=None, progress_callback=None) -> None:
        sync_interface_mapping_file()
        self.settings = settings or load_analysis_settings()
        self.kpi_group_key = kpi_group_key
        self.runtime_logger = runtime_logger
        self.progress_callback = progress_callback
        self.invalid_runtime_issues: list[ConfigValidationIssue] = []
        self._load_runtime_components()

    def reload_runtime_definitions(self, settings: AnalysisSettings | None = None, kpi_group_key: str | None = None) -> None:
        self.settings = settings or self.settings
        if kpi_group_key is not None:
            self.kpi_group_key = kpi_group_key
        self._load_runtime_components()

    def _load_runtime_components(self) -> None:
        self.kpi_definitions = load_kpi_definitions(self.kpi_group_key)
        self.kpi_plugins = load_kpi_plugins(self.kpi_group_key)
        self.derived_signal_definitions = load_derived_signal_definitions()
        self.derived_signal_plugins = load_derived_signal_plugins()
        self._filter_invalid_runtime_components()
        self.required_raw_input_signals = self._build_required_raw_input_signals()

    def _filter_invalid_runtime_components(self) -> None:
        issues: dict[tuple[str, str], ConfigValidationIssue] = {}
        derived_lookup = {
            str(definition.get("name", "")).strip(): definition
            for definition in self.derived_signal_definitions
            if str(definition.get("name", "")).strip()
        }
        visiting: set[str] = set()
        validity_cache: dict[str, bool] = {}

        def add_issue(path: Path | str, message: str, code: str) -> None:
            issue_path = Path(path) if path else Path.cwd()
            issues[(str(issue_path), message)] = ConfigValidationIssue(path=issue_path, message=message, code=code)

        def validate_derived(signal_name: str, owner_definition: dict[str, object], owner_kind: str) -> bool:
            normalized_name = str(signal_name).strip()
            if not normalized_name:
                return True
            if normalized_name in validity_cache:
                return validity_cache[normalized_name]
            if normalized_name in visiting:
                add_issue(
                    str(owner_definition.get("module_path", "")),
                    f"{owner_kind} {owner_definition.get('name', 'unnamed')} 的 derived_inputs 存在循环依赖: {normalized_name}",
                    "derived-cycle",
                )
                validity_cache[normalized_name] = False
                return False
            definition = derived_lookup.get(normalized_name)
            if definition is None:
                add_issue(
                    str(owner_definition.get("module_path", "")),
                    f"{owner_kind} {owner_definition.get('name', 'unnamed')} 的 derived_inputs 引用了不存在的派生量: {normalized_name}",
                    "missing-derived-input",
                )
                validity_cache[normalized_name] = False
                return False
            visiting.add(normalized_name)
            valid = True
            for dependency_name in definition.get("derived_inputs", []):
                if not validate_derived(str(dependency_name).strip(), definition, "派生量"):
                    valid = False
            visiting.remove(normalized_name)
            validity_cache[normalized_name] = valid
            return valid

        valid_kpi_names: set[str] = set()
        for definition in self.kpi_definitions:
            dependencies = [str(name).strip() for name in definition.get("derived_inputs", []) if str(name).strip()]
            if all(validate_derived(signal_name, definition, "KPI") for signal_name in dependencies):
                valid_kpi_names.add(str(definition.get("name", "")).strip())

        self.kpi_definitions = [
            definition
            for definition in self.kpi_definitions
            if str(definition.get("name", "")).strip() in valid_kpi_names
        ]
        self.kpi_plugins = [
            plugin
            for plugin in self.kpi_plugins
            if str(plugin.get("definition", {}).get("name", "")).strip() in valid_kpi_names
        ]

        required_derived_names = self._resolve_required_derived_names(self.kpi_definitions)
        self.derived_signal_definitions = [
            definition
            for definition in self.derived_signal_definitions
            if str(definition.get("name", "")).strip() in required_derived_names
        ]
        self.derived_signal_plugins = [
            plugin
            for plugin in self.derived_signal_plugins
            if str(plugin.get("definition", {}).get("name", "")).strip() in required_derived_names
        ]
        self.invalid_runtime_issues = list(issues.values())

    def _resolve_required_derived_names(self, kpi_definitions: list[dict[str, object]]) -> set[str]:
        lookup = {
            str(definition.get("name", "")).strip(): definition
            for definition in self.derived_signal_definitions
            if str(definition.get("name", "")).strip()
        }
        resolved: set[str] = set()

        def visit(signal_name: str) -> None:
            normalized_name = str(signal_name).strip()
            if not normalized_name or normalized_name in resolved:
                return
            definition = lookup.get(normalized_name)
            if definition is None:
                return
            for dependency_name in definition.get("derived_inputs", []):
                visit(str(dependency_name).strip())
            resolved.add(normalized_name)

        for definition in kpi_definitions:
            for signal_name in definition.get("derived_inputs", []):
                visit(str(signal_name).strip())
        return resolved

    def _build_required_raw_input_signals(self) -> list[str]:
        required_signals = {"time_s"}
        required_signals.update({
            str(signal_name).strip()
            for definition in self.kpi_definitions
            for signal_name in definition.get("raw_inputs", [])
            if str(signal_name).strip()
        })
        for definition in self.derived_signal_definitions:
            for signal_name in definition.get("raw_inputs", []):
                normalized_name = str(signal_name).strip()
                if normalized_name:
                    required_signals.add(normalized_name)
        return sorted(required_signals)

    def _emit_runtime_log(self, level: str, message: str) -> None:
        if callable(self.runtime_logger):
            self.runtime_logger(level, message)

    def _emit_progress(self, fraction: float, message: str) -> None:
        if callable(self.progress_callback):
            self.progress_callback(float(fraction), message)

    @staticmethod
    def _mapping_log_display_name(column_name: str, source_column_redirects: dict[str, str] | None = None) -> str:
        display_column = str(column_name)
        if display_column.startswith(MAPPING_EXPRESSION_PREFIX):
            return display_column[len(MAPPING_EXPRESSION_PREFIX):]
        redirects = {
            str(source).strip(): str(target).strip()
            for source, target in (source_column_redirects or {}).items()
            if str(source).strip() and str(target).strip()
        }
        inverse_redirects = {target: source for source, target in redirects.items()}
        return inverse_redirects.get(display_column, display_column)

    def analyze_file(self, file_path: str | Path, kpi_group_key: str | None = None) -> AnalysisResult:
        if kpi_group_key != self.kpi_group_key:
            self.reload_runtime_definitions(kpi_group_key=kpi_group_key)
        source_path = Path(file_path)
        generated_at = datetime.now().astimezone().isoformat(timespec="seconds")
        self._emit_runtime_log("debug", f"开始分析文件: {source_path.name}")
        requested_signal_names = resolve_requested_signal_names(self.required_raw_input_signals)
        mapping_candidates = describe_mapping_candidates(self.required_raw_input_signals)
        mapping: dict[str, str] | None = None
        dataframe: pd.DataFrame
        source_suffix = source_path.suffix.lower()
        inspection_supported_suffixes = {".csv", ".xlsx", ".xls", ".dat", ".mdf", ".mf4"}
        if source_suffix in inspection_supported_suffixes:
            self._emit_progress(0.08, f"分析中 {source_path.name} - 初步预映射")
            self._emit_runtime_log("debug", f"确认所需信号完成: 共 {len(self.required_raw_input_signals)} 项")
            for standard_name, candidate_names in mapping_candidates.items():
                display_candidates = []
                for candidate in candidate_names:
                    candidate_text = str(candidate).strip()
                    if candidate_text.startswith(MAPPING_EXPRESSION_PREFIX):
                        candidate_text = candidate_text[len(MAPPING_EXPRESSION_PREFIX):]
                    display_candidates.append(candidate_text)
                self._emit_runtime_log("debug", f"初步预映射: {standard_name} <- {' | '.join(display_candidates)}")

            inspected = inspect_timeseries_file_columns(source_path)
            if inspected is not None:
                header_columns, original_columns, source_column_redirects = inspected
                self._emit_progress(0.16, f"分析中 {source_path.name} - 确认实际映射")
                mapping = build_signal_mapping(
                    header_columns,
                    self.required_raw_input_signals,
                    source_column_redirects=source_column_redirects,
                    source_columns_before_time_normalization=original_columns,
                )
                self._emit_runtime_log("debug", f"接口映射确认完成: 已从实际数据中命中 {len(mapping)} 个信号")
                for standard_name, column_name in mapping.items():
                    display_column = self._mapping_log_display_name(column_name, source_column_redirects=source_column_redirects)
                    self._emit_runtime_log("debug", f"接口映射: {standard_name} -> {display_column}")

                selected_source_columns = list_source_columns_for_mapping(mapping, source_column_redirects=source_column_redirects)
                self._emit_runtime_log(
                    "debug",
                    f"将只读取最终命中的 {len(selected_source_columns)} 个原始列/通道: {', '.join(selected_source_columns[:20])}{' ...' if len(selected_source_columns) > 20 else ''}",
                )
                self._emit_progress(0.24, f"分析中 {source_path.name} - 读取已确认信号列")
                self._emit_runtime_log("debug", f"读取数据文件: {source_path}")
                dataframe = load_timeseries_file(
                    source_path,
                    required_signals=requested_signal_names,
                    selected_source_columns=selected_source_columns,
                )
            else:
                self._emit_runtime_log("debug", f"读取数据文件: {source_path}")
                self._emit_progress(0.18, f"分析中 {source_path.name} - 读取数据文件")
                dataframe = load_timeseries_file(
                    source_path,
                    required_signals=requested_signal_names,
                )
        else:
            if source_suffix in {".blf", ".asc"}:
                self._emit_runtime_log(
                    "debug",
                    f"总线日志采用按需 DBC 解码：将只尝试解码所需信号涉及的报文，不会展开全部总线信号。当前所需信号候选共 {len(requested_signal_names)} 项。",
                )
            self._emit_runtime_log("debug", f"读取数据文件: {source_path}")
            self._emit_progress(0.18, f"分析中 {source_path.name} - 读取数据文件")
            dataframe = load_timeseries_file(
                source_path,
                required_signals=requested_signal_names,
            )
        self._emit_runtime_log(
            "debug",
            f"读取完成: {source_path.name}，共 {len(dataframe)} 行、{len(dataframe.columns)} 列，列名: {', '.join(map(str, list(dataframe.columns)[:12]))}{' ...' if len(dataframe.columns) > 12 else ''}",
        )
        dataframe.attrs["source_path"] = str(source_path)
        dataframe.attrs["source_name"] = source_path.name
        dataframe.attrs["source_stem"] = source_path.stem
        dataframe.attrs["analysis_profile"] = self.settings.profile_name
        dataframe.attrs["generated_at"] = generated_at
        self._emit_progress(0.28, f"分析中 {source_path.name} - 校验接口映射")
        mapping = mapping or build_signal_mapping(
            dataframe.columns,
            self.required_raw_input_signals,
            source_column_redirects=dict(dataframe.attrs.get("source_column_redirects", {})),
            source_columns_before_time_normalization=dataframe.attrs.get("source_columns_before_time_normalization", dataframe.columns),
        )
        if source_suffix not in inspection_supported_suffixes:
            self._emit_runtime_log("debug", f"接口映射完成: 已命中 {len(mapping)} 个信号")
            for standard_name, column_name in mapping.items():
                display_column = self._mapping_log_display_name(
                    column_name,
                    source_column_redirects=dict(dataframe.attrs.get("source_column_redirects", {})),
                )
                self._emit_runtime_log("debug", f"接口映射: {standard_name} -> {display_column}")

        self._emit_progress(0.38, f"分析中 {source_path.name} - 标准化信号")
        dataframe.attrs["mapped_columns"] = dict(mapping)
        normalized = normalize_signals(dataframe, mapping)
        self._emit_runtime_log("debug", f"信号标准化完成: 当前 {len(normalized)} 行、{len(normalized.columns)} 列")
        normalized.attrs.update(dataframe.attrs)
        self._emit_progress(0.5, f"分析中 {source_path.name} - 时间轴处理")
        normalized = detect_and_resample(normalized, time_column="time_s")
        self._emit_runtime_log("debug", f"时间轴检查/重采样完成: 当前 {len(normalized)} 行")
        normalized.attrs.update(dataframe.attrs)
        if self.derived_signal_definitions:
            self._emit_runtime_log(
                "debug",
                f"开始计算派生量: {', '.join(str(item.get('name', '')) for item in self.derived_signal_definitions[:12] if str(item.get('name', '')).strip())}{' ...' if len(self.derived_signal_definitions) > 12 else ''}",
            )
        self._emit_progress(0.64, f"分析中 {source_path.name} - 计算派生量")
        normalized = attach_derived_signal_columns(
            normalized,
            self.kpi_definitions,
            self.derived_signal_plugins,
            runtime_logger=self.runtime_logger,
        )
        self._emit_runtime_log("debug", f"派生量计算完成: 当前 {len(normalized.columns)} 列")
        normalized.attrs.update(dataframe.attrs)
        self._emit_runtime_log("debug", f"开始计算 KPI: 共 {len(self.kpi_definitions)} 项")
        self._emit_progress(0.8, f"分析中 {source_path.name} - 计算 KPI")
        kpis = calculate_global_kpis(normalized, self.settings, self.kpi_plugins, runtime_logger=self.runtime_logger)
        pass_count = sum(1 for item in kpis if item.status == "pass")
        warning_count = sum(1 for item in kpis if item.status == "warning")
        fail_count = sum(1 for item in kpis if item.status == "fail")
        self._emit_runtime_log("debug", f"KPI 计算完成: 达标 {pass_count}，未知 {warning_count}，未达标 {fail_count}")
        normalized = attach_signal_library_columns(normalized, kpis)
        normalized.attrs.update(dataframe.attrs)

        context = AnalysisContext(
            source_path=source_path,
            dataframe=dataframe,
            mapped_columns=mapping,
            metadata={
                "analysis_profile": self.settings.profile_name,
                "kpi_group_key": self.kpi_group_key or "__all_kpis__",
                "config_path": str(self.settings.config_path) if self.settings.config_path else None,
                "analyzer_version": __version__,
                "generated_at": generated_at,
                "settings_metadata": dict(self.settings.metadata),
                "rule_settings": self.settings.export_rule_settings(),
                "config_files": {key: str(value) for key, value in get_config_file_paths().items()},
            },
        )

        rule_results = build_rule_results_from_kpis(kpis)
        self._emit_runtime_log("debug", f"规则结果生成完成: 共 {len(rule_results)} 条")
        self._emit_progress(0.94, f"分析中 {source_path.name} - 生成结果")
        self._emit_runtime_log("debug", f"文件分析结束: {source_path.name}")
        self._emit_progress(1.0, f"分析完成 {source_path.name}")

        return AnalysisResult(
            context=context,
            kpis=kpis,
            rule_results=rule_results,
            normalized_frame=normalized,
        )

    def analyze_files(self, file_paths: list[str | Path], kpi_group_key: str | None = None) -> list[AnalysisResult]:
        results: list[AnalysisResult] = []
        for file_path in file_paths:
            results.append(self.analyze_file(file_path, kpi_group_key=kpi_group_key))
        return results

    def collect_supported_files(self, input_path: str | Path, recursive: bool = False) -> list[Path]:
        path = Path(input_path)
        if path.is_file():
            if path.name.startswith("~$"):
                return []
            return [path]

        if not path.exists():
            raise FileNotFoundError(f"路径不存在: {path}")

        pattern = "**/*" if recursive else "*"
        files = [
            candidate
            for candidate in path.glob(pattern)
            if candidate.is_file() and candidate.suffix.lower() in SUPPORTED_FILE_TYPES and not candidate.name.startswith("~$")
        ]
        return sorted(files)

    @staticmethod
    def summarize_analysis(result: AnalysisResult) -> dict[str, object]:
        statuses = [rule.status for rule in result.rule_results]
        fail_count = statuses.count("fail")
        warning_count = statuses.count("warning")
        pass_count = statuses.count("pass")
        overall_status = "fail" if fail_count else "warning" if warning_count else "pass"

        kpi_lookup = {item.name: item.value for item in result.kpis}
        return {
            "file_name": result.context.source_path.name,
            "file_path": str(result.context.source_path),
            "overall_status": overall_status,
            "analysis_profile": result.context.metadata.get("analysis_profile", "default"),
            "config_path": result.context.metadata.get("config_path"),
            "rule_count": len(result.rule_results),
            "pass_count": pass_count,
            "warning_count": warning_count,
            "fail_count": fail_count,
            "max_slip_kph": kpi_lookup.get("max_slip_kph", 0.0),
            "max_jerk_mps3": kpi_lookup.get("max_jerk_mps3", 0.0),
        }

    def build_batch_summary_frame(self, results: list[AnalysisResult]) -> pd.DataFrame:
        return pd.DataFrame([self.summarize_analysis(result) for result in results])
