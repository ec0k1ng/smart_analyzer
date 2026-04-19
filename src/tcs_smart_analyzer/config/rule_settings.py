from __future__ import annotations

import json
from functools import lru_cache
from importlib.resources import files
from typing import Any


@lru_cache(maxsize=1)
def load_rule_settings() -> dict[str, dict[str, Any]]:
    config_path = files("tcs_smart_analyzer.config").joinpath("rule_thresholds.json")
    with config_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def get_rule_threshold(rule_id: str, default: float) -> float:
    settings = load_rule_settings()
    return float(settings.get(rule_id, {}).get("threshold", default))


def get_rule_threshold_source(rule_id: str, default: str = "fixed") -> str:
    settings = load_rule_settings()
    return str(settings.get(rule_id, {}).get("source", default))
