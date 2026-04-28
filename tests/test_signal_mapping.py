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

    def test_build_signal_mapping_falls_back_to_exact_standard_column_names(self) -> None:
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
            mapping = build_signal_mapping(frame.columns, required_signals=self._minimal_required_signals())

        self.assertEqual(mapping["time_s"], "time_s")
        self.assertEqual(mapping["vehicle_speed_kph"], "vehicle_speed")
        self.assertEqual(mapping["tcs_active"], "tcs_active")

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

    def test_wheel_specific_tcs_signal_can_satisfy_tcs_active_and_be_normalized(self) -> None:
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
            mapping = build_signal_mapping(frame.columns, required_signals=self._minimal_required_signals())
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
            mapping = build_signal_mapping(columns, required_signals=["time_s", "vehicle_speed_kph"])

        self.assertEqual(mapping["time_s"], "time_s")

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
