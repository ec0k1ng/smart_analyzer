from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from tcs_smart_analyzer.config.analysis_settings import AnalysisSettings, load_analysis_settings
from tcs_smart_analyzer.core.models import RuleResult, ScenarioWindow


class BaseRule(ABC):
    rule_id: str
    category: str
    title: str

    def __init__(self, settings: AnalysisSettings | None = None) -> None:
        self.settings = settings or load_analysis_settings()

    def get_threshold(self, default: float) -> float:
        return self.settings.get_rule_threshold(self.rule_id, default)

    def get_threshold_source(self, default: str = "fixed") -> str:
        return self.settings.get_rule_threshold_source(self.rule_id, default)

    @abstractmethod
    def evaluate(self, dataframe: pd.DataFrame, scenarios: list[ScenarioWindow]) -> list[RuleResult]:
        raise NotImplementedError
