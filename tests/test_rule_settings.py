from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tcs_smart_analyzer.config import get_rule_threshold, get_rule_threshold_source, load_analysis_settings, load_rule_settings
from tcs_smart_analyzer.config.editable_configs import build_default_rule_settings


class RuleSettingsTests(unittest.TestCase):
    def test_rule_thresholds_are_available(self) -> None:
        settings = load_rule_settings()

        self.assertIn("PERF-001", settings)
        self.assertAlmostEqual(get_rule_threshold("PERF-001", 0.0), 0.18)
        self.assertEqual(get_rule_threshold_source("STB-001", "fixed"), "historical_recommendation")

    def test_default_kpi_threshold_settings_are_available(self) -> None:
        settings = build_default_rule_settings()

        self.assertIn("max_slip_kph", settings)
        self.assertAlmostEqual(float(settings["max_slip_kph"]["threshold"]), 30.0)
        self.assertEqual(settings["max_jerk_mps3"]["source"], "migrated_from_stb_001")

    def test_analysis_profile_overrides_thresholds_and_enabled_rules(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "analysis_profile.json"
            config_path.write_text(
                json.dumps(
                    {
                        "profile_name": "test_profile",
                        "metadata": {"vehicle_program": "A01"},
                        "rules": {
                            "PERF-001": {"threshold": 0.12, "source": "vehicle_A01"},
                            "STB-002": {"enabled": False},
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            settings = load_analysis_settings(config_path)

            self.assertEqual(settings.profile_name, "test_profile")
            self.assertEqual(settings.metadata["vehicle_program"], "A01")
            self.assertAlmostEqual(settings.get_rule_threshold("PERF-001", 0.0), 0.12)
            self.assertEqual(settings.get_rule_threshold_source("PERF-001", "fixed"), "vehicle_A01")
            self.assertFalse(settings.is_rule_enabled("STB-002", True))


if __name__ == "__main__":
    unittest.main()
