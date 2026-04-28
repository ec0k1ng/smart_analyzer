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
from tcs_smart_analyzer.core.signal_mapping import build_signal_mapping, normalize_signals, resolve_requested_signal_names
from tcs_smart_analyzer.data.loaders import SUPPORTED_FILE_TYPES, load_timeseries_file
from tcs_smart_analyzer.data.resampler import detect_and_resample


class AnalysisEngine:
    def __init__(self, settings: AnalysisSettings | None = None, kpi_group_key: str | None = None, runtime_logger=None) -> None:
        sync_interface_mapping_file()
        self.settings = settings or load_analysis_settings()
        self.kpi_group_key = kpi_group_key
        self.runtime_logger = runtime_logger
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
        required_signals = {
            str(signal_name).strip()
            for definition in self.kpi_definitions
            for signal_name in definition.get("raw_inputs", [])
            if str(signal_name).strip()
        }
        for definition in self.derived_signal_definitions:
            for signal_name in definition.get("raw_inputs", []):
                normalized_name = str(signal_name).strip()
                if normalized_name:
                    required_signals.add(normalized_name)
        return sorted(required_signals)

    def analyze_file(self, file_path: str | Path, kpi_group_key: str | None = None) -> AnalysisResult:
        if kpi_group_key != self.kpi_group_key:
            self.reload_runtime_definitions(kpi_group_key=kpi_group_key)
        source_path = Path(file_path)
        generated_at = datetime.now().astimezone().isoformat(timespec="seconds")
        dataframe = load_timeseries_file(
            source_path,
            required_signals=resolve_requested_signal_names(self.required_raw_input_signals),
        )
        dataframe.attrs["source_path"] = str(source_path)
        dataframe.attrs["source_name"] = source_path.name
        dataframe.attrs["source_stem"] = source_path.stem
        dataframe.attrs["analysis_profile"] = self.settings.profile_name
        dataframe.attrs["generated_at"] = generated_at
        mapping = build_signal_mapping(dataframe.columns, self.required_raw_input_signals)
        dataframe.attrs["mapped_columns"] = dict(mapping)
        normalized = normalize_signals(dataframe, mapping)
        normalized.attrs.update(dataframe.attrs)
        normalized = detect_and_resample(normalized, time_column="time_s")
        normalized.attrs.update(dataframe.attrs)
        normalized = attach_derived_signal_columns(
            normalized,
            self.kpi_definitions,
            self.derived_signal_plugins,
            runtime_logger=self.runtime_logger,
        )
        normalized.attrs.update(dataframe.attrs)
        kpis = calculate_global_kpis(normalized, self.settings, self.kpi_plugins, runtime_logger=self.runtime_logger)
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
