from __future__ import annotations

import unittest
from pathlib import Path

import pandas as pd

from tcs_smart_analyzer.config.editable_configs import delete_kpi_group, get_config_file_paths, save_interface_signal_tables, save_kpi_group
from tcs_smart_analyzer.core.engine import AnalysisEngine
from tcs_smart_analyzer.core.features import populate_kpi_signal_values


class EnginePipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        config_paths = get_config_file_paths()
        self._interface_mapping_path = config_paths["interface_mapping"]
        self._interface_mapping_backup = self._interface_mapping_path.read_bytes() if self._interface_mapping_path.exists() else None
        save_interface_signal_tables(
            [
                {"standard_signal": "time_s", "actual_names": ["time_s"]},
                {"standard_signal": "wheel_speed_fl", "actual_names": ["wheel_speed_fl"]},
                {"standard_signal": "wheel_speed_fr", "actual_names": ["wheel_speed_fr"]},
                {"standard_signal": "wheel_speed_rl", "actual_names": ["wheel_speed_rl"]},
                {"standard_signal": "wheel_speed_rr", "actual_names": ["wheel_speed_rr"]},
                {"standard_signal": "vehicle_speed", "actual_names": ["vehicle_speed"]},
                {"standard_signal": "accel_pedal_pct", "actual_names": ["accel_pedal_pct"]},
                {"standard_signal": "torque_request_nm", "actual_names": ["torque_request_nm"]},
                {"standard_signal": "torque_actual_nm", "actual_names": ["torque_actual_nm"]},
                {"standard_signal": "brake_pressure_fl_bar", "actual_names": ["brake_pressure_fl_bar"]},
                {"standard_signal": "brake_pressure_fr_bar", "actual_names": ["brake_pressure_fr_bar"]},
                {"standard_signal": "longitudinal_accel_mps2", "actual_names": ["longitudinal_accel_mps2"]},
                {"standard_signal": "tcs_active", "actual_names": ["tcs_active"]},
            ],
            [],
        )

    def tearDown(self) -> None:
        if self._interface_mapping_backup is None:
            if self._interface_mapping_path.exists():
                self._interface_mapping_path.unlink()
            return
        self._interface_mapping_path.write_bytes(self._interface_mapping_backup)

    def test_demo_file_produces_kpi_assessments(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        demo_file = project_root / "sample_data" / "tcs_demo.csv"

        engine = AnalysisEngine()
        result = engine.analyze_file(demo_file)

        kpi_names = {item.name for item in result.kpis}
        self.assertTrue({"max_jerk_mps3", "max_slip_speed", "mean_vehicle_speed_kph", "peak_slip_ratio"}.issubset(kpi_names))
        self.assertGreaterEqual(len(result.rule_results), 4)
        self.assertIn("peak_slip_ratio", {item.name for item in result.kpis})
        self.assertIn("slip_ratio", result.normalized_frame.columns)
        populate_kpi_signal_values(result.normalized_frame, result.kpis, group_key=str(result.context.metadata.get("kpi_group_key", "__all_kpis__")))
        peak_slip_ratio = next(item for item in result.kpis if item.name == "peak_slip_ratio")
        self.assertIsNotNone(peak_slip_ratio.signal_values)
        self.assertEqual(len(peak_slip_ratio.signal_values), len(result.normalized_frame))
        mean_vehicle_speed = next(item for item in result.kpis if item.name == "mean_vehicle_speed_kph")
        self.assertIsNotNone(mean_vehicle_speed.signal_values)
        self.assertAlmostEqual(float(mean_vehicle_speed.signal_values.iloc[-1]), mean_vehicle_speed.value, places=6)

    def test_engine_can_filter_kpis_by_group(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        demo_file = project_root / "sample_data" / "tcs_demo.csv"
        save_kpi_group("最小分组", ["peak_slip_ratio", "max_jerk_mps3"], key="minimal_group")
        try:
            engine = AnalysisEngine(kpi_group_key="minimal_group")
            result = engine.analyze_file(demo_file, kpi_group_key="minimal_group")

            self.assertEqual({item.name for item in result.kpis}, {"peak_slip_ratio", "max_jerk_mps3"})
            self.assertEqual(result.context.metadata.get("kpi_group_key"), "minimal_group")
        finally:
            delete_kpi_group("minimal_group")

    def test_engine_runtime_logger_captures_plugin_prints(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        demo_file = project_root / "sample_data" / "tcs_demo.csv"
        captured_logs: list[tuple[str, str]] = []
        config_paths = get_config_file_paths()
        temp_kpi_path = config_paths["kpi_specs_dir"] / "temp_print_logger_kpi.py"
        temp_kpi_path.write_text(
            '''from __future__ import annotations

IS_TEMPLATE = False

import pandas as pd

KPI_DEFINITION = {
    "name": "temp_print_logger_kpi",
    "title": "日志打印测试KPI",
    "raw_inputs": ["vehicle_speed"],
    "derived_inputs": [],
    "trend_source": "temp_print_logger_kpi",
    "unit": "kph",
    "description": "验证print输出被运行日志捕获。",
    "threshold": 9999.0,
    "source": "test",
    "pass_condition": "value <= threshold",
    "rule_description": "test",
    "pass_message": "pass",
    "fail_message": "fail",
}

def calculate_kpi(dataframe):
    print("temp logger from calculate_kpi")
    return float(pd.to_numeric(dataframe["vehicle_speed"], errors="coerce").fillna(0.0).mean())

def calculate_kpi_series(dataframe):
    print("temp logger from calculate_kpi_series")
    return pd.to_numeric(dataframe["vehicle_speed"], errors="coerce")
''',
            encoding="utf-8",
        )
        try:
            engine = AnalysisEngine(runtime_logger=lambda level, message: captured_logs.append((level, message)))
            engine.analyze_file(demo_file)

            self.assertTrue(any(level == "info" and "temp_print_logger_kpi:calculate_kpi" in message for level, message in captured_logs))
            self.assertTrue(any(level == "info" and "temp_print_logger_kpi:calculate_kpi_series" in message for level, message in captured_logs))
        finally:
            if temp_kpi_path.exists():
                temp_kpi_path.unlink()

    def test_invalid_kpi_dependency_does_not_block_engine_startup(self) -> None:
        config_paths = get_config_file_paths()
        temp_kpi_path = config_paths["kpi_specs_dir"] / "temp_invalid_dependency_kpi.py"
        temp_kpi_path.write_text(
            '''from __future__ import annotations

IS_TEMPLATE = False

KPI_DEFINITION = {
    "name": "temp_invalid_dependency_kpi",
    "title": "坏依赖KPI",
    "raw_inputs": ["vehicle_speed"],
    "derived_inputs": ["missing_derived_signal_for_engine_test"],
    "trend_source": "temp_invalid_dependency_kpi",
    "unit": "",
    "description": "测试引擎启动容错。",
    "threshold": 0.0,
    "source": "test",
    "pass_condition": "value >= threshold",
    "rule_description": "test",
    "pass_message": "pass",
    "fail_message": "fail",
}

def calculate_kpi(dataframe):
    return 0.0

def calculate_kpi_series(dataframe):
    return dataframe["vehicle_speed"]
''',
            encoding="utf-8",
        )
        try:
            engine = AnalysisEngine()

            self.assertNotIn("temp_invalid_dependency_kpi", {item["name"] for item in engine.kpi_definitions})
            self.assertTrue(any("missing_derived_signal_for_engine_test" in issue.message for issue in engine.invalid_runtime_issues))
        finally:
            if temp_kpi_path.exists():
                temp_kpi_path.unlink()


if __name__ == "__main__":
    unittest.main()
