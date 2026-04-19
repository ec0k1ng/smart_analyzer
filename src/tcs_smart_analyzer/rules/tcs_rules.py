from __future__ import annotations

import pandas as pd

from tcs_smart_analyzer.config.analysis_settings import AnalysisSettings, load_analysis_settings
from tcs_smart_analyzer.config.editable_configs import load_rule_plugins
from tcs_smart_analyzer.core.models import RuleResult, ScenarioWindow
from tcs_smart_analyzer.rules.base import BaseRule


class PythonRule(BaseRule):
    def __init__(self, plugin: dict[str, object], settings: AnalysisSettings | None = None) -> None:
        super().__init__(settings)
        self.plugin = plugin
        self.definition = dict(plugin["definition"])
        self.rule_id = str(self.definition.get("rule_id", "UNKNOWN"))
        self.category = str(self.definition.get("category", "custom"))
        self.title = str(self.definition.get("title", self.rule_id))

    def evaluate(self, dataframe: pd.DataFrame, scenarios: list[ScenarioWindow]) -> list[RuleResult]:
        scope = str(self.definition.get("scope", "global"))
        if scope == "scenario":
            results: list[RuleResult] = []
            for scenario in scenarios:
                frame = dataframe.iloc[scenario.start_index : scenario.end_index + 1].copy()
                result = self._evaluate_scope(frame, scenarios, scenario)
                if result is not None:
                    results.append(result)
            return results

        result = self._evaluate_scope(dataframe, scenarios, None)
        return [result] if result is not None else []

    def _evaluate_scope(
        self,
        frame: pd.DataFrame,
        scenarios: list[ScenarioWindow],
        scenario: ScenarioWindow | None,
    ) -> RuleResult | None:
        evaluate_rule = self.plugin["evaluate_rule"]
        payload = evaluate_rule(frame, scenarios, scenario, self.settings)
        if payload is None:
            return None
        if not isinstance(payload, dict):
            raise ValueError(f"规则 {self.rule_id} 的 evaluate_rule 必须返回 dict 或 None。")

        return RuleResult(
            rule_id=self.rule_id,
            category=self.category,
            title=self.title,
            status=str(payload.get("status", "fail")),
            severity=str(payload.get("severity", "medium")),
            measured_value=payload.get("measured_value"),
            threshold_value=payload.get("threshold_value"),
            unit=str(self.definition.get("unit", "")),
            message=str(payload.get("message", self.title)),
            scenario_id=scenario.scenario_id if scenario is not None else None,
            start_time=scenario.start_time if scenario is not None else None,
            end_time=scenario.end_time if scenario is not None else None,
            threshold_source=str(payload.get("threshold_source", self.get_threshold_source(str(self.definition.get("source", "fixed"))))),
            confidence=float(payload.get("confidence", 1.0)),
        )


def build_default_rule_set(settings: AnalysisSettings | None = None) -> list[BaseRule]:
    resolved_settings = settings or load_analysis_settings()
    plugins = load_rule_plugins()
    rules = [PythonRule(plugin, resolved_settings) for plugin in plugins]
    return [rule for rule in rules if resolved_settings.is_rule_enabled(rule.rule_id, bool(rule.definition.get("enabled", True)))]
