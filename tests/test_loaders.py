from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, call, patch

import pandas as pd

from tcs_smart_analyzer.data.loaders import (
    SUPPORTED_FILE_TYPES,
    UnsupportedFileTypeError,
    _build_bus_frame_from_timeseries,
    _build_can_message_lookup,
    _decode_can_message,
    _load_can_databases,
    load_timeseries_file,
)


class _FakeSignal:
    def __init__(self, name: str) -> None:
        self.name = name


class _FakeMessage:
    def __init__(self, frame_id: int, signal_names: list[str], decoded: dict[str, object]) -> None:
        self.frame_id = frame_id
        self.signals = [_FakeSignal(name) for name in signal_names]
        self._decoded = decoded
        self.decode_calls = 0

    def decode(self, payload: bytes, decode_choices: bool = False) -> dict[str, object]:  # noqa: ARG002
        self.decode_calls += 1
        return dict(self._decoded)


class _FakeDatabase:
    def __init__(self, messages: list[_FakeMessage]) -> None:
        self.messages = messages


class LoaderTests(unittest.TestCase):
    def test_supported_file_types_include_dat_and_blf(self) -> None:
        self.assertIn(".dat", SUPPORTED_FILE_TYPES)
        self.assertIn(".blf", SUPPORTED_FILE_TYPES)

    def test_text_dat_file_can_be_loaded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "sample.dat"
            path.write_text("time_s\twheel_speed_fl\n0.0\t10\n0.1\t12\n", encoding="utf-8")

            dataframe = load_timeseries_file(path)

            self.assertEqual(list(dataframe.columns), ["time_s", "wheel_speed_fl"])
            self.assertEqual(len(dataframe), 2)

    def test_dat_protocol_suffix_is_removed_from_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "sample.dat"
            path.write_text(
                "time_s\tETCS_VSE_s_SpdWhlCorrFrLe_kmph\\XCP: 1\twheel_speed_fr\\CCP: 2\n0.0\t10\t11\n0.1\t12\t13\n",
                encoding="utf-8",
            )

            dataframe = load_timeseries_file(path)

            self.assertEqual(
                list(dataframe.columns),
                ["time_s", "ETCS_VSE_s_SpdWhlCorrFrLe_kmph", "wheel_speed_fr"],
            )

    def test_wps_style_csv_with_gb18030_and_semicolon_can_be_loaded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "sample.csv"
            path.write_bytes("time_s;wheel_speed_fl\n0,0;10\n0,1;12\n".encode("gb18030"))

            dataframe = load_timeseries_file(path)

            self.assertEqual(list(dataframe.columns), ["time_s", "wheel_speed_fl"])
            self.assertEqual(len(dataframe), 2)
            self.assertAlmostEqual(float(dataframe.iloc[1]["wheel_speed_fl"]), 12.0)

    def test_csv_loading_only_keeps_requested_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "sample.csv"
            path.write_text("Timestamp,wheel_speed_fl,unused_signal\n0.0,10,99\n0.1,12,98\n", encoding="utf-8")

            dataframe = load_timeseries_file(path, required_signals={"time_s", "wheel_speed_fl"})

            self.assertEqual(list(dataframe.columns), ["time_s", "wheel_speed_fl"])
            self.assertNotIn("unused_signal", dataframe.columns)

    def test_xlsx_file_can_be_loaded_with_explicit_engine_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "sample.xlsx"
            pd.DataFrame({"time_s": [0.0, 0.1], "wheel_speed_fl": [10, 12]}).to_excel(path, index=False)

            dataframe = load_timeseries_file(path)

            self.assertEqual(list(dataframe.columns), ["time_s", "wheel_speed_fl"])
            self.assertEqual(len(dataframe), 2)

    def test_xlsx_loading_only_keeps_requested_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "sample.xlsx"
            pd.DataFrame({"time_s": [0.0, 0.1], "wheel_speed_fl": [10, 12], "unused_signal": [99, 98]}).to_excel(path, index=False)

            dataframe = load_timeseries_file(path, required_signals={"time_s", "wheel_speed_fl"})

            self.assertEqual(list(dataframe.columns), ["time_s", "wheel_speed_fl"])
            self.assertNotIn("unused_signal", dataframe.columns)

    def test_text_payload_named_xlsx_falls_back_to_delimited_reader(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "sample.xlsx"
            path.write_text("time_s,wheel_speed_fl\n0.0,10\n0.1,12\n", encoding="utf-8")

            dataframe = load_timeseries_file(path)

            self.assertEqual(list(dataframe.columns), ["time_s", "wheel_speed_fl"])
            self.assertEqual(len(dataframe), 2)

    def test_time_column_is_normalized_to_time_s(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "sample.csv"
            path.write_text("Timestamp,wheel_speed_fl\n0.0,10\n0.1,12\n", encoding="utf-8")

            dataframe = load_timeseries_file(path)

            self.assertEqual(list(dataframe.columns), ["time_s", "wheel_speed_fl"])
            self.assertAlmostEqual(float(dataframe.iloc[1]["time_s"]), 0.1)

    def test_dat_loading_only_keeps_requested_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "sample.dat"
            path.write_text("time_s\twheel_speed_fl\tunused_signal\n0.0\t10\t99\n0.1\t12\t98\n", encoding="utf-8")

            dataframe = load_timeseries_file(path, required_signals={"time_s", "wheel_speed_fl"})

            self.assertEqual(list(dataframe.columns), ["time_s", "wheel_speed_fl"])
            self.assertNotIn("unused_signal", dataframe.columns)

    def test_binary_dat_file_raises_helpful_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "binary.dat"
            path.write_bytes(b"\x00\x01\x02\x03")

            with self.assertRaises(UnsupportedFileTypeError) as context:
                load_timeseries_file(path)

            self.assertIn("测量文件格式", str(context.exception))

    def test_binary_dat_can_fallback_to_measurement_loader(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "binary.dat"
            path.write_bytes(b"\x00\x01\x02\x03")

            with patch("tcs_smart_analyzer.data.loaders._load_mdf_file", return_value=pd.DataFrame({"time_s": [0.0], "wheel_speed_fl": [1.0]})):
                dataframe = load_timeseries_file(path)

            self.assertEqual(list(dataframe.columns), ["time_s", "wheel_speed_fl"])

    def test_mat_loader_receives_requested_signals_and_filters_result(self) -> None:
        expected = {"time_s", "wheel_speed_fl"}
        with patch(
            "tcs_smart_analyzer.data.loaders._load_mat_file",
            return_value=pd.DataFrame({"time_s": [0.0], "wheel_speed_fl": [1.0], "unused_signal": [2.0]}),
        ) as loader_mock:
            dataframe = load_timeseries_file("/tmp/sample.mat", required_signals=expected)

        loader_mock.assert_called_once_with(Path("/tmp/sample.mat"), required_signals=expected)
        self.assertEqual(list(dataframe.columns), ["time_s", "wheel_speed_fl"])

    def test_mdf_loader_receives_requested_signals_and_filters_result(self) -> None:
        expected = {"time_s", "wheel_speed_fl"}
        with patch(
            "tcs_smart_analyzer.data.loaders._load_mdf_file",
            return_value=pd.DataFrame({"time_s": [0.0], "wheel_speed_fl": [1.0], "unused_signal": [2.0]}),
        ) as loader_mock:
            dataframe = load_timeseries_file("/tmp/sample.mf4", required_signals=expected)

        loader_mock.assert_called_once_with(Path("/tmp/sample.mf4"), required_signals=expected)
        self.assertEqual(list(dataframe.columns), ["time_s", "wheel_speed_fl"])

    def test_non_text_dat_without_null_bytes_can_fallback_to_measurement_loader(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "inca.dat"
            path.write_bytes(b"MEASUREMENT-DAT-FORMAT")

            with patch("tcs_smart_analyzer.data.loaders._load_mdf_file", return_value=pd.DataFrame({"time_s": [0.0], "wheel_speed_fl": [1.0]})):
                dataframe = load_timeseries_file(path)

            self.assertEqual(list(dataframe.columns), ["time_s", "wheel_speed_fl"])

    def test_nonstandard_excel_reports_protection_or_format_hint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "sample.xlsx"
            path.write_bytes(b"not-a-real-excel-file")

            with self.assertRaises(UnsupportedFileTypeError) as context:
                load_timeseries_file(path)

            self.assertIn("受保护/加密", str(context.exception))

    def test_load_can_databases_uses_non_strict_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            dbc_path = Path(tmp_dir) / "sample.dbc"
            dbc_path.write_text("VERSION \"\"", encoding="utf-8")
            cantools_mock = Mock()
            cantools_mock.database.load_file.return_value = object()

            databases, dbc_paths, errors = _load_can_databases(dbc_path.with_suffix(".blf"), cantools_mock)

            self.assertGreaterEqual(len(databases), 1)
            self.assertIn(dbc_path, dbc_paths)
            self.assertEqual(errors, [])
            self.assertIn(call(str(dbc_path), strict=False), cantools_mock.database.load_file.call_args_list)

    def test_build_bus_frame_from_timeseries_aligns_gap_mask_with_float_index(self) -> None:
        dataframe = _build_bus_frame_from_timeseries(
            {
                "wheel_speed_fl": ([0.0, 0.5], [10.0, 12.0]),
                "vehicle_speed": ([0.1, 0.2, 0.3, 0.4, 0.5], [1.0, 1.0, 1.0, 1.0, 1.0]),
            },
            "BLF",
        )

        series = dataframe.set_index("time_s")["wheel_speed_fl"]
        self.assertEqual(float(series.loc[0.1]), 10.0)
        self.assertTrue(pd.isna(series.loc[0.3]))
        self.assertTrue(pd.isna(series.loc[0.4]))
        self.assertEqual(float(series.loc[0.5]), 12.0)

    def test_can_decoder_lookup_only_keeps_requested_signals(self) -> None:
        target_message = _FakeMessage(
            0x123,
            ["wheel_speed_fl", "wheel_speed_fr"],
            {"wheel_speed_fl": 10.0, "wheel_speed_fr": 11.0},
        )
        skipped_message = _FakeMessage(0x456, ["engine_speed"], {"engine_speed": 1234.0})
        lookup = _build_can_message_lookup([_FakeDatabase([target_message, skipped_message])], {"wheel_speed_fl"})

        decoded = _decode_can_message(0x123, b"\x00" * 8, lookup)

        self.assertEqual(decoded, {"wheel_speed_fl": 10.0})
        self.assertEqual(target_message.decode_calls, 1)
        self.assertEqual(skipped_message.decode_calls, 0)


if __name__ == "__main__":
    unittest.main()
