from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tcs_smart_analyzer.config.editable_configs import build_default_rule_settings
from tcs_smart_analyzer.config.rule_settings import load_rule_settings


@dataclass(slots=True)
class AnalysisSettings:
    profile_name: str = "default"
    rule_settings: dict[str, dict[str, Any]] = field(default_factory=load_rule_settings)
    config_path: Path | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def default(cls) -> AnalysisSettings:
        base_settings = build_default_rule_settings()
        legacy_settings = deepcopy(load_rule_settings())
        for rule_id, settings in legacy_settings.items():
            base_settings.setdefault(rule_id, {}).update(settings)
        return cls(rule_settings=base_settings)

    @classmethod
    def from_file(cls, config_path: str | Path) -> AnalysisSettings:
        path = Path(config_path).expanduser().resolve()
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("分析配置文件必须是 JSON 对象。")

        rules = raw.get("rules", raw.get("kpis", {}))
        if not isinstance(rules, dict):
            raise ValueError("分析配置文件中的 rules/kpis 必须是 JSON 对象。")

        metadata = raw.get("metadata", {})
        if not isinstance(metadata, dict):
            raise ValueError("分析配置文件中的 metadata 必须是 JSON 对象。")

        merged_rules = cls.default().rule_settings
        for rule_id, override in rules.items():
            if not isinstance(override, dict):
                raise ValueError(f"KPI/规则 {rule_id} 的配置必须是 JSON 对象。")
            target = merged_rules.setdefault(str(rule_id), {})
            for key in ("threshold", "source", "enabled", "unit"):
                if key in override:
                    target[key] = override[key]

        return cls(
            profile_name=str(raw.get("profile_name", path.stem)),
            rule_settings=merged_rules,
            config_path=path,
            metadata=metadata,
        )

    def get_rule_threshold(self, rule_id: str, default: float) -> float:
        return float(self.rule_settings.get(rule_id, {}).get("threshold", default))

    def get_rule_threshold_source(self, rule_id: str, default: str = "fixed") -> str:
        return str(self.rule_settings.get(rule_id, {}).get("source", default))

    def is_rule_enabled(self, rule_id: str, default: bool = True) -> bool:
        return bool(self.rule_settings.get(rule_id, {}).get("enabled", default))

    def export_rule_settings(self) -> dict[str, dict[str, Any]]:
        return deepcopy(self.rule_settings)


def load_analysis_settings(config_path: str | Path | None = None) -> AnalysisSettings:
    if config_path is None:
        return AnalysisSettings.default()
    return AnalysisSettings.from_file(config_path)