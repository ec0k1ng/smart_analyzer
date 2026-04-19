from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, call, patch

import pandas as pd

from tcs_smart_analyzer.data.loaders import SUPPORTED_FILE_TYPES, UnsupportedFileTypeError, _load_can_databases, load_timeseries_file


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

    def test_wps_style_csv_with_gb18030_and_semicolon_can_be_loaded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "sample.csv"
            path.write_bytes("time_s;wheel_speed_fl\n0,0;10\n0,1;12\n".encode("gb18030"))

            dataframe = load_timeseries_file(path)

            self.assertEqual(list(dataframe.columns), ["time_s", "wheel_speed_fl"])
            self.assertEqual(len(dataframe), 2)
            self.assertAlmostEqual(float(dataframe.iloc[1]["wheel_speed_fl"]), 12.0)

    def test_xlsx_file_can_be_loaded_with_explicit_engine_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "sample.xlsx"
            pd.DataFrame({"time_s": [0.0, 0.1], "wheel_speed_fl": [10, 12]}).to_excel(path, index=False)

            dataframe = load_timeseries_file(path)

            self.assertEqual(list(dataframe.columns), ["time_s", "wheel_speed_fl"])
            self.assertEqual(len(dataframe), 2)

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


if __name__ == "__main__":
    unittest.main()