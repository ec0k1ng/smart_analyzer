from __future__ import annotations

import csv
import io
import re
import zipfile
from collections.abc import Iterable
from pathlib import Path

import numpy as np
import pandas as pd


SUPPORTED_FILE_TYPES = {".csv", ".xlsx", ".xls", ".mat", ".mf4", ".mdf", ".blf", ".dat", ".asc"}
CAN_DATABASE_DIR = Path(__file__).resolve().parents[1] / "config" / "can_databases"
TEXT_ENCODINGS = ["utf-8-sig", "utf-8", "gb18030", "gbk", "utf-16", "utf-16-le", "utf-16-be", "cp1252", "latin1"]
OLE_SIGNATURE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
ZIP_SIGNATURE = b"PK\x03\x04"


class UnsupportedFileTypeError(ValueError):
    pass


def _clean_column_name(name: object) -> str:
    cleaned = str(name).strip().strip('"').strip("'")
    cleaned = re.sub(r"\s*[\\/]\s*[A-Za-z][\w .-]*:\s*[-+]?\d+\s*$", "", cleaned)
    cleaned = re.sub(r"\s+\[(?:XCP|CCP|CAN|LIN|ETH|FLEXRAY)[^\]]*\]\s*$", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip() or str(name).strip()


def load_timeseries_file(file_path: str | Path, required_signals: Iterable[str] | None = None) -> pd.DataFrame:
    return _load_timeseries_file(file_path, required_signals=required_signals, selected_source_columns=None)


def _load_timeseries_file(
    file_path: str | Path,
    required_signals: Iterable[str] | None = None,
    selected_source_columns: Iterable[str] | None = None,
) -> pd.DataFrame:
    path = Path(file_path)
    suffix = path.suffix.lower()
    selected_columns = [str(name).strip() for name in (selected_source_columns or []) if str(name).strip()]
    if path.name.startswith("~$"):
        raise UnsupportedFileTypeError("检测到 Office/WPS 临时锁文件，请选择真实的数据文件再分析。")
    if suffix not in SUPPORTED_FILE_TYPES:
        raise UnsupportedFileTypeError(
            f"当前工具支持 CSV/Excel/MAT/DAT/BLF/ASC/MDF/MF4，暂不支持 {suffix or '未知类型'} 文件。"
        )

    if suffix == ".csv":
        dataframe = _load_csv_file(path, selected_source_columns=selected_columns)
    elif suffix in {".xlsx", ".xls"}:
        dataframe = _load_excel_file(path, selected_source_columns=selected_columns)
    elif suffix == ".dat":
        dataframe = _load_dat_file(path, selected_source_columns=selected_columns)
    elif suffix == ".mat":
        dataframe = _load_mat_file(path)
    elif suffix == ".blf":
        dataframe = _load_blf_file(path, required_signals=required_signals)
    elif suffix == ".asc":
        dataframe = _load_asc_file(path, required_signals=required_signals)
    else:
        dataframe = _load_mdf_file(path, selected_source_columns=selected_columns)

    dataframe.columns = [_clean_column_name(column) for column in dataframe.columns]
    dataframe.attrs["source_columns_before_time_normalization"] = list(dataframe.columns)
    dataframe.attrs["source_column_redirects"] = {}
    return _normalize_time_axis_column(dataframe)


def load_timeseries_file(
    file_path: str | Path,
    required_signals: Iterable[str] | None = None,
    selected_source_columns: Iterable[str] | None = None,
) -> pd.DataFrame:
    return _load_timeseries_file(file_path, required_signals=required_signals, selected_source_columns=selected_source_columns)


def inspect_timeseries_file_columns(file_path: str | Path) -> tuple[list[str], list[str], dict[str, str]] | None:
    path = Path(file_path)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        original_columns = _inspect_csv_columns(path)
    elif suffix in {".xlsx", ".xls"}:
        original_columns = _inspect_excel_columns(path)
    elif suffix == ".dat":
        original_columns = _inspect_dat_columns(path)
    elif suffix in {".mdf", ".mf4"}:
        original_columns = _inspect_mdf_columns(path)
    else:
        return None
    if not original_columns:
        return None
    preview = pd.DataFrame(columns=original_columns)
    preview.columns = [_clean_column_name(column) for column in preview.columns]
    preview.attrs["source_columns_before_time_normalization"] = list(preview.columns)
    preview.attrs["source_column_redirects"] = {}
    normalized = _normalize_time_axis_column(preview)
    return list(normalized.columns), list(normalized.attrs.get("source_columns_before_time_normalization", [])), dict(normalized.attrs.get("source_column_redirects", {}))


def _normalize_time_axis_column(dataframe: pd.DataFrame) -> pd.DataFrame:
    if "time_s" in dataframe.columns:
        return dataframe

    normalized_lookup = {str(column).strip().lower(): column for column in dataframe.columns}
    for candidate in [
        "time", "timestamps", "timestamp", "time[s]", "time(s)", "times", "ts",
        "time [s]", "time (s)", "t [s]", "t(s)", "t[s]", "zeit", "zeit [s]",
        "zeit(s)", "zeit[s]", "time_stamp", "timestamp_s", "elapsed_time",
    ]:
        actual = normalized_lookup.get(candidate)
        if actual is not None and actual != "time_s":
            normalized = dataframe.rename(columns={actual: "time_s"})
            normalized.attrs["source_column_redirects"] = {**dict(dataframe.attrs.get("source_column_redirects", {})), str(actual): "time_s"}
            return normalized

    stripped_lookup = {_strip_unit_suffix(str(column).strip()).lower(): column for column in dataframe.columns}
    for candidate in ["time", "t", "timestamp", "zeit", "elapsed_time"]:
        actual = stripped_lookup.get(candidate)
        if actual is not None and actual != "time_s":
            normalized = dataframe.rename(columns={actual: "time_s"})
            normalized.attrs["source_column_redirects"] = {**dict(dataframe.attrs.get("source_column_redirects", {})), str(actual): "time_s"}
            return normalized

    first_column = dataframe.columns[0]
    first_name = str(first_column).strip().lower()
    if first_name in {"index", "unnamed: 0"}:
        normalized = dataframe.rename(columns={first_column: "time_s"})
        normalized.attrs["source_column_redirects"] = {**dict(dataframe.attrs.get("source_column_redirects", {})), str(first_column): "time_s"}
        return normalized

    return dataframe


def _strip_unit_suffix(name: str) -> str:
    cleaned = re.sub(r"\s*\[.*?\]\s*$", "", name)
    cleaned = re.sub(r"\s*\(.*?\)\s*$", "", cleaned)
    return cleaned.strip()


def _inspect_csv_columns(path: Path) -> list[str]:
    raw_bytes = path.read_bytes()
    if not raw_bytes.strip():
        raise UnsupportedFileTypeError("CSV 文件为空。")
    for encoding in TEXT_ENCODINGS:
        try:
            text = raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
        columns = _inspect_delimited_text_columns(text)
        if columns:
            return columns
    raise UnsupportedFileTypeError("CSV 文件编码无法识别，请确认文件已完整导出。")


def _load_csv_file(path: Path, selected_source_columns: Iterable[str] | None = None) -> pd.DataFrame:
    raw_bytes = path.read_bytes()
    if not raw_bytes.strip():
        raise UnsupportedFileTypeError("CSV 文件为空。")

    errors: list[str] = []
    for encoding in TEXT_ENCODINGS:
        try:
            text = raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
        try:
            return _load_delimited_text(text, source_label=path.name, selected_source_columns=selected_source_columns)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{encoding}: {exc}")
            continue

    if errors:
        detail = "；".join(errors[:3])
        raise UnsupportedFileTypeError(f"CSV 文件读取失败，已尝试常见编码与分隔符。{detail}")
    raise UnsupportedFileTypeError("CSV 文件编码无法识别，请确认文件已完整导出。")


def _inspect_excel_columns(path: Path) -> list[str]:
    raw_bytes = path.read_bytes()
    if not raw_bytes.strip():
        raise UnsupportedFileTypeError("Excel 文件为空。")
    if _looks_like_delimited_text(raw_bytes):
        return _inspect_delimited_text_columns(_decode_text_bytes(raw_bytes))
    engine_candidates: list[str | None]
    if raw_bytes.startswith(ZIP_SIGNATURE):
        engine_candidates = ["openpyxl", None]
    elif raw_bytes.startswith(OLE_SIGNATURE):
        engine_candidates = ["xlrd", None, "openpyxl"]
    else:
        engine_candidates = [None, "openpyxl", "xlrd", "pyxlsb"]
    for engine in engine_candidates:
        try:
            read_options: dict[str, object] = {"sheet_name": 0, "nrows": 0}
            if engine is not None:
                read_options["engine"] = engine
            dataframe = pd.read_excel(path, **read_options)
            columns = [str(column) for column in dataframe.columns]
            if len(columns) >= 2:
                return columns
        except Exception:  # noqa: BLE001
            continue
    raise UnsupportedFileTypeError("Excel 文件表头读取失败，无法建立接口映射。")


def _load_excel_file(path: Path, selected_source_columns: Iterable[str] | None = None) -> pd.DataFrame:
    raw_bytes = path.read_bytes()
    if not raw_bytes.strip():
        raise UnsupportedFileTypeError("Excel 文件为空。")

    if _looks_like_delimited_text(raw_bytes):
        return _load_delimited_text(_decode_text_bytes(raw_bytes), source_label=path.name, selected_source_columns=selected_source_columns)

    engine_candidates: list[str | None]
    if raw_bytes.startswith(ZIP_SIGNATURE):
        engine_candidates = ["openpyxl", None]
    elif raw_bytes.startswith(OLE_SIGNATURE):
        engine_candidates = ["xlrd", None, "openpyxl"]
    else:
        engine_candidates = [None, "openpyxl", "xlrd", "pyxlsb"]

    errors: list[str] = []
    selected_set = {_clean_column_name(name) for name in (selected_source_columns or []) if str(name).strip()}
    for engine in engine_candidates:
        try:
            read_options = {"sheet_name": 0}
            if engine is not None:
                read_options["engine"] = engine
            if selected_set:
                read_options["usecols"] = lambda column_name: _clean_column_name(column_name) in selected_set
            dataframe = pd.read_excel(path, **read_options)
            dataframe = _clean_tabular_frame(dataframe)
            if _is_viable_tabular_frame(dataframe):
                return dataframe
        except ImportError as exc:
            errors.append(f"{engine or 'auto'}: 缺少依赖 {exc}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{engine or 'auto'}: {exc}")

    if _looks_like_delimited_text(raw_bytes, allow_binary_fallback=True):
        return _load_delimited_text(_decode_text_bytes(raw_bytes), source_label=path.name, selected_source_columns=selected_source_columns)

    if _looks_like_protected_or_nonstandard_excel(raw_bytes):
        raise UnsupportedFileTypeError(
            "Excel 文件读取失败：文件可能是受保护/加密文件，或扩展名为 Excel 但内容不是标准 xlsx/xls 工作簿。"
            " 请先在 Excel 中另存为标准未加密的 .xlsx 后再分析。"
        )

    detail = "；".join(errors[:3]) if errors else "未识别到可用工作表。"
    raise UnsupportedFileTypeError(f"Excel 文件读取失败，已尝试常见引擎和文本兜底。{detail}")


def _looks_like_protected_or_nonstandard_excel(raw_bytes: bytes) -> bool:
    if not raw_bytes.strip():
        return False
    if raw_bytes.startswith(ZIP_SIGNATURE):
        try:
            with zipfile.ZipFile(io.BytesIO(raw_bytes), "r") as zip_file:
                names = {name.lower() for name in zip_file.namelist()}
                return "encryptedpackage" in names or "encryptioninfo" in names
        except zipfile.BadZipFile:
            return True
    if raw_bytes.startswith(OLE_SIGNATURE):
        return True
    return not _looks_like_delimited_text(raw_bytes, allow_binary_fallback=True)


def _decode_text_bytes(raw_bytes: bytes) -> str:
    for encoding in TEXT_ENCODINGS:
        try:
            return raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise UnsupportedFileTypeError("文本文件编码无法识别，请确认文件已完整导出。")


def _looks_like_delimited_text(raw_bytes: bytes, allow_binary_fallback: bool = False) -> bool:
    sample_bytes = raw_bytes[:8192]
    if sample_bytes.startswith(ZIP_SIGNATURE) or sample_bytes.startswith(OLE_SIGNATURE):
        return False
    if b"\x00" in sample_bytes:
        return False
    try:
        text = _decode_text_bytes(sample_bytes)
    except UnsupportedFileTypeError:
        return False
    sample_lines = [line for line in text.splitlines() if line.strip()][:10]
    if not sample_lines:
        return False
    joined = "\n".join(sample_lines)
    printable_ratio = sum(character.isprintable() or character in "\r\n\t" for character in joined) / max(len(joined), 1)
    if printable_ratio < (0.85 if allow_binary_fallback else 0.92):
        return False
    return any(delimiter in joined for delimiter in [",", ";", "\t", "|"])


def _inspect_delimited_text_columns(text: str) -> list[str]:
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return []
    sample_lines = lines[:50]
    for delimiter in _candidate_delimiters(sample_lines):
        try:
            read_options: dict[str, object] = {"engine": "python", "nrows": 0, "skipinitialspace": True}
            if delimiter is None:
                read_options["sep"] = None
            else:
                read_options["sep"] = delimiter
            dataframe = pd.read_csv(io.StringIO("\n".join(sample_lines)), **read_options)
            columns = [str(column) for column in dataframe.columns if not str(column).strip().lower().startswith("unnamed:")]
            if len(columns) >= 2:
                return columns
        except Exception:  # noqa: BLE001
            continue
    return []


def _load_delimited_text(text: str, source_label: str, selected_source_columns: Iterable[str] | None = None) -> pd.DataFrame:
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        raise UnsupportedFileTypeError(f"{source_label} 为空或未包含可读取的表格。")

    errors: list[str] = []
    selected_set = {_clean_column_name(name) for name in (selected_source_columns or []) if str(name).strip()}
    for delimiter in _candidate_delimiters(lines):
        decimal_candidates = [",", "."] if delimiter in {";", "\t"} else ["."]
        for decimal in decimal_candidates:
            try:
                read_options = {
                    "engine": "python",
                    "skipinitialspace": True,
                    "on_bad_lines": "skip",
                    "decimal": decimal,
                }
                if delimiter is None:
                    read_options["sep"] = None
                else:
                    read_options["sep"] = delimiter
                if selected_set:
                    read_options["usecols"] = lambda column_name: _clean_column_name(column_name) in selected_set
                dataframe = pd.read_csv(io.StringIO("\n".join(lines)), **read_options)
                dataframe = _clean_tabular_frame(dataframe)
                if _is_viable_tabular_frame(dataframe):
                    return dataframe
            except Exception as exc:  # noqa: BLE001
                delimiter_label = "auto" if delimiter is None else delimiter
                errors.append(f"{delimiter_label}/{decimal}: {exc}")
    detail = "；".join(errors[:3]) if errors else "未识别到有效列。"
    raise UnsupportedFileTypeError(f"{source_label} 未能识别为有效的分隔文本。{detail}")


def _candidate_delimiters(lines: list[str]) -> list[str | None]:
    sample = "\n".join(lines[:20])
    candidates: list[str | None] = []
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        candidates.append(dialect.delimiter)
    except csv.Error:
        pass
    for delimiter in ["\t", ";", ",", "|"]:
        if delimiter in sample and delimiter not in candidates:
            candidates.append(delimiter)
    candidates.append(None)
    candidates.append(r"\s+")
    return candidates


def _clean_tabular_frame(dataframe: pd.DataFrame) -> pd.DataFrame:
    cleaned = dataframe.dropna(axis=1, how="all").dropna(axis=0, how="all")
    unnamed_columns = [column for column in cleaned.columns if str(column).strip().lower().startswith("unnamed:")]
    if unnamed_columns:
        cleaned = cleaned.drop(columns=unnamed_columns)
    return cleaned


def _is_viable_tabular_frame(dataframe: pd.DataFrame) -> bool:
    return not dataframe.empty and dataframe.shape[1] >= 2


def _inspect_dat_columns(path: Path) -> list[str]:
    measurement_columns = _inspect_mdf_columns(path)
    if measurement_columns:
        return measurement_columns

    raw_bytes = path.read_bytes()
    if b"\x00" in raw_bytes[:4096]:
        return []

    try:
        text = _decode_text_bytes(raw_bytes)
    except UnsupportedFileTypeError:
        return []

    return _inspect_text_dat_columns(text)


def _inspect_text_dat_columns(text: str) -> list[str]:
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    if not lines:
        return []

    inca_header = _inspect_inca_dat_columns(lines)
    if inca_header:
        return inca_header

    header_index, delimiter = _detect_dat_table(lines)
    header_line = lines[header_index].lstrip("#;/* ")
    if delimiter == r"\s+":
        parts = re.split(delimiter, header_line)
    else:
        parts = header_line.split(delimiter)
    return [part.strip() for part in parts if part.strip()]


def _load_dat_file(path: Path, selected_source_columns: Iterable[str] | None = None) -> pd.DataFrame:
    measurement_frame = _try_load_dat_as_measurement_file(path, selected_source_columns=selected_source_columns)
    if measurement_frame is not None:
        return measurement_frame

    inca_frame = _try_load_inca_dat(path, selected_source_columns=selected_source_columns)
    if inca_frame is not None:
        return inca_frame

    raw_bytes = path.read_bytes()
    if b"\x00" in raw_bytes[:4096]:
        raise UnsupportedFileTypeError("当前 DAT 未能按常见测量文件格式直接解析，且文件内容不是可读取的文本 DAT。")

    try:
        text = _decode_text_bytes(raw_bytes)
    except UnsupportedFileTypeError as exc:
        raise UnsupportedFileTypeError("DAT 文件未能按测量文件格式解析，文本编码也无法识别；请提供可复现样本以补齐该 INCA DAT 变体。") from exc

    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    if not lines:
        raise UnsupportedFileTypeError("DAT 文件为空或未包含可读取的文本表格。")

    header_index, delimiter = _detect_dat_table(lines)
    candidate_text = "\n".join(lines[header_index:])
    read_options = {"engine": "python"}
    if delimiter == r"\s+":
        read_options["sep"] = delimiter
    else:
        read_options["sep"] = delimiter
    selected_set = {_clean_column_name(name) for name in (selected_source_columns or []) if str(name).strip()}
    if selected_set:
        read_options["usecols"] = lambda column_name: _clean_column_name(column_name) in selected_set
    dataframe = pd.read_csv(io.StringIO(candidate_text), **read_options)
    dataframe = dataframe.dropna(axis=1, how="all")
    if dataframe.empty or dataframe.shape[1] < 2:
        raise UnsupportedFileTypeError("未能从 DAT 文件中识别出有效的时序数据表。")
    return dataframe


def _inspect_inca_dat_columns(lines: list[str]) -> list[str]:
    header_line_idx: int | None = None
    for idx, raw_line in enumerate(lines[:100]):
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith(("#", ";", "//", "/*", "'")):
            continue
        delimiter = _detect_inca_delimiter(line)
        parts = _split_inca_line(line, delimiter)
        if len(parts) < 2:
            continue
        numeric_count = sum(_looks_numeric(part) for part in parts)
        if numeric_count < len(parts) * 0.5:
            header_line_idx = idx
            break
    if header_line_idx is None:
        return []
    header_raw = lines[header_line_idx].strip()
    delimiter = _detect_inca_delimiter(header_raw)
    headers_raw = _split_inca_line(header_raw, delimiter)
    return [_strip_unit_suffix(h.strip().strip('"').strip("'")) for h in headers_raw]


def _try_load_inca_dat(path: Path, selected_source_columns: Iterable[str] | None = None) -> pd.DataFrame | None:
    raw_bytes = path.read_bytes()
    if b"\x00" in raw_bytes[:4096]:
        return None
    try:
        text = _decode_text_bytes(raw_bytes)
    except UnsupportedFileTypeError:
        return None

    lines = text.splitlines()
    if not lines:
        return None

    is_inca = any(
        keyword in lines[0].lower() if lines else False
        for keyword in ["inca", "etas", "asam", "mdf", "experiment"]
    )
    header_line_idx: int | None = None
    unit_line_idx: int | None = None
    data_start_idx: int | None = None

    for idx, raw_line in enumerate(lines[:100]):
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith(("#", ";", "//", "/*", "'")):
            is_inca = True
            continue
        delimiter = _detect_inca_delimiter(line)
        parts = _split_inca_line(line, delimiter)
        if len(parts) < 2:
            continue
        numeric_count = sum(_looks_numeric(part) for part in parts)
        if header_line_idx is None and numeric_count < len(parts) * 0.5:
            header_line_idx = idx
            next_non_empty_idx = _next_non_empty_line(lines, idx + 1)
            if next_non_empty_idx is not None:
                next_line = lines[next_non_empty_idx].strip()
                next_parts = _split_inca_line(next_line, delimiter)
                next_numeric = sum(_looks_numeric(p) for p in next_parts)
                if next_numeric < len(next_parts) * 0.5 and len(next_parts) >= 2:
                    unit_line_idx = next_non_empty_idx
                    data_after = _next_non_empty_line(lines, next_non_empty_idx + 1)
                    if data_after is not None:
                        data_start_idx = data_after
                else:
                    data_start_idx = next_non_empty_idx
            break
        elif numeric_count >= len(parts) * 0.5:
            if header_line_idx is None:
                data_start_idx = idx
            break

    if header_line_idx is None and data_start_idx is None:
        if not is_inca:
            return None
        return None

    if header_line_idx is None:
        return None

    header_raw = lines[header_line_idx].strip()
    delimiter = _detect_inca_delimiter(header_raw)
    headers_raw = _split_inca_line(header_raw, delimiter)
    headers_clean = [_strip_unit_suffix(h.strip().strip('"').strip("'")) for h in headers_raw]

    if data_start_idx is None:
        data_start_idx = header_line_idx + 1

    data_lines = []
    for raw_line in lines[data_start_idx:]:
        line = raw_line.strip()
        if not line or line.startswith(("#", ";", "//", "/*")):
            continue
        data_lines.append(line)

    if not data_lines:
        return None

    data_text = "\n".join(data_lines)
    try:
        read_options: dict[str, object] = {"engine": "python", "header": None, "on_bad_lines": "skip"}
        if delimiter == "\t":
            read_options["sep"] = "\t"
        elif delimiter == ";":
            read_options["sep"] = ";"
        elif delimiter == ",":
            read_options["sep"] = ","
        else:
            read_options["sep"] = r"\s+"
        dataframe = pd.read_csv(io.StringIO(data_text), **read_options)
    except Exception:
        return None

    if dataframe.empty or dataframe.shape[1] < 2:
        return None

    if len(headers_clean) == dataframe.shape[1]:
        dataframe.columns = headers_clean
    elif len(headers_clean) > dataframe.shape[1]:
        dataframe.columns = headers_clean[: dataframe.shape[1]]

    selected_set = {_clean_column_name(name) for name in (selected_source_columns or []) if str(name).strip()}
    if selected_set:
        keep_columns = [column for column in dataframe.columns if _clean_column_name(column) in selected_set]
        dataframe = dataframe.loc[:, keep_columns]

    dataframe = dataframe.dropna(axis=1, how="all")
    for col in dataframe.columns:
        dataframe[col] = pd.to_numeric(dataframe[col], errors="coerce")
    dataframe = dataframe.dropna(axis=0, how="all")

    if dataframe.empty or dataframe.shape[1] < 2:
        return None

    return dataframe


def _detect_inca_delimiter(line: str) -> str:
    tab_count = line.count("\t")
    semi_count = line.count(";")
    comma_count = line.count(",")
    if tab_count >= 2:
        return "\t"
    if semi_count >= 2:
        return ";"
    if comma_count >= 2:
        return ","
    return r"\s+"


def _split_inca_line(line: str, delimiter: str) -> list[str]:
    if delimiter == r"\s+":
        return [p for p in re.split(r"\s+", line.strip()) if p]
    return [p.strip() for p in line.split(delimiter) if p.strip()]


def _next_non_empty_line(lines: list[str], start: int) -> int | None:
    for idx in range(start, min(start + 10, len(lines))):
        if lines[idx].strip():
            return idx
    return None


def _try_load_dat_as_measurement_file(path: Path, selected_source_columns: Iterable[str] | None = None) -> pd.DataFrame | None:
    try:
        dataframe = _load_mdf_file(path, selected_source_columns=selected_source_columns)
    except Exception:  # noqa: BLE001
        return None
    if dataframe.empty or dataframe.shape[1] < 2:
        return None
    return dataframe


def _detect_dat_table(lines: list[str]) -> tuple[int, str]:
    delimiter_candidates = ["\t", ";", ",", r"\s+"]
    for index, line in enumerate(lines[:80]):
        cleaned = line.lstrip("#;/* ")
        if not cleaned:
            continue
        for delimiter in delimiter_candidates:
            parts = re.split(delimiter, cleaned) if delimiter == r"\s+" else cleaned.split(delimiter)
            parts = [part.strip() for part in parts if part.strip()]
            if len(parts) < 2:
                continue
            next_line = next((candidate for candidate in lines[index + 1 :] if candidate.strip()), "")
            next_parts = re.split(delimiter, next_line.strip()) if delimiter == r"\s+" else next_line.split(delimiter)
            next_parts = [part.strip() for part in next_parts if part.strip()]
            if len(next_parts) < 2:
                continue
            numeric_hits = sum(_looks_numeric(part) for part in next_parts)
            if numeric_hits >= max(1, len(next_parts) // 2):
                return index, delimiter
    return 0, ","


def _looks_numeric(value: str) -> bool:
    try:
        float(str(value).replace(",", ""))
        return True
    except ValueError:
        return False


def _load_mat_file(path: Path) -> pd.DataFrame:
    try:
        from scipy.io import loadmat
    except ImportError as exc:
        raise UnsupportedFileTypeError("读取 MAT 文件需要先安装 scipy。") from exc

    raw = loadmat(path, squeeze_me=True, struct_as_record=False)
    series_map: dict[str, np.ndarray] = {}
    expected_length: int | None = None

    for key, value in raw.items():
        if key.startswith("__"):
            continue

        array = np.asarray(value).squeeze()
        if array.ndim != 1:
            continue
        if not np.issubdtype(array.dtype, np.number):
            continue

        if expected_length is None:
            expected_length = int(array.shape[0])
        if int(array.shape[0]) != expected_length:
            continue

        series_map[key] = array.astype(float, copy=False)

    if not series_map:
        raise UnsupportedFileTypeError("MAT 文件中未找到可直接转换为时序表的一维数值变量。")

    return pd.DataFrame(series_map)


def _inspect_mdf_columns(path: Path) -> list[str]:
    try:
        from asammdf import MDF
    except ImportError:
        return []

    try:
        mdf = MDF(str(path))
    except Exception:
        return []

    channels_db = getattr(mdf, "channels_db", {}) or {}
    channel_names = [str(name).strip() for name in channels_db.keys() if str(name).strip()]
    if channel_names:
        return ["timestamps", *channel_names]
    return []


def _load_mdf_file(path: Path, selected_source_columns: Iterable[str] | None = None) -> pd.DataFrame:
    try:
        from asammdf import MDF
    except ImportError as exc:
        raise UnsupportedFileTypeError("读取 MDF/MF4 文件需要先安装 asammdf。") from exc

    mdf = MDF(str(path))
    dataframe = _try_decode_bus_mdf(mdf, path)
    if dataframe is None:
        try:
            selected_channels = [
                str(name).strip()
                for name in (selected_source_columns or [])
                if str(name).strip() and str(name).strip() not in {"time_s", "timestamps", "timestamp", "time"}
            ]
            if selected_channels and hasattr(mdf, "filter"):
                dataframe = mdf.filter(selected_channels).to_dataframe()
            else:
                dataframe = mdf.to_dataframe()
        except Exception as exc:
            raise UnsupportedFileTypeError(f"MDF/MF4 文件解析失败：{exc}") from exc
    dataframe = dataframe.reset_index()

    if hasattr(dataframe.index, "dtype") and np.issubdtype(dataframe.index.dtype, np.datetime64):
        dataframe = dataframe.reset_index()

    for col in dataframe.columns:
        col_lower = str(col).strip().lower()
        if col_lower in {"timestamps", "timestamp", "time"} and col != "time_s":
            series = pd.to_numeric(dataframe[col], errors="coerce")
            if series.notna().any():
                if series.max() > 1e9:
                    series = series - series.iloc[0]
                dataframe[col] = series

    return _normalize_time_axis_column(dataframe)


def _normalize_requested_signal_names(required_signals: Iterable[str] | None) -> set[str] | None:
    normalized = {str(signal_name).strip() for signal_name in (required_signals or []) if str(signal_name).strip()}
    return normalized or None


def _load_blf_file(path: Path, required_signals: Iterable[str] | None = None) -> pd.DataFrame:
    try:
        import can
        import cantools
    except ImportError as exc:
        raise UnsupportedFileTypeError("读取 BLF 文件需要先安装 python-can 和 cantools。") from exc

    databases, dbc_paths, dbc_errors = _load_can_databases(path, cantools)
    if not dbc_paths:
        raise UnsupportedFileTypeError("读取 BLF 总线数据需要 DBC 文件。请将 .dbc 放到 config/can_databases/ 或数据文件同目录。")
    if not databases:
        detail = f" 已发现 DBC，但均未能成功加载：{'；'.join(dbc_errors[:3])}" if dbc_errors else ""
        raise UnsupportedFileTypeError(f"读取 BLF 总线数据需要可用的 DBC 文件。{detail}")

    decoder_lookup = _build_can_message_lookup(databases, required_signals)
    signal_timeseries: dict[str, tuple[list[float], list[float]]] = {}
    start_time: float | None = None
    decoded_count = 0
    undecoded_count = 0
    with can.BLFReader(str(path)) as reader:
        for message in reader:
            if getattr(message, "is_error_frame", False) or getattr(message, "is_remote_frame", False):
                continue
            decoded = _decode_can_message(message.arbitration_id, bytes(message.data), decoder_lookup)
            if not decoded:
                undecoded_count += 1
                continue
            decoded_count += 1
            if start_time is None:
                start_time = float(message.timestamp)
            relative_time = float(message.timestamp) - start_time
            for signal_name, signal_value in decoded.items():
                if signal_name not in signal_timeseries:
                    signal_timeseries[signal_name] = ([], [])
                signal_timeseries[signal_name][0].append(relative_time)
                signal_timeseries[signal_name][1].append(signal_value)

    return _build_bus_frame_from_timeseries(signal_timeseries, "BLF", decoded_count, undecoded_count)


def _load_asc_file(path: Path, required_signals: Iterable[str] | None = None) -> pd.DataFrame:
    try:
        import cantools
    except ImportError as exc:
        raise UnsupportedFileTypeError("读取 ASC 文件需要先安装 cantools。") from exc

    databases, dbc_paths, dbc_errors = _load_can_databases(path, cantools)
    if not dbc_paths:
        raise UnsupportedFileTypeError("读取 ASC 总线数据需要 DBC 文件。请将 .dbc 放到 config/can_databases/ 或数据文件同目录。")
    if not databases:
        detail = f" 已发现 DBC，但均未能成功加载：{'；'.join(dbc_errors[:3])}" if dbc_errors else ""
        raise UnsupportedFileTypeError(f"读取 ASC 总线数据需要可用的 DBC 文件。{detail}")

    decoder_lookup = _build_can_message_lookup(databases, required_signals)
    raw_bytes = path.read_bytes()
    try:
        text = _decode_text_bytes(raw_bytes)
    except UnsupportedFileTypeError as exc:
        raise UnsupportedFileTypeError("ASC 文件编码无法识别。") from exc

    signal_timeseries: dict[str, tuple[list[float], list[float]]] = {}
    start_time: float | None = None
    decoded_count = 0
    undecoded_count = 0
    asc_msg_pattern = re.compile(
        r"^\s*(?P<time>[0-9]+\.?[0-9]*)\s+"
        r"(?P<channel>\d+)\s+"
        r"(?P<id>[0-9A-Fa-f]+)x?\s+"
        r"(?:Rx|Tx)\s+"
        r"d\s+(?P<dlc>\d+)\s+"
        r"(?P<data>[0-9A-Fa-f\s]+)"
    )

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("date", "base", "internal", "Begin", "End", "//", ";", "Start")):
            continue
        match = asc_msg_pattern.match(line)
        if match is None:
            continue

        try:
            msg_time = float(match.group("time"))
            arb_id = int(match.group("id"), 16)
            data_bytes_str = match.group("data").strip().split()
            payload = bytes(int(b, 16) for b in data_bytes_str)
        except (ValueError, IndexError):
            continue

        decoded = _decode_can_message(arb_id, payload, decoder_lookup)
        if not decoded:
            undecoded_count += 1
            continue
        decoded_count += 1
        if start_time is None:
            start_time = msg_time
        relative_time = msg_time - start_time
        for signal_name, signal_value in decoded.items():
            if signal_name not in signal_timeseries:
                signal_timeseries[signal_name] = ([], [])
            signal_timeseries[signal_name][0].append(relative_time)
            signal_timeseries[signal_name][1].append(signal_value)

    return _build_bus_frame_from_timeseries(signal_timeseries, "ASC", decoded_count, undecoded_count)


def _try_decode_bus_mdf(mdf, path: Path) -> pd.DataFrame | None:  # noqa: ANN001
    dbc_paths = _discover_dbc_paths(path)
    if not dbc_paths:
        return None
    database_files = {"CAN": []}
    for dbc_path in dbc_paths:
        for bus_index in range(8):
            database_files["CAN"].append((str(dbc_path), bus_index))
    try:
        decoded_mdf = mdf.extract_bus_logging(database_files=database_files)
    except Exception:
        return None
    try:
        dataframe = decoded_mdf.to_dataframe().reset_index()
    except Exception:
        return None
    if dataframe.empty or dataframe.shape[1] <= 1:
        return None

    for col in dataframe.columns:
        if np.issubdtype(dataframe[col].dtype, np.datetime64):
            epoch = pd.Timestamp("1970-01-01")
            numeric_col = (dataframe[col] - epoch).dt.total_seconds()
            if numeric_col.notna().any():
                numeric_col = numeric_col - numeric_col.iloc[0]
                dataframe[col] = numeric_col

    return dataframe


def _discover_dbc_paths(log_path: Path) -> list[Path]:
    CAN_DATABASE_DIR.mkdir(parents=True, exist_ok=True)
    candidates = _list_dbc_files(CAN_DATABASE_DIR)
    candidates.extend(_list_dbc_files(log_path.parent))
    sidecar = log_path.with_suffix(".dbc")
    if sidecar.exists():
        candidates.append(sidecar)
    unique: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        unique.append(candidate)
        seen.add(resolved)
    return unique


def _list_dbc_files(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return sorted([path for path in directory.iterdir() if path.is_file() and path.suffix.lower() == ".dbc"], key=lambda item: item.name.lower())


def _load_can_databases(log_path: Path, cantools_module) -> tuple[list[object], list[Path], list[str]]:  # noqa: ANN001
    databases = []
    dbc_paths = _discover_dbc_paths(log_path)
    errors: list[str] = []
    for dbc_path in dbc_paths:
        try:
            databases.append(cantools_module.database.load_file(str(dbc_path), strict=False))
        except Exception as exc:  # noqa: BLE001
            message = f"{dbc_path.name}: {exc}"
            if message not in errors:
                errors.append(message)
            continue
    return databases, dbc_paths, errors


def _build_can_message_lookup(databases: list[object], required_signals: Iterable[str] | None = None) -> dict[int, list[tuple[object, tuple[str, ...]]]]:
    requested_names = _normalize_requested_signal_names(required_signals)
    lookup: dict[int, list[tuple[object, tuple[str, ...]]]] = {}
    for database in databases:
        for message in getattr(database, "messages", []):
            signal_names = tuple(
                str(signal.name).strip()
                for signal in getattr(message, "signals", [])
                if str(getattr(signal, "name", "")).strip()
            )
            if requested_names is None:
                relevant_signal_names = signal_names
            else:
                relevant_signal_names = tuple(signal_name for signal_name in signal_names if signal_name in requested_names)
                if not relevant_signal_names:
                    continue
            frame_id = int(getattr(message, "frame_id", 0))
            for candidate_id in {frame_id, frame_id & 0x1FFFFFFF, frame_id & 0x7FF}:
                lookup.setdefault(candidate_id, []).append((message, relevant_signal_names))
    return lookup


def _decode_can_message(
    arbitration_id: int,
    payload: bytes,
    decoder_lookup: dict[int, list[tuple[object, tuple[str, ...]]]],
) -> dict[str, object]:
    seen_messages: set[int] = set()
    for candidate_id in [arbitration_id, arbitration_id & 0x1FFFFFFF, arbitration_id & 0x7FF]:
        for message, relevant_signal_names in decoder_lookup.get(candidate_id, []):
            message_identity = id(message)
            if message_identity in seen_messages:
                continue
            seen_messages.add(message_identity)
            try:
                decoded = message.decode(payload, decode_choices=False)
            except Exception:
                continue
            if relevant_signal_names:
                filtered = {signal_name: decoded[signal_name] for signal_name in relevant_signal_names if signal_name in decoded}
            else:
                filtered = {str(key): value for key, value in decoded.items()}
            if filtered:
                return filtered
    return {}


def _build_bus_frame_from_timeseries(
    signal_timeseries: dict[str, tuple[list[float], list[float]]],
    source_label: str,
    decoded_count: int = 0,
    undecoded_count: int = 0,
) -> pd.DataFrame:
    if not signal_timeseries:
        detail = ""
        if undecoded_count > 0:
            detail = f" 共读取 {undecoded_count} 条报文但均未被 DBC 覆盖。"
        raise UnsupportedFileTypeError(
            f"{source_label} 中未能解出任何信号。请确认 DBC 文件已放入 config/can_databases/ 或数据文件同目录。{detail}"
        )

    all_timestamps: set[float] = set()
    for times, _values in signal_timeseries.values():
        all_timestamps.update(times)
    unified_time = np.array(sorted(all_timestamps))

    result = pd.DataFrame({"time_s": unified_time})
    max_fill_gap = 0.2

    for signal_name, (times, values) in signal_timeseries.items():
        if not times:
            continue
        time_index = pd.Index(unified_time, dtype=float)
        signal_series = pd.Series(
            data=[float(v) if isinstance(v, (int, float)) else np.nan for v in values],
            index=pd.Index(times, dtype=float),
        )
        signal_series = signal_series.groupby(signal_series.index).last()
        reindexed = signal_series.reindex(time_index)
        time_diff = pd.Series(unified_time, index=time_index, dtype=float).diff().fillna(0.0)
        cumulative_gap = time_diff.where(reindexed.isna(), 0.0).groupby(reindexed.notna().cumsum()).cumsum()
        filled = reindexed.ffill()
        mask = (cumulative_gap > max_fill_gap).reindex(filled.index, fill_value=False)
        filled[mask] = np.nan
        result[signal_name] = filled.values

    return result.sort_values("time_s").reset_index(drop=True)


def _bus_records_to_frame(records: list[dict[str, object]], source_label: str) -> pd.DataFrame:
    if not records:
        raise UnsupportedFileTypeError(
            f"{source_label} 中未能解出任何信号。请确认 DBC 文件已放入 config/can_databases/ 或数据文件同目录。"
        )
    signal_timeseries: dict[str, tuple[list[float], list[float]]] = {}
    for record in records:
        t = float(record.get("time_s", 0.0))
        for key, value in record.items():
            if key == "time_s":
                continue
            if key not in signal_timeseries:
                signal_timeseries[key] = ([], [])
            signal_timeseries[key][0].append(t)
            signal_timeseries[key][1].append(value)
    return _build_bus_frame_from_timeseries(signal_timeseries, source_label)
