from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass(slots=True)
class AnalysisContext:
    source_path: Path
    dataframe: pd.DataFrame
    mapped_columns: dict[str, str]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class KpiResult:
    name: str
    title: str
    value: float | None
    unit: str
    description: str
    signal_values: pd.Series | None = None
    rule_description: str = ""
    status: str = "pass"
    assessment_message: str = ""
    threshold_value: float | None = None
    threshold_source: str = "kpi_definition"
    pass_condition: str = "True"
    result_label: str = "达标"


@dataclass(slots=True)
class RuleResult:
    rule_id: str
    category: str
    title: str
    status: str
    severity: str
    measured_value: float | None
    threshold_value: float | None
    unit: str
    message: str
    threshold_source: str = "fixed"
    confidence: float = 1.0


@dataclass(slots=True)
class AnalysisResult:
    context: AnalysisContext
    kpis: list[KpiResult]
    rule_results: list[RuleResult]
    normalized_frame: pd.DataFrame
