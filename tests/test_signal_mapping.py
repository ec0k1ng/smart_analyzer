from __future__ import annotations

import unittest
from unittest.mock import patch

import pandas as pd

from tcs_smart_analyzer.core.signal_mapping import SignalMappingError, build_signal_mapping, normalize_signals


class SignalMappingTests(unittest.TestCase):
    @staticmethod
    def _minimal_required_signals() -> list[str]:
        return ["time_s", "wheel_speed_rl_kph", "wheel_speed_rr_kph", "vehicle_speed_kph", "longitudinal_accel_mps2", "tcs_active"]

    def test_build_signal_mapping_uses_manual_interface_mapping(self) -> None:
        columns = [
            "TimeColumn",
            "RearLeftSpeed",
            "RearRightSpeed",
            "VehicleRefSpeed",
            "LongAccColumn",
            "TCSFlagColumn",
        ]
        interface_mapping = {
            "time_s": {"manual_column": "TimeColumn"},
            "wheel_speed_rl_kph": {"manual_column": "RearLeftSpeed"},
            "wheel_speed_rr_kph": {"manual_column": "RearRightSpeed"},
            "vehicle_speed_kph": {"manual_column": "VehicleRefSpeed"},
            "longitudinal_accel_mps2": {"manual_column": "LongAccColumn"},
            "tcs_active": {"manual_column": "TCSFlagColumn"},
        }

        with patch("tcs_smart_analyzer.core.signal_mapping.load_interface_mapping", return_value=interface_mapping):
            mapping = build_signal_mapping(columns, required_signals=self._minimal_required_signals())

        self.assertEqual(mapping["time_s"], "TimeColumn")
        self.assertEqual(mapping["vehicle_speed_kph"], "VehicleRefSpeed")
        self.assertEqual(mapping["longitudinal_accel_mps2"], "LongAccColumn")
        self.assertEqual(mapping["tcs_active"], "TCSFlagColumn")

    def test_normalize_signals_sorts_and_keeps_required_columns(self) -> None:
        frame = pd.DataFrame(
            {
                "TimeColumn": [0.1, 0.0, 0.2],
                "RearLeftSpeed": [1, 0, 2],
                "RearRightSpeed": [1, 0, 2],
                "VehicleRefSpeed": [1, 0, 2],
                "LongAccColumn": [0.0, 0.1, 0.2],
                "TCSFlagColumn": [0, 0, 1],
            }
        )
        interface_mapping = {
            "time_s": {"manual_column": "TimeColumn"},
            "wheel_speed_rl_kph": {"manual_column": "RearLeftSpeed"},
            "wheel_speed_rr_kph": {"manual_column": "RearRightSpeed"},
            "vehicle_speed_kph": {"manual_column": "VehicleRefSpeed"},
            "longitudinal_accel_mps2": {"manual_column": "LongAccColumn"},
            "tcs_active": {"manual_column": "TCSFlagColumn"},
        }

        with patch("tcs_smart_analyzer.core.signal_mapping.load_interface_mapping", return_value=interface_mapping):
            mapping = build_signal_mapping(frame.columns, required_signals=self._minimal_required_signals())
            normalized = normalize_signals(frame, mapping)

        self.assertListEqual(normalized["time_s"].tolist(), [0.0, 0.1, 0.2])
        self.assertNotIn("sample_time_s", normalized.columns)
        self.assertIn("tcs_active", normalized.columns)

    def test_build_signal_mapping_requires_manual_mapping_names(self) -> None:
        frame = pd.DataFrame(
            {
                "time_s": [0.0, 0.001],
                "col_alpha": [10.0, 10.2],
                "col_beta": [10.1, 10.4],
                "col_gamma": [10.1, 10.4],
                "col_delta": [0.0, 0.2],
                "col_epsilon": [0, 1],
            }
        )

        with patch("tcs_smart_analyzer.core.signal_mapping.load_interface_mapping", return_value={}):
            with self.assertRaises(SignalMappingError):
                build_signal_mapping(frame.columns, required_signals=self._minimal_required_signals())

    def test_build_signal_mapping_does_not_fallback_to_standard_column_names(self) -> None:
        frame = pd.DataFrame(
            {
                "time_s": [0.0, 0.1],
                "wheel_speed_rl": [1.0, 1.1],
                "wheel_speed_rr": [1.0, 1.1],
                "vehicle_speed": [1.0, 1.0],
                "longitudinal_accel_mps2": [0.0, 0.1],
                "tcs_active": [0, 1],
            }
        )

        with patch("tcs_smart_analyzer.core.signal_mapping.load_interface_mapping", return_value={}):
            with self.assertRaises(SignalMappingError):
                build_signal_mapping(frame.columns, required_signals=self._minimal_required_signals())

    def test_manual_interface_mapping_overrides_aliases(self) -> None:
        columns = [
            "MyTime",
            "RearLeft",
            "RearRight",
            "VehicleRef",
            "LongAcc",
            "TCSFlag",
        ]

        interface_mapping = {
            "time_s": {"manual_column": "MyTime"},
            "wheel_speed_rl_kph": {"manual_column": "RearLeft"},
            "wheel_speed_rr_kph": {"manual_column": "RearRight"},
            "vehicle_speed_kph": {"manual_column": "VehicleRef"},
            "longitudinal_accel_mps2": {"manual_column": "LongAcc"},
            "tcs_active": {"manual_column": "TCSFlag"},
        }

        with patch("tcs_smart_analyzer.core.signal_mapping.load_interface_mapping", return_value=interface_mapping):
            mapping = build_signal_mapping(columns, required_signals=self._minimal_required_signals())

        self.assertEqual(mapping["time_s"], "MyTime")
        self.assertEqual(mapping["vehicle_speed_kph"], "VehicleRef")
        self.assertEqual(mapping["tcs_active"], "TCSFlag")

    def test_manual_interface_mapping_supports_non_builtin_standard_names(self) -> None:
        columns = ["time", "CustomWheelSlip"]
        interface_mapping = {
            "time_s": {"manual_column": "time"},
            "custom_slip_trace": {"manual_column": "CustomWheelSlip"},
        }

        with patch("tcs_smart_analyzer.core.signal_mapping.load_interface_mapping", return_value=interface_mapping):
            mapping = build_signal_mapping(columns, required_signals=["time_s", "custom_slip_trace"])
            normalized = normalize_signals(pd.DataFrame({"time": [0.0, 0.1], "CustomWheelSlip": [0.2, 0.4]}), mapping)

        self.assertEqual(mapping["custom_slip_trace"], "CustomWheelSlip")
        self.assertIn("custom_slip_trace", normalized.columns)
        self.assertListEqual(normalized["custom_slip_trace"].tolist(), [0.2, 0.4])

    def test_normalize_signals_can_fill_tcs_active_from_wheel_specific_columns(self) -> None:
        frame = pd.DataFrame(
            {
                "time": [0.0, 0.1],
                "whlspd_rl": [1.0, 1.1],
                "whlspd_rr": [1.0, 1.1],
                "veh_spd": [1.0, 1.0],
                "LongAcc": [0.0, 0.0],
                "TcsActiv(1)": [0, 1],
            }
        )

        interface_mapping = {
            "time_s": {"manual_column": "time"},
            "wheel_speed_rl_kph": {"manual_column": "whlspd_rl"},
            "wheel_speed_rr_kph": {"manual_column": "whlspd_rr"},
            "vehicle_speed_kph": {"manual_column": "veh_spd"},
            "longitudinal_accel_mps2": {"manual_column": "LongAcc"},
            "tcs_active_fl": {"manual_column": "TcsActiv(1)"},
        }

        with patch("tcs_smart_analyzer.core.signal_mapping.load_interface_mapping", return_value=interface_mapping):
            mapping = build_signal_mapping(
                frame.columns,
                required_signals=["time_s", "wheel_speed_rl_kph", "wheel_speed_rr_kph", "vehicle_speed_kph", "longitudinal_accel_mps2", "tcs_active_fl"],
            )
            normalized = normalize_signals(frame, mapping)

        self.assertEqual(mapping["tcs_active_fl"], "TcsActiv(1)")
        self.assertIn("tcs_active_fl", normalized.columns)
        self.assertIn("tcs_active", normalized.columns)
        self.assertListEqual(normalized["tcs_active_fl"].tolist(), [0.0, 1.0])
        self.assertListEqual(normalized["tcs_active"].tolist(), [0.0, 1.0])

    def test_manual_time_mapping_does_not_fallback_to_auto_normalized_time_column(self) -> None:
        columns = ["time_s", "wheel_speed_rl", "wheel_speed_rr", "vehicle_speed", "longitudinal_accel_mps2", "tcs_active"]
        interface_mapping = {
            "time_s": {"manual_column": "time1"},
            "wheel_speed_rl_kph": {"manual_column": "wheel_speed_rl"},
            "wheel_speed_rr_kph": {"manual_column": "wheel_speed_rr"},
            "vehicle_speed_kph": {"manual_column": "vehicle_speed"},
            "longitudinal_accel_mps2": {"manual_column": "longitudinal_accel_mps2"},
            "tcs_active": {"manual_column": "tcs_active"},
        }

        with patch("tcs_smart_analyzer.core.signal_mapping.load_interface_mapping", return_value=interface_mapping):
            with self.assertRaises(SignalMappingError):
                build_signal_mapping(columns, required_signals=self._minimal_required_signals())

    def test_explicit_optional_signal_mapping_must_exist(self) -> None:
        columns = ["time_s"]
        interface_mapping = {
            "time_s": {"manual_column": "time_s"},
            "tcs_active_fl": {"manual_column": "TcsActiv(1)1"},
        }

        with patch("tcs_smart_analyzer.core.signal_mapping.load_interface_mapping", return_value=interface_mapping):
            with self.assertRaises(SignalMappingError):
                build_signal_mapping(columns, required_signals=["time_s", "tcs_active_fl"])

    def test_default_alias_style_mapping_does_not_fallback_to_sample_headers(self) -> None:
        columns = [
            "time",
            "SpdVeh",
            "SpdWhl(1)",
            "SpdWhl(2)",
            "SpdWhl(3)",
            "SpdWhl(4)",
            "AgWhlTar(1)",
            "Lgt",
            "YawRate",
            "SteerTar",
            "TcsActiv(1)",
            "TcsActiv(2)",
            "TcsActiv(3)",
            "TcsActiv(4)",
        ]
        interface_mapping = {
            "time_s": {"manual_column": "time", "actual_names": ["time"]},
            "vehicle_speed_kph": {"manual_column": "vehicle_speed", "actual_names": ["vehicle_speed"]},
            "wheel_speed_fl_kph": {"manual_column": "wheel_speed_fl", "actual_names": ["wheel_speed_fl"]},
            "wheel_speed_fr_kph": {"manual_column": "wheel_speed_fr", "actual_names": ["wheel_speed_fr"]},
            "wheel_speed_rl_kph": {"manual_column": "wheel_speed_rl", "actual_names": ["wheel_speed_rl"]},
            "wheel_speed_rr_kph": {"manual_column": "wheel_speed_rr", "actual_names": ["wheel_speed_rr"]},
            "accel_pedal_pct": {"manual_column": "accel_pedal_pct", "actual_names": ["accel_pedal_pct"]},
            "longitudinal_accel_mps2": {"manual_column": "longitudinal_accel_mps2", "actual_names": ["longitudinal_accel_mps2"]},
            "yaw_rate_degps": {"manual_column": "yawrate", "actual_names": ["yawrate"]},
            "steering_wheel_angle_deg": {"manual_column": "steering_wheel_angle_deg", "actual_names": ["steering_wheel_angle_deg"]},
            "tcs_active_fl": {"manual_column": "tcs_active", "actual_names": ["tcs_active"]},
            "tcs_active_fr": {"manual_column": "tcs_active", "actual_names": ["tcs_active"]},
            "tcs_active_rl": {"manual_column": "tcs_active", "actual_names": ["tcs_active"]},
            "tcs_active_rr": {"manual_column": "tcs_active", "actual_names": ["tcs_active"]},
        }

        with patch("tcs_smart_analyzer.core.signal_mapping.load_interface_mapping", return_value=interface_mapping):
            with self.assertRaises(SignalMappingError):
                build_signal_mapping(
                    columns,
                    required_signals=[
                        "time_s",
                        "vehicle_speed_kph",
                        "wheel_speed_fl_kph",
                        "wheel_speed_fr_kph",
                        "wheel_speed_rl_kph",
                        "wheel_speed_rr_kph",
                        "accel_pedal_pct",
                        "longitudinal_accel_mps2",
                        "yaw_rate_degps",
                        "steering_wheel_angle_deg",
                        "tcs_active_fl",
                        "tcs_active_fr",
                        "tcs_active_rl",
                        "tcs_active_rr",
                    ],
                )

    def test_explicit_missing_signal_name_is_reported_directly(self) -> None:
        columns = ["time_s", "vehicle_speed", "accel_pedal_pct", "longitudinal_accel_mps2", "tcs_active"]
        interface_mapping = {
            "yaw_rate_degps": {
                "manual_column": "yaw_rate_degps",
                "actual_names": ["yaw_rate_degps"],
                "source_sheet": "系统信号",
            }
        }

        with patch("tcs_smart_analyzer.core.signal_mapping.load_interface_mapping", return_value=interface_mapping):
            with self.assertRaises(SignalMappingError):
                build_signal_mapping(columns, required_signals=["yaw_rate_degps"])

    def test_explicit_manual_time_mapping_does_not_match_pandas_mangled_duplicate_column(self) -> None:
        columns = ["time", "time.1", "time.2"]
        interface_mapping = {
            "time_s": {"manual_column": "time1"},
        }

        with patch("tcs_smart_analyzer.core.signal_mapping.load_interface_mapping", return_value=interface_mapping):
            with self.assertRaises(SignalMappingError):
                build_signal_mapping(columns, required_signals=["time_s"])

    def test_explicit_manual_time_mapping_accepts_loader_normalized_time_alias(self) -> None:
        columns = ["time_s", "vehicle_speed"]
        interface_mapping = {
            "time_s": {"manual_column": "time"},
            "vehicle_speed_kph": {"manual_column": "vehicle_speed"},
        }

        with patch("tcs_smart_analyzer.core.signal_mapping.load_interface_mapping", return_value=interface_mapping):
            mapping = build_signal_mapping(
                columns,
                required_signals=["time_s", "vehicle_speed_kph"],
                source_column_redirects={"time": "time_s"},
                source_columns_before_time_normalization=["time", "vehicle_speed"],
            )

        self.assertEqual(mapping["time_s"], "time_s")

    def test_wrong_manual_time_s_name_does_not_match_loader_normalized_time_column(self) -> None:
        columns = ["time_s", "vehicle_speed"]
        interface_mapping = {
            "time_s": {"manual_column": "time_s"},
            "vehicle_speed_kph": {"manual_column": "vehicle_speed"},
        }

        with patch("tcs_smart_analyzer.core.signal_mapping.load_interface_mapping", return_value=interface_mapping):
            with self.assertRaises(SignalMappingError):
                build_signal_mapping(
                    columns,
                    required_signals=["time_s", "vehicle_speed_kph"],
                    source_column_redirects={"time": "time_s"},
                    source_columns_before_time_normalization=["time", "vehicle_speed"],
                )

    def test_manual_mapping_uses_left_to_right_priority(self) -> None:
        columns = ["BackupSpeed", "PrimarySpeed", "time_s"]
        interface_mapping = {
            "time_s": {"manual_column": "time_s"},
            "vehicle_speed_kph": {"actual_names": ["MissingSpeed", "BackupSpeed", "PrimarySpeed"]},
        }

        with patch("tcs_smart_analyzer.core.signal_mapping.load_interface_mapping", return_value=interface_mapping):
            mapping = build_signal_mapping(columns, required_signals=["time_s", "vehicle_speed_kph"])

        self.assertEqual(mapping["vehicle_speed_kph"], "BackupSpeed")

    def test_manual_mapping_can_use_formula_expression(self) -> None:
        frame = pd.DataFrame(
            {
                "time_ms": [0.0, 100.0, 200.0],
                "vehicle_speed": [1.0, 2.0, 3.0],
            }
        )
        interface_mapping = {
            "time_s": {"manual_column": "time_ms*0.001"},
            "vehicle_speed_kph": {"manual_column": "vehicle_speed"},
        }

        with patch("tcs_smart_analyzer.core.signal_mapping.load_interface_mapping", return_value=interface_mapping):
            mapping = build_signal_mapping(frame.columns, required_signals=["time_s", "vehicle_speed_kph"])
            normalized = normalize_signals(frame, mapping)

        self.assertEqual(mapping["time_s"], "expr:time_ms*0.001")
        self.assertListEqual(normalized["time_s"].tolist(), [0.0, 0.1, 0.2])


if __name__ == "__main__":
    unittest.main()
