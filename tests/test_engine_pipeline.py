from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import NamedTemporaryFile

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
                {"standard_signal": "wheel_speed_fl_kph", "actual_names": ["wheel_speed_fl"]},
                {"standard_signal": "wheel_speed_fr_kph", "actual_names": ["wheel_speed_fr"]},
                {"standard_signal": "wheel_speed_rl_kph", "actual_names": ["wheel_speed_rl"]},
                {"standard_signal": "wheel_speed_rr_kph", "actual_names": ["wheel_speed_rr"]},
                {"standard_signal": "vehicle_speed_kph", "actual_names": ["vehicle_speed"]},
                {"standard_signal": "accel_pedal_pct", "actual_names": ["accel_pedal_pct"]},
                {"standard_signal": "brake_depth_pct", "actual_names": ["brake_depth_pct"]},
                {"standard_signal": "torque_request_nm", "actual_names": ["torque_request_nm"]},
                {"standard_signal": "torque_actual_nm", "actual_names": ["torque_actual_nm"]},
                {"standard_signal": "longitudinal_accel_mps2", "actual_names": ["longitudinal_accel_mps2"]},
                {"standard_signal": "yaw_rate_degps", "actual_names": ["yawrate"]},
                {"standard_signal": "steering_wheel_angle_deg", "actual_names": ["steering_wheel_angle_deg"]},
                {"standard_signal": "tcs_active", "actual_names": ["tcs_active"]},
                {"standard_signal": "tcs_active_fl", "actual_names": ["tcs_active"]},
                {"standard_signal": "tcs_active_fr", "actual_names": ["tcs_active"]},
                {"standard_signal": "tcs_active_rl", "actual_names": ["tcs_active"]},
                {"standard_signal": "tcs_active_rr", "actual_names": ["tcs_active"]},
            ],
            [],
        )

    def _create_demo_input_file(self) -> Path:
        frame = pd.DataFrame(
            {
                "time_s": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5],
                "wheel_speed_fl": [0.0, 6.0, 12.0, 17.0, 20.5, 22.0],
                "wheel_speed_fr": [0.0, 6.2, 12.1, 17.1, 20.4, 22.1],
                "wheel_speed_rl": [0.0, 6.8, 13.8, 18.5, 21.2, 22.4],
                "wheel_speed_rr": [0.0, 6.7, 13.6, 18.2, 21.0, 22.2],
                "vehicle_speed": [0.0, 5.8, 11.8, 16.8, 20.0, 22.0],
                "accel_pedal_pct": [20.0, 45.0, 88.0, 92.0, 95.0, 96.0],
                "brake_depth_pct": [0.0] * 6,
                "torque_request_nm": [0.0, 50.0, 120.0, 180.0, 220.0, 230.0],
                "torque_actual_nm": [0.0, 48.0, 115.0, 175.0, 215.0, 225.0],
                "longitudinal_accel_mps2": [0.0, 1.2, 2.8, 4.4, 4.7, 4.3],
                "yawrate": [0.0, 0.8, 1.6, 2.9, 4.2, 3.1],
                "steering_wheel_angle_deg": [0.0, 2.0, 4.5, 7.0, 10.0, 8.0],
                "tcs_active": [0, 0, 1, 1, 1, 0],
            }
        )
        temp_file = NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8", newline="")
        frame.to_csv(temp_file.name, index=False)
        temp_file.close()
        self.addCleanup(lambda: Path(temp_file.name).unlink(missing_ok=True))
        return Path(temp_file.name)

    def tearDown(self) -> None:
        if self._interface_mapping_backup is None:
            if self._interface_mapping_path.exists():
                self._interface_mapping_path.unlink()
            return
        self._interface_mapping_path.write_bytes(self._interface_mapping_backup)

    def test_demo_file_produces_kpi_assessments(self) -> None:
        demo_file = self._create_demo_input_file()

        engine = AnalysisEngine()
        result = engine.analyze_file(demo_file)

        kpi_names = {item.name for item in result.kpis}
        self.assertTrue(
            {
                "max_jerk_mps3",
                "max_slip_kph",
                "mean_full_brake_decel_mps2",
                "tcs_ctrl_time_max_s",
                "max_yaw_rate_degps",
                "max_steer_angle_deg",
                "mean_full_throttle_accel_mps2",
            }.issubset(kpi_names)
        )
        self.assertGreaterEqual(len(result.rule_results), 7)
        self.assertIn("slip_kph", result.normalized_frame.columns)
        self.assertIn("tcs_target_slip_kph", result.normalized_frame.columns)
        populate_kpi_signal_values(result.normalized_frame, result.kpis, group_key=str(result.context.metadata.get("kpi_group_key", "__all_kpis__")))
        max_slip_kph = next(item for item in result.kpis if item.name == "max_slip_kph")
        self.assertIsNotNone(max_slip_kph.signal_values)
        self.assertEqual(len(max_slip_kph.signal_values), len(result.normalized_frame))
        mean_full_brake_decel = next(item for item in result.kpis if item.name == "mean_full_brake_decel_mps2")
        self.assertIsNotNone(mean_full_brake_decel.signal_values)
        self.assertTrue(mean_full_brake_decel.signal_values.isna().all())

    def test_engine_can_filter_kpis_by_group(self) -> None:
        demo_file = self._create_demo_input_file()
        save_kpi_group("最小分组", ["max_slip_kph", "max_jerk_mps3"], key="minimal_group")
        try:
            engine = AnalysisEngine(kpi_group_key="minimal_group")
            result = engine.analyze_file(demo_file, kpi_group_key="minimal_group")

            self.assertEqual([item.name for item in result.kpis], ["max_slip_kph", "max_jerk_mps3"])
            self.assertEqual(result.context.metadata.get("kpi_group_key"), "minimal_group")
        finally:
            delete_kpi_group("minimal_group")

    def test_engine_runtime_logger_captures_plugin_prints(self) -> None:
        demo_file = self._create_demo_input_file()
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
    "raw_inputs": ["vehicle_speed_kph"],
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
    return float(pd.to_numeric(dataframe["vehicle_speed_kph"], errors="coerce").fillna(0.0).mean())

def calculate_kpi_series(dataframe):
    print("temp logger from calculate_kpi_series")
    return pd.to_numeric(dataframe["vehicle_speed_kph"], errors="coerce")
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
    "raw_inputs": ["vehicle_speed_kph"],
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
    return dataframe["vehicle_speed_kph"]
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
