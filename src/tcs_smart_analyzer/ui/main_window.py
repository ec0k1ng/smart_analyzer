from __future__ import annotations

import html
import json
import math
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from pypinyin import lazy_pinyin
except ImportError:  # pragma: no cover - fallback when optional dependency is missing
    lazy_pinyin = None

from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis
from PySide6.QtCore import QMargins, QMimeData, QPoint, QPointF, QRect, Qt, QTimer, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QDrag, QKeySequence, QMouseEvent, QPainter, QPen, QShortcut, QTextCharFormat, QTextCursor, QTextDocument, QTextFormat, QWheelEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QColorDialog,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextBrowser,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QRubberBand,
)

from tcs_smart_analyzer.config import (
    align_python_config_file_name,
    create_derived_signal_draft_file,
    create_kpi_draft_file,
    create_report_template_file,
    delete_formula_signal_definition,
    delete_kpi_group,
    delete_config_file,
    extract_derived_signal_name_from_text,
    extract_kpi_name_from_text,
    get_plot_signal_names,
    list_derived_signal_spec_entries,
    list_kpi_spec_entries,
    load_chart_view_state,
    load_derived_signal_definitions,
    load_formula_signal_definitions,
    load_kpi_groups,
    list_report_template_entries,
    load_analysis_settings,
    load_interface_signal_tables,
    read_text_config_file,
    rename_derived_signal_references,
    rename_kpi_references,
    save_chart_view_state,
    save_formula_signal_definition,
    save_kpi_group,
    save_interface_signal_tables,
    validate_python_config_content,
    validate_runtime_definition_files,
    write_text_config_file,
)
from tcs_smart_analyzer.core.engine import AnalysisEngine
from tcs_smart_analyzer.core.features import ConfigExecutionError, populate_kpi_signal_values
from tcs_smart_analyzer.core.models import AnalysisResult
from tcs_smart_analyzer.data.loaders import CAN_DATABASE_DIR
from tcs_smart_analyzer.reporting.exporters import batch_report_filename, batch_word_filename, export_html, export_word


FILE_DIALOG_FILTER = "Supported Logs (*.csv *.xlsx *.xls *.dat *.blf *.asc *.mat *.mdf *.mf4)"
QUEUE_PATH_ROLE = Qt.ItemDataRole.UserRole
QUEUE_GROUP_ROLE = Qt.ItemDataRole.UserRole + 1
QUEUE_HEADER_ROLE = Qt.ItemDataRole.UserRole + 2
RESULT_ROW_KIND_ROLE = Qt.ItemDataRole.UserRole + 20
RESULT_ROW_PATH_ROLE = Qt.ItemDataRole.UserRole + 21
PROTECTED_DERIVED_FILES = {"00_example_and_guide.py"}
PROTECTED_KPI_FILES = {"00_example_and_guide.py"}
PROTECTED_TEMPLATE_FILES = {"00_example_and_guide.html"}
SYSTEM_MAPPING_HEADERS = [
    "raw_input_name",
    "from",
    "actual_signal_name_1",
    "actual_signal_name_2",
    "actual_signal_name_3",
    "actual_signal_name_4",
    "actual_signal_name_5",
]
CUSTOM_MAPPING_HEADERS = [
    "raw_input_name",
    "actual_signal_name_1",
    "actual_signal_name_2",
    "actual_signal_name_3",
    "actual_signal_name_4",
    "actual_signal_name_5",
]
APP_STYLE = """
* {
    font-family: "Microsoft YaHei UI", "Segoe UI", "Helvetica Neue", sans-serif;
}
QMainWindow {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #e8f0fe, stop:0.4 #f0f4fa, stop:0.7 #f5f8fc, stop:1 #eaf5f0);
}
QGroupBox {
    background: rgba(255, 255, 255, 0.95);
    border: 1px solid #dce6f0;
    border-radius: 16px;
    margin-top: 12px;
    padding-top: 18px;
    color: #1a3553;
    font-weight: 600;
    font-size: 12px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 16px;
    padding: 2px 8px;
    background: rgba(255, 255, 255, 0.9);
    border-radius: 8px;
}
QPushButton, QToolButton {
    min-height: 32px;
    border-radius: 10px;
    border: 1px solid #c5d3e3;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:1 #f0f5fc);
    padding: 2px 14px;
    color: #1a3553;
    font-weight: 500;
    font-size: 12px;
}
QPushButton:hover, QToolButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f8fbff, stop:1 #e5eef9);
    border-color: #7aade4;
}
QPushButton:pressed, QToolButton:pressed {
    background: #d4e4f7;
    border-color: #5c9ad8;
}
QPushButton:disabled {
    color: #a0b0c0;
    background: #f0f3f6;
    border-color: #dde3ea;
}
QLineEdit, QComboBox, QListWidget, QTableWidget, QPlainTextEdit, QTextEdit {
    background: #ffffff;
    border: 1px solid #d0dbe7;
    border-radius: 8px;
    padding: 4px 8px;
    selection-background-color: #cde2fa;
    selection-color: #13324e;
    font-size: 12px;
}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {
    border: 1.5px solid #6ea8e0;
    background: #fafcff;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    border: 1px solid #c5d3e3;
    border-radius: 8px;
    background: #ffffff;
    selection-background-color: #dceafa;
}
QTabWidget::pane {
    border: 1px solid #d0dbe7;
    border-radius: 14px;
    background: rgba(255, 255, 255, 0.97);
    top: -1px;
}
QTabBar::tab {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #eef3fa, stop:1 #e0e9f3);
    border: 1px solid #d0dbe7;
    padding: 8px 20px;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    margin-right: 3px;
    color: #3a5672;
    font-weight: 500;
    font-size: 12px;
}
QTabBar::tab:selected {
    background: #ffffff;
    color: #0d5ba6;
    font-weight: 600;
    border-bottom-color: #ffffff;
}
QTabBar::tab:hover:!selected {
    background: #f5f9ff;
    color: #1a3553;
}
QHeaderView::section {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f4f8fc, stop:1 #eaf0f7);
    border: none;
    border-bottom: 1.5px solid #cddaea;
    border-right: 1px solid #e2eaf3;
    padding: 8px 10px;
    color: #1a3553;
    font-weight: 600;
    font-size: 11px;
}
QToolTip {
    font-size: 11px;
    padding: 6px 10px;
    border: 1px solid #c5d3e3;
    border-radius: 6px;
    background: #ffffff;
    color: #334155;
}
QProgressBar {
    background: #e8eff7;
    border: 1px solid #d0dbe7;
    border-radius: 8px;
    min-height: 20px;
    text-align: center;
    color: #1a3553;
    font-size: 11px;
    font-weight: 500;
}
QProgressBar::chunk {
    border-radius: 7px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:0.5 #3b82f6, stop:1 #10b981);
}
QSplitter::handle {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 transparent, stop:0.4 #c5d3e3, stop:0.6 #c5d3e3, stop:1 transparent);
    width: 5px;
    height: 5px;
    border-radius: 2px;
}
QSplitter::handle:hover {
    background: #7aade4;
}
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 2px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: #c5d3e3;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #9bb5ca;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background: transparent;
    height: 10px;
    margin: 2px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal {
    background: #c5d3e3;
    border-radius: 5px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover {
    background: #9bb5ca;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}
QLabel {
    color: #1a3553;
}
QCheckBox {
    spacing: 6px;
    color: #2a4a66;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1.5px solid #b0c4d8;
    background: #ffffff;
}
QCheckBox::indicator:checked {
    background: #2563eb;
    border-color: #2563eb;
}
QTextBrowser {
    background: #ffffff;
    border: 1px solid #d0dbe7;
    border-radius: 8px;
}
"""

TOOL_BUTTON_STYLE = """
QToolButton {
    min-width: 30px;
    max-width: 30px;
    min-height: 30px;
    max-height: 30px;
    padding: 0;
    font-size: 14px;
    font-weight: 700;
    border-radius: 8px;
    border: 1px solid #c5d3e3;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:1 #f0f5fc);
    color: #1a3553;
}
QToolButton:hover {
    border-color: #7aade4;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f8fbff, stop:1 #e5eef9);
}
QToolButton:pressed {
    background: #d4e4f7;
    border-color: #5c9ad8;
}
QToolButton:checked {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2563eb, stop:1 #1d4ed8);
    color: #ffffff;
    border-color: #1d4ed8;
}
"""

SIGNAL_DRAG_MIME_TYPE = "application/x-tcs-signal-list"


def _build_signal_drag_payload(signal_names: list[str], source_panel_id: int | None = None) -> str:
    payload = {
        "signals": [str(signal).strip() for signal in signal_names if str(signal).strip()],
        "source_panel_id": source_panel_id,
    }
    return json.dumps(payload, ensure_ascii=False)


def _parse_signal_drag_payload(mime_data: QMimeData) -> tuple[list[str], int | None]:
    payload_text = ""
    if mime_data.hasFormat(SIGNAL_DRAG_MIME_TYPE):
        payload_text = bytes(mime_data.data(SIGNAL_DRAG_MIME_TYPE)).decode("utf-8", errors="ignore")
    elif mime_data.hasText():
        payload_text = mime_data.text()
    if not payload_text.strip():
        return [], None
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError:
        signal_names = [line.strip() for line in payload_text.splitlines() if line.strip()]
        return list(dict.fromkeys(signal_names)), None
    signal_names = [str(signal).strip() for signal in payload.get("signals", []) if str(signal).strip()]
    source_panel_id = payload.get("source_panel_id")
    if not isinstance(source_panel_id, int):
        source_panel_id = None
    return list(dict.fromkeys(signal_names)), source_panel_id


class QueueListWidget(QListWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._delete_callback = None

    def set_delete_callback(self, callback) -> None:
        self._delete_callback = callback

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Delete and self._delete_callback is not None:
            self._delete_callback()
            event.accept()
            return
        super().keyPressEvent(event)


class DraggableSignalListWidget(QListWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setViewMode(QListWidget.ViewMode.ListMode)
        self.setFlow(QListWidget.Flow.TopToBottom)
        self.setResizeMode(QListWidget.ResizeMode.Fixed)
        self.setWrapping(False)
        self.setSpacing(2)
        self.setMinimumHeight(280)

    def startDrag(self, supported_actions) -> None:  # noqa: ANN001
        signal_names = [item.text().strip() for item in self.selectedItems() if item.text().strip()]
        if not signal_names:
            return
        mime = QMimeData()
        payload = _build_signal_drag_payload(signal_names)
        mime.setData(SIGNAL_DRAG_MIME_TYPE, payload.encode("utf-8"))
        mime.setText("\n".join(signal_names))
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.CopyAction)


class FormulaSignalListWidget(DraggableSignalListWidget):
    def __init__(self, edit_callback, delete_callback, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._edit_callback = edit_callback
        self._delete_callback = delete_callback

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Delete:
            item = self.currentItem()
            if item is not None:
                self._delete_callback(item)
                event.accept()
                return
        super().keyPressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        item = self.itemAt(event.position().toPoint())
        if item is not None:
            self._edit_callback(item)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


class FormulaSignalDialog(QDialog):
    def __init__(
        self,
        signal_names: list[str],
        parent: QWidget | None = None,
        *,
        title: str,
        name: str = "",
        expression: str = "",
        allow_rename: bool = True,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(560, 520)
        self._all_signal_names = list(signal_names)

        layout = QVBoxLayout(self)
        form = QGridLayout()
        self.name_edit = QLineEdit(name)
        self.name_edit.setReadOnly(not allow_rename)
        self.expression_edit = QLineEdit(expression)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索可用信号，双击可插入公式")
        self.signal_list = QListWidget()
        self.signal_list.itemDoubleClicked.connect(self._insert_signal_name)
        self.search_edit.textChanged.connect(self._refresh_signal_list)

        form.addWidget(QLabel("信号名称"), 0, 0)
        form.addWidget(self.name_edit, 0, 1)
        form.addWidget(QLabel("公式表达式"), 1, 0)
        form.addWidget(self.expression_edit, 1, 1)
        form.addWidget(QLabel("快速搜索"), 2, 0)
        form.addWidget(self.search_edit, 2, 1)
        layout.addLayout(form)
        layout.addWidget(self.signal_list, 1)

        tips = QLabel("表达式可直接使用现有信号和 KPI 名称，例如 wheel_speed_fl + wheel_speed_fr")
        tips.setStyleSheet("color: #5f7388; font-size: 11px;")
        layout.addWidget(tips)

        action_row = QHBoxLayout()
        action_row.addStretch(1)
        cancel_button = QPushButton("取消")
        ok_button = QPushButton("保存")
        cancel_button.clicked.connect(self.reject)
        ok_button.clicked.connect(self.accept)
        action_row.addWidget(cancel_button)
        action_row.addWidget(ok_button)
        layout.addLayout(action_row)

        self._refresh_signal_list("")

    def _refresh_signal_list(self, keyword: str) -> None:
        query = keyword.strip().lower()
        self.signal_list.clear()
        for signal_name in sorted(self._all_signal_names, key=str.lower):
            if query and query not in signal_name.lower():
                continue
            self.signal_list.addItem(signal_name)

    def _insert_signal_name(self, item: QListWidgetItem) -> None:
        token = item.text()
        current_text = self.expression_edit.text()
        cursor_position = self.expression_edit.cursorPosition()
        insert_text = token if not current_text or current_text.endswith(("(", "+", "-", "*", "/", " ")) else f" {token}"
        updated = current_text[:cursor_position] + insert_text + current_text[cursor_position:]
        self.expression_edit.setText(updated)
        self.expression_edit.setCursorPosition(cursor_position + len(insert_text))

    def values(self) -> tuple[str, str]:
        return self.name_edit.text().strip(), self.expression_edit.text().strip()


class JumpAwarePlainTextEdit(QPlainTextEdit):
    def __init__(self, jump_callback=None, parent: QWidget | None = None, *, highlight_config_keys: bool = False) -> None:
        super().__init__(parent)
        self._jump_callback = jump_callback
        self._highlight_config_keys = highlight_config_keys
        self._search_ranges: list[tuple[int, int]] = []
        self._current_search_range: tuple[int, int] | None = None
        self._replacement_ranges: list[tuple[int, int]] = []
        self._navigation_ranges: list[tuple[int, int]] = []
        self._issue_ranges: list[tuple[int, int]] = []
        self._issue_line_blocks: list[int] = []
        self._undo_ranges: list[tuple[int, int]] = []
        self._highlight_next_change_as_undo = False
        self._pending_undo_range: tuple[int, int] | None = None
        self.cursorPositionChanged.connect(self._refresh_decorations)
        self.textChanged.connect(self._refresh_decorations)
        self.document().contentsChange.connect(self._on_document_contents_change)

    def _token_at_position(self, position) -> str:  # noqa: ANN001
        cursor = self.cursorForPosition(position)
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        return cursor.selectedText().strip()

    def _make_range_selection(self, start: int, end: int, color: str) -> QTextEdit.ExtraSelection:
        selection = QTextEdit.ExtraSelection()
        cursor = self.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        selection.cursor = cursor
        selection.format.setBackground(QColor(color))
        return selection

    def _make_full_width_selection(self, block_number: int, color: str) -> QTextEdit.ExtraSelection:
        selection = QTextEdit.ExtraSelection()
        cursor = QTextCursor(self.document().findBlockByNumber(block_number))
        cursor.clearSelection()
        selection.cursor = cursor
        selection.format.setBackground(QColor(color))
        selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
        return selection

    def _collect_config_key_line_blocks(self) -> list[int]:
        if not self._highlight_config_keys:
            return []
        blocks: list[int] = []
        highlighted_keys = ['"raw_inputs"', '"derived_inputs"', '"threshold"', '"pass_condition"']
        block = self.document().firstBlock()
        capturing_calibration = False
        calibration_balance = 0
        while block.isValid():
            text = block.text()
            if any(key in text for key in highlighted_keys):
                blocks.append(block.blockNumber())
            stripped_text = text.strip()
            if capturing_calibration:
                blocks.append(block.blockNumber())
                calibration_balance += text.count("{") - text.count("}")
                if calibration_balance <= 0:
                    capturing_calibration = False
            elif stripped_text.startswith("CALIBRATION") and "=" in stripped_text:
                blocks.append(block.blockNumber())
                calibration_balance = text.count("{") - text.count("}")
                if calibration_balance > 0:
                    capturing_calibration = True
            block = block.next()
        return sorted(set(blocks))

    def _collect_array_spans(self, key_name: str) -> list[tuple[int, int]]:
        spans: list[tuple[int, int]] = []
        block = self.document().firstBlock()
        capturing = False
        start_position = 0
        bracket_balance = 0
        while block.isValid():
            text = block.text()
            if not capturing and f'"{key_name}"' in text:
                start_position = block.position()
                bracket_balance = text.count("[") - text.count("]")
                if bracket_balance <= 0:
                    spans.append((start_position, block.position() + len(text)))
                else:
                    capturing = True
            elif capturing:
                bracket_balance += text.count("[") - text.count("]")
                if bracket_balance <= 0:
                    spans.append((start_position, block.position() + len(text)))
                    capturing = False
            block = block.next()
        return spans

    def _find_literal_ranges(self, needle: str, spans: list[tuple[int, int]] | None = None) -> list[tuple[int, int]]:
        if not needle:
            return []
        haystack = self.toPlainText()
        allowed_spans = spans or [(0, len(haystack))]
        ranges: list[tuple[int, int]] = []
        for start_limit, end_limit in allowed_spans:
            cursor = start_limit
            while cursor < end_limit:
                found = haystack.find(needle, cursor, end_limit)
                if found < 0:
                    break
                ranges.append((found, found + len(needle)))
                cursor = found + len(needle)
        return ranges

    def set_search_results(self, ranges: list[tuple[int, int]], current_range: tuple[int, int] | None = None) -> None:
        self._search_ranges = ranges
        self._current_search_range = current_range
        self._refresh_decorations()

    def clear_issue_locations(self) -> None:
        self._issue_ranges = []
        self._issue_line_blocks = []
        self._refresh_decorations()

    def set_issue_locations(self, locations: list[tuple[int | None, int | None]]) -> None:
        self._issue_ranges = []
        self._issue_line_blocks = []
        for line_number, column_number in locations:
            if line_number is None or line_number <= 0:
                continue
            block = self.document().findBlockByNumber(line_number - 1)
            if not block.isValid():
                continue
            self._issue_line_blocks.append(block.blockNumber())
            block_text = block.text()
            start = block.position()
            if column_number is None or column_number <= 0:
                end = start + max(1, len(block_text))
            else:
                offset = min(max(0, column_number - 1), len(block_text))
                start += offset
                end = min(block.position() + len(block_text), start + 1)
            self._issue_ranges.append((start, max(start + 1, end)))
        self._refresh_decorations()

    def focus_location(self, line_number: int | None, column_number: int | None = None) -> None:
        if line_number is None or line_number <= 0:
            self.setFocus()
            return
        block = self.document().findBlockByNumber(line_number - 1)
        if not block.isValid():
            self.setFocus()
            return
        cursor = self.textCursor()
        position = block.position()
        if column_number is not None and column_number > 0:
            position += min(max(0, column_number - 1), len(block.text()))
        cursor.setPosition(position)
        self.setTextCursor(cursor)
        self.centerCursor()
        self.setFocus()

    def clear_search_results(self) -> None:
        self._search_ranges = []
        self._current_search_range = None
        self._refresh_decorations()

    def clear_transient_highlights(self) -> None:
        self._replacement_ranges = []
        self._navigation_ranges = []
        self._undo_ranges = []
        self._pending_undo_range = None
        self._highlight_next_change_as_undo = False
        self._refresh_decorations()

    def set_replacement_ranges(self, ranges: list[tuple[int, int]]) -> None:
        self._replacement_ranges = ranges
        self._refresh_decorations()

    def focus_named_input(self, signal_name: str | None, *, raw_inputs_only: bool = False) -> None:
        if not signal_name:
            self._navigation_ranges = []
            self._refresh_decorations()
            return
        spans = self._collect_array_spans("raw_inputs") if raw_inputs_only else None
        targets = self._find_literal_ranges(f'"{signal_name}"', spans)
        if not targets:
            targets = self._find_literal_ranges(signal_name, spans)
        self._navigation_ranges = targets
        if targets:
            cursor = self.textCursor()
            cursor.setPosition(targets[0][0])
            cursor.setPosition(targets[0][1], QTextCursor.MoveMode.KeepAnchor)
            self.setTextCursor(cursor)
            self.centerCursor()
            self.setFocus()
        self._refresh_decorations()

    def _refresh_decorations(self) -> None:
        selections: list[QTextEdit.ExtraSelection] = []
        for block_number in self._collect_config_key_line_blocks():
            selections.append(self._make_full_width_selection(block_number, "#fff4bf"))
        for block_number in self._issue_line_blocks:
            selections.append(self._make_full_width_selection(block_number, "#fee2e2"))
        for start, end in self._search_ranges:
            selections.append(self._make_range_selection(start, end, "#dbeafe"))
        if self._current_search_range is not None:
            selections.append(self._make_range_selection(self._current_search_range[0], self._current_search_range[1], "#93c5fd"))
        for start, end in self._replacement_ranges:
            selections.append(self._make_range_selection(start, end, "#bbf7d0"))
        for start, end in self._navigation_ranges:
            selections.append(self._make_range_selection(start, end, "#fcd34d"))
        for start, end in self._issue_ranges:
            selections.append(self._make_range_selection(start, end, "#fca5a5"))
        for start, end in self._undo_ranges:
            selections.append(self._make_range_selection(start, end, "#fca5a5"))
        self.setExtraSelections(selections)

    def _on_document_contents_change(self, position: int, chars_removed: int, chars_added: int) -> None:
        if not self._highlight_next_change_as_undo:
            return
        document_length = max(0, len(self.toPlainText()))
        if chars_added > 0:
            end = min(document_length, position + chars_added)
            self._pending_undo_range = (position, end)
        elif document_length > 0:
            start = min(max(0, position - 1), max(0, document_length - 1))
            end = min(document_length, max(start + 1, position + 1))
            self._pending_undo_range = (start, end)
        else:
            self._pending_undo_range = None
        self._highlight_next_change_as_undo = False

    def undo(self) -> None:  # noqa: D401
        self._highlight_next_change_as_undo = True
        self._pending_undo_range = None
        super().undo()
        self._undo_ranges = [] if self._pending_undo_range is None else [self._pending_undo_range]
        self._pending_undo_range = None
        self._refresh_decorations()

    def keyPressEvent(self, event) -> None:  # noqa: ANN001
        if event.matches(QKeySequence.StandardKey.Undo):
            self.undo()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self._undo_ranges:
            self._undo_ranges = []
            self._refresh_decorations()
        super().mousePressEvent(event)

    def focusOutEvent(self, event) -> None:  # noqa: ANN001,N802
        self.clear_transient_highlights()
        super().focusOutEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        token = self._token_at_position(event.position().toPoint())
        super().mouseDoubleClickEvent(event)
        if token and callable(self._jump_callback) and self._jump_callback(token):
            event.accept()


class SearchReplaceBar(QWidget):
    def __init__(self, editor: JumpAwarePlainTextEdit, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._editor = editor
        self.setVisible(False)

        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(6)
        layout.setVerticalSpacing(4)

        self.find_edit = QLineEdit()
        self.find_edit.setPlaceholderText("查找")
        self.find_edit.textChanged.connect(self._refresh_search_highlights)
        self.replace_edit = QLineEdit()
        self.replace_edit.setPlaceholderText("替换为")
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #58708b;")

        previous_button = QPushButton("上一个")
        previous_button.clicked.connect(lambda: self.find_next(backward=True))
        next_button = QPushButton("下一个")
        next_button.clicked.connect(self.find_next)
        replace_button = QPushButton("替换当前")
        replace_button.clicked.connect(self.replace_current)
        replace_all_button = QPushButton("全部替换")
        replace_all_button.clicked.connect(self.replace_all)
        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.hide_panel)

        layout.addWidget(QLabel("查找"), 0, 0)
        layout.addWidget(self.find_edit, 0, 1)
        layout.addWidget(previous_button, 0, 2)
        layout.addWidget(next_button, 0, 3)
        layout.addWidget(close_button, 0, 4)
        layout.addWidget(QLabel("替换"), 1, 0)
        layout.addWidget(self.replace_edit, 1, 1)
        layout.addWidget(replace_button, 1, 2)
        layout.addWidget(replace_all_button, 1, 3)
        layout.addWidget(self.status_label, 1, 4)

    def show_panel(self) -> None:
        self.setVisible(True)
        selected_text = self._editor.textCursor().selectedText().strip()
        if selected_text and "\u2029" not in selected_text:
            self.find_edit.setText(selected_text)
        self.find_edit.setFocus()
        self.find_edit.selectAll()
        self._refresh_search_highlights()

    def hide_panel(self) -> None:
        self.setVisible(False)
        self._editor.clear_search_results()

    def _find_ranges(self, text: str) -> list[tuple[int, int]]:
        if not text:
            return []
        document = self._editor.document()
        cursor = QTextCursor(document)
        ranges: list[tuple[int, int]] = []
        while True:
            cursor = document.find(text, cursor)
            if cursor.isNull():
                break
            ranges.append((cursor.selectionStart(), cursor.selectionEnd()))
            next_cursor = QTextCursor(document)
            next_cursor.setPosition(cursor.selectionEnd())
            cursor = next_cursor
        return ranges

    def _refresh_search_highlights(self) -> None:
        find_text = self.find_edit.text()
        ranges = self._find_ranges(find_text)
        current_cursor = self._editor.textCursor()
        current_range = None
        if current_cursor.hasSelection():
            candidate = (current_cursor.selectionStart(), current_cursor.selectionEnd())
            if candidate in ranges:
                current_range = candidate
        self._editor.set_search_results(ranges, current_range)
        self.status_label.setText(f"{len(ranges)} 处匹配" if find_text else "")

    def find_next(self, backward: bool = False) -> bool:
        find_text = self.find_edit.text()
        if not find_text:
            self.status_label.setText("请输入要查找的内容")
            return False
        document = self._editor.document()
        cursor = self._editor.textCursor()
        if cursor.hasSelection():
            cursor.setPosition(cursor.selectionStart() if backward else cursor.selectionEnd())
        flags = QTextDocument.FindFlag.FindBackward if backward else QTextDocument.FindFlag(0)
        found = document.find(find_text, cursor, flags)
        if found.isNull():
            restart = QTextCursor(document)
            if backward:
                restart.movePosition(QTextCursor.MoveOperation.End)
            found = document.find(find_text, restart, flags)
        if found.isNull():
            self.status_label.setText("未找到匹配内容")
            self._editor.set_search_results(self._find_ranges(find_text), None)
            return False
        self._editor.setTextCursor(found)
        self._editor.centerCursor()
        current_range = (found.selectionStart(), found.selectionEnd())
        self._editor.set_search_results(self._find_ranges(find_text), current_range)
        return True

    def replace_current(self) -> None:
        if self._editor.isReadOnly():
            QMessageBox.information(self, "只读文件", "当前文件为保护示例文件，只支持查找，不支持替换。")
            return
        find_text = self.find_edit.text()
        if not find_text:
            self.status_label.setText("请输入要查找的内容")
            return
        cursor = self._editor.textCursor()
        if not cursor.hasSelection() or cursor.selectedText() != find_text:
            if not self.find_next():
                return
            cursor = self._editor.textCursor()
        start = cursor.selectionStart()
        cursor.insertText(self.replace_edit.text())
        self._editor.set_replacement_ranges([(start, start + len(self.replace_edit.text()))])
        self._refresh_search_highlights()
        QMessageBox.information(self, "替换完成", "已替换 1 处。")

    def replace_all(self) -> None:
        if self._editor.isReadOnly():
            QMessageBox.information(self, "只读文件", "当前文件为保护示例文件，只支持查找，不支持替换。")
            return
        find_text = self.find_edit.text()
        if not find_text:
            self.status_label.setText("请输入要查找的内容")
            return
        document = self._editor.document()
        search_cursor = document.find(find_text, 0)
        replacement_ranges: list[tuple[int, int]] = []
        while not search_cursor.isNull():
            start = search_cursor.selectionStart()
            search_cursor.insertText(self.replace_edit.text())
            replacement_ranges.append((start, start + len(self.replace_edit.text())))
            next_cursor = QTextCursor(document)
            next_cursor.setPosition(start + len(self.replace_edit.text()))
            search_cursor = document.find(find_text, next_cursor)
        self._editor.set_replacement_ranges(replacement_ranges)
        self._refresh_search_highlights()
        QMessageBox.information(self, "替换完成", f"已替换 {len(replacement_ranges)} 处。")


class PanelSignalTable(QTableWidget):
    def __init__(self, panel_id: int, remove_callback, color_callback, drop_callback, parent: QWidget | None = None) -> None:
        super().__init__(0, 3, parent)
        self._panel_id = panel_id
        self._remove_callback = remove_callback
        self._color_callback = color_callback
        self._drop_callback = drop_callback
        self.setHorizontalHeaderLabels(["信号", "光标1", "光标2"])
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(False)
        self.setShowGrid(False)
        self.setWordWrap(False)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(17)
        self.horizontalHeader().setStretchLastSection(False)
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.setMinimumWidth(180)
        self.setMaximumWidth(560)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet(
            "QTableWidget { border: none; background: transparent; }"
            "QHeaderView::section { padding: 1px 2px; border: none; background: rgba(238, 245, 252, 0.18); color: #627588; }"
            "QTableWidget::item { padding: 0 1px; }"
            "QTableWidget::item:selected { background: rgba(198, 221, 243, 0.34); color: #0f2740; }"
        )
        self.set_cursor_column_visibility(0)

    def set_cursor_column_visibility(self, cursor_mode: int) -> None:
        show_cursor_1 = cursor_mode >= 1
        show_cursor_2 = cursor_mode >= 2
        self.setColumnHidden(1, not show_cursor_1)
        self.setColumnHidden(2, not show_cursor_2)

    def desired_table_width(self) -> int:
        for column in range(self.columnCount()):
            if not self.isColumnHidden(column):
                self.resizeColumnToContents(column)
        visible_width = sum(self.columnWidth(column) for column in range(self.columnCount()) if not self.isColumnHidden(column))
        scrollbar_width = self.verticalScrollBar().sizeHint().width() if self.verticalScrollBar().isVisible() else 0
        desired = visible_width + scrollbar_width + self.frameWidth() * 2 + 18
        return max(self.minimumWidth(), min(self.maximumWidth(), desired))

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Delete:
            signal_names = self._selected_signal_names()
            if signal_names:
                for signal_name in signal_names:
                    self._remove_callback(signal_name)
                event.accept()
                return
        super().keyPressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        item = self.itemAt(event.position().toPoint())
        if item is not None and item.column() == 0:
            self._color_callback(item.text())
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def startDrag(self, supported_actions) -> None:  # noqa: ANN001
        signal_names = self._selected_signal_names()
        if not signal_names:
            return
        mime = QMimeData()
        payload = _build_signal_drag_payload(signal_names, source_panel_id=self._panel_id)
        mime.setData(SIGNAL_DRAG_MIME_TYPE, payload.encode("utf-8"))
        mime.setText("\n".join(signal_names))
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.MoveAction)

    def dragEnterEvent(self, event) -> None:  # noqa: ANN001
        signal_names, _source_panel_id = _parse_signal_drag_payload(event.mimeData())
        if signal_names:
            event.acceptProposedAction()
            return
        event.ignore()

    def dragMoveEvent(self, event) -> None:  # noqa: ANN001
        signal_names, _source_panel_id = _parse_signal_drag_payload(event.mimeData())
        if signal_names:
            event.acceptProposedAction()
            return
        event.ignore()

    def dropEvent(self, event) -> None:  # noqa: ANN001
        signal_names, source_panel_id = _parse_signal_drag_payload(event.mimeData())
        if signal_names:
            self._drop_callback(signal_names, source_panel_id)
            event.acceptProposedAction()
            return
        event.ignore()

    def _selected_signal_names(self) -> list[str]:
        signal_names: list[str] = []
        for row_index in sorted({index.row() for index in self.selectedIndexes()}):
            item = self.item(row_index, 0)
            if item is not None and item.text().strip():
                signal_names.append(item.text().strip())
        return signal_names


class MappingEditorTable(QTableWidget):
    def __init__(self, read_only_columns: set[int] | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._read_only_columns = set(read_only_columns or set())
        self._after_paste_callback = None

    def keyPressEvent(self, event) -> None:  # noqa: ANN001
        if event.matches(QKeySequence.StandardKey.Copy):
            self._copy_selection_to_clipboard()
            event.accept()
            return
        if event.matches(QKeySequence.StandardKey.Paste):
            if self._paste_from_clipboard():
                event.accept()
                return
        if event.key() == Qt.Key.Key_Delete:
            if self._clear_selected_cells():
                event.accept()
                return
        super().keyPressEvent(event)

    def _copy_selection_to_clipboard(self) -> None:
        ranges = self.selectedRanges()
        if not ranges:
            return
        selected_range = ranges[0]
        lines: list[str] = []
        for row_index in range(selected_range.topRow(), selected_range.bottomRow() + 1):
            row_values: list[str] = []
            for column_index in range(selected_range.leftColumn(), selected_range.rightColumn() + 1):
                item = self.item(row_index, column_index)
                row_values.append("" if item is None else item.text())
            lines.append("\t".join(row_values))
        QApplication.clipboard().setText("\n".join(lines))

    def _paste_from_clipboard(self) -> bool:
        ranges = self.selectedRanges()
        text = QApplication.clipboard().text()
        if not ranges or not text.strip():
            return False
        start_row = ranges[0].topRow()
        start_column = ranges[0].leftColumn()
        rows = [row.split("\t") for row in text.replace("\r\n", "\n").split("\n") if row != ""]
        if not rows:
            return False
        self.blockSignals(True)
        try:
            for row_offset, row_values in enumerate(rows):
                target_row = start_row + row_offset
                if target_row >= self.rowCount():
                    break
                for column_offset, value in enumerate(row_values):
                    target_column = start_column + column_offset
                    if target_column >= self.columnCount():
                        break
                    if target_column in self._read_only_columns:
                        continue
                    item = self.item(target_row, target_column)
                    if item is None:
                        item = QTableWidgetItem("")
                        self.setItem(target_row, target_column, item)
                    item.setText(value)
        finally:
            self.blockSignals(False)
        if callable(self._after_paste_callback):
            self._after_paste_callback()
        self.viewport().update()
        return True

    def _clear_selected_cells(self) -> bool:
        indexes = self.selectedIndexes()
        if not indexes:
            return False
        self.blockSignals(True)
        try:
            for index in indexes:
                if index.column() in self._read_only_columns:
                    continue
                item = self.item(index.row(), index.column())
                if item is None:
                    item = QTableWidgetItem("")
                    self.setItem(index.row(), index.column(), item)
                item.setText("")
        finally:
            self.blockSignals(False)
        if callable(self._after_paste_callback):
            self._after_paste_callback()
        self.viewport().update()
        return True


class InteractiveChartView(QChartView):
    def __init__(self, cursor_move_callback, signal_drop_callback, x_range_sync_callback=None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cursor_move_callback = cursor_move_callback
        self._signal_drop_callback = signal_drop_callback
        self._x_range_sync_callback = x_range_sync_callback
        self._last_pan_position: QPoint | None = None
        self._right_drag_origin: QPoint | None = None
        self._x_bounds: tuple[float, float] | None = None
        self._y_bounds: tuple[float, float] | None = None
        self.zoom_mode = "both"
        self.cursor_mode = 0
        self.cursor_positions: list[float | None] = [None, None]
        self._dragging_cursor_index: int | None = None
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRubberBand(QChartView.RubberBand.NoRubberBand)
        self.setAcceptDrops(True)
        self._cursor_labels = [QLabel(self.viewport()), QLabel(self.viewport())]
        for label in self._cursor_labels:
            label.setStyleSheet(
                "background: rgba(255,255,255,0.92);"
                "border: 1px solid #c9d8ea;"
                "border-radius: 8px;"
                "padding: 1px 6px;"
                "font-size: 11px;"
                "color: #0f172a;"
            )
            label.hide()
        self._delta_label = QLabel(self.viewport())
        self._delta_label.setStyleSheet(
            "background: rgba(15,23,42,0.85);"
            "border-radius: 8px;"
            "padding: 2px 8px;"
            "font-size: 11px;"
            "color: white;"
        )
        self._delta_label.hide()
        self._selection_band = QRubberBand(QRubberBand.Shape.Rectangle, self.viewport())
        self._selection_band.hide()

    def set_data_bounds(self, x_bounds: tuple[float, float] | None, y_bounds: tuple[float, float] | None) -> None:
        self._x_bounds = x_bounds
        self._y_bounds = y_bounds
        self._refresh_cursor_labels()

    def set_cursor_state(self, cursor_mode: int, cursor_positions: list[float | None]) -> None:
        self.cursor_mode = cursor_mode
        self.cursor_positions = [None, None] if cursor_mode == 0 else list(cursor_positions)
        if cursor_mode == 0:
            self._dragging_cursor_index = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
        self._refresh_cursor_labels()
        self.viewport().update()

    def current_axis_ranges(self) -> tuple[tuple[float, float] | None, tuple[float, float] | None]:
        axis_x, axis_y = self._get_axes()
        x_range = None if axis_x is None else (float(axis_x.min()), float(axis_x.max()))
        y_range = None if axis_y is None else (float(axis_y.min()), float(axis_y.max()))
        return x_range, y_range

    def restore_axis_ranges(
        self,
        x_range: tuple[float, float] | None,
        y_range: tuple[float, float] | None,
        x_bounds: tuple[float, float] | None,
        y_bounds: tuple[float, float] | None,
    ) -> None:
        axis_x, axis_y = self._get_axes()
        if axis_x is not None and x_range is not None and x_bounds is not None:
            lower = max(x_bounds[0], min(x_range[0], x_bounds[1]))
            upper = min(x_bounds[1], max(x_range[1], x_bounds[0]))
            if upper <= lower:
                lower, upper = x_bounds
            axis_x.setRange(lower, upper)
        if axis_y is not None and y_range is not None and y_bounds is not None:
            lower = max(y_bounds[0], min(y_range[0], y_bounds[1]))
            upper = min(y_bounds[1], max(y_range[1], y_bounds[0]))
            if upper <= lower:
                lower, upper = y_bounds
            axis_y.setRange(lower, upper)
        self._refresh_cursor_labels()

    def set_x_range(self, x_range: tuple[float, float], x_bounds: tuple[float, float] | None) -> None:
        axis_x, _axis_y = self._get_axes()
        if axis_x is None or x_bounds is None:
            return
        lower = max(x_bounds[0], min(x_range[0], x_bounds[1]))
        upper = min(x_bounds[1], max(x_range[1], x_bounds[0]))
        if upper <= lower:
            lower, upper = x_bounds
        axis_x.setRange(lower, upper)
        self._refresh_cursor_labels()

    def fit_all(self) -> None:
        self._apply_bounds(True, True)

    def fit_x(self) -> None:
        self._apply_bounds(True, False)

    def fit_y(self) -> None:
        visible_bounds = self._visible_y_bounds()
        if visible_bounds is not None:
            self.set_y_range(visible_bounds, self._y_bounds)
            return
        self._apply_bounds(False, True)

    def _apply_bounds(self, reset_x: bool, reset_y: bool) -> None:
        axis_x, axis_y = self._get_axes()
        if axis_x is None or axis_y is None:
            return
        if reset_x and self._x_bounds is not None:
            axis_x.setRange(*self._x_bounds)
        if reset_y and self._y_bounds is not None:
            axis_y.setRange(*self._y_bounds)
        self._refresh_cursor_labels()

    def set_y_range(self, y_range: tuple[float, float], y_bounds: tuple[float, float] | None) -> None:
        _axis_x, axis_y = self._get_axes()
        if axis_y is None:
            return
        lower, upper = y_range
        if y_bounds is not None:
            lower = max(y_bounds[0], min(lower, y_bounds[1]))
            upper = min(y_bounds[1], max(upper, y_bounds[0]))
            if upper <= lower:
                lower, upper = y_bounds
        axis_y.setRange(lower, upper)
        self._refresh_cursor_labels()

    def _get_axes(self) -> tuple[QValueAxis | None, QValueAxis | None]:
        chart = self.chart()
        if chart is None:
            return None, None
        axes = chart.axes()
        axis_x = next((axis for axis in axes if isinstance(axis, QValueAxis) and axis.alignment() == Qt.AlignmentFlag.AlignBottom), None)
        axis_y = next((axis for axis in axes if isinstance(axis, QValueAxis) and axis.alignment() == Qt.AlignmentFlag.AlignLeft), None)
        return axis_x, axis_y

    def _plot_area_rect(self) -> QRect | None:
        chart = self.chart()
        if chart is None:
            return None
        plot_area = chart.plotArea().toRect()
        if plot_area.width() <= 0 or plot_area.height() <= 0:
            return None
        return plot_area

    def _update_selection_band(self, current_pos: QPoint) -> None:
        plot_area = self._plot_area_rect()
        if self._right_drag_origin is None or plot_area is None:
            return
        left = max(plot_area.left(), min(self._right_drag_origin.x(), current_pos.x()))
        right = min(plot_area.right(), max(self._right_drag_origin.x(), current_pos.x()))
        if right <= left:
            self._selection_band.hide()
            return
        self._selection_band.setGeometry(QRect(QPoint(left, plot_area.top()), QPoint(right, plot_area.bottom())))
        self._selection_band.show()

    def _apply_band_zoom(self, end_pos: QPoint) -> None:
        if self._right_drag_origin is None:
            return
        plot_area = self._plot_area_rect()
        axis_x, _axis_y = self._get_axes()
        chart = self.chart()
        if plot_area is None or axis_x is None or chart is None:
            return
        left = max(plot_area.left(), min(self._right_drag_origin.x(), end_pos.x()))
        right = min(plot_area.right(), max(self._right_drag_origin.x(), end_pos.x()))
        if right - left < 6:
            return
        center_y = plot_area.center().y()
        left_value = chart.mapToValue(QPointF(float(left), float(center_y))).x()
        right_value = chart.mapToValue(QPointF(float(right), float(center_y))).x()
        lower = float(min(left_value, right_value))
        upper = float(max(left_value, right_value))
        if upper <= lower:
            return
        if self._x_range_sync_callback is not None:
            self._x_range_sync_callback((lower, upper), self)
        else:
            self.set_x_range((lower, upper), self._x_bounds)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            self._last_pan_position = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        if event.button() == Qt.MouseButton.RightButton:
            self._right_drag_origin = event.position().toPoint()
            self._update_selection_band(self._right_drag_origin)
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            cursor_index = self._hit_test_cursor(event.position())
            if cursor_index is not None:
                self._dragging_cursor_index = cursor_index
                self.setCursor(Qt.CursorShape.SizeHorCursor)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._dragging_cursor_index is not None and self.chart() is not None:
            chart_point = self.chart().mapToValue(event.position())
            self._cursor_move_callback(self._dragging_cursor_index, float(chart_point.x()))
            event.accept()
            return
        if self._last_pan_position is not None and self.chart() is not None:
            delta = event.position().toPoint() - self._last_pan_position
            self.chart().scroll(-delta.x(), delta.y())
            self._last_pan_position = event.position().toPoint()
            axis_x, _axis_y = self._get_axes()
            if axis_x is not None and self._x_range_sync_callback is not None:
                self._x_range_sync_callback((float(axis_x.min()), float(axis_x.max())), self)
            self._refresh_cursor_labels()
            event.accept()
            return
        if self._right_drag_origin is not None:
            self._update_selection_band(event.position().toPoint())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._dragging_cursor_index is not None:
            self._dragging_cursor_index = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return
        if event.button() == Qt.MouseButton.MiddleButton:
            self._last_pan_position = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return
        if event.button() == Qt.MouseButton.RightButton:
            self._apply_band_zoom(event.position().toPoint())
            self._right_drag_origin = None
            self._selection_band.hide()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        axis_x, axis_y = self._get_axes()
        if axis_x is None or axis_y is None:
            super().wheelEvent(event)
            return
        modifiers = event.modifiers()
        effective_zoom_mode = self.zoom_mode
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            effective_zoom_mode = "x"
        elif modifiers & Qt.KeyboardModifier.ShiftModifier:
            effective_zoom_mode = "y"
        factor = 0.85 if event.angleDelta().y() > 0 else 1.18
        if effective_zoom_mode in {"both", "x"}:
            self._scale_axis(axis_x, factor)
            if self._x_range_sync_callback is not None:
                self._x_range_sync_callback((float(axis_x.min()), float(axis_x.max())), self)
        if effective_zoom_mode in {"both", "y"}:
            self._scale_axis(axis_y, factor)
        self._refresh_cursor_labels()
        event.accept()

    def resizeEvent(self, event) -> None:  # noqa: ANN001
        super().resizeEvent(event)
        self._refresh_cursor_labels()

    def dragEnterEvent(self, event) -> None:  # noqa: ANN001
        signal_names, _source_panel_id = _parse_signal_drag_payload(event.mimeData())
        if signal_names:
            event.acceptProposedAction()
            return
        event.ignore()

    def dragMoveEvent(self, event) -> None:  # noqa: ANN001
        signal_names, _source_panel_id = _parse_signal_drag_payload(event.mimeData())
        if signal_names:
            event.acceptProposedAction()
            return
        event.ignore()

    def dropEvent(self, event) -> None:  # noqa: ANN001
        signal_names, source_panel_id = _parse_signal_drag_payload(event.mimeData())
        if signal_names:
            self._signal_drop_callback(signal_names, source_panel_id)
            event.acceptProposedAction()
            return
        event.ignore()

    def _hit_test_cursor(self, position) -> int | None:  # noqa: ANN001
        axis_x, _axis_y = self._get_axes()
        chart = self.chart()
        if chart is None or axis_x is None or self.cursor_mode == 0:
            return None
        for cursor_index in range(self.cursor_mode):
            cursor_x = self.cursor_positions[cursor_index]
            if cursor_x is None:
                continue
            x_pos = chart.mapToPosition(QPointF(cursor_x, axis_x.min())).x()
            if abs(position.x() - x_pos) <= 8:
                return cursor_index
        return None

    def _refresh_cursor_labels(self) -> None:
        axis_x, axis_y = self._get_axes()
        chart = self.chart()
        if chart is None or axis_x is None or axis_y is None or self.cursor_mode == 0:
            for label in self._cursor_labels:
                label.hide()
            self._delta_label.hide()
            return
        for label in self._cursor_labels:
            label.hide()
        self._delta_label.hide()
        self.viewport().update()

    def paintEvent(self, event) -> None:  # noqa: ANN001
        super().paintEvent(event)
        axis_x, axis_y = self._get_axes()
        chart = self.chart()
        if chart is None or axis_x is None or axis_y is None or self.cursor_mode == 0:
            return
        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        plot_area = chart.plotArea()
        pen_colors = [QColor("#0f766e"), QColor("#9333ea")]
        for cursor_index in range(self.cursor_mode):
            cursor_x = self.cursor_positions[cursor_index]
            if cursor_x is None:
                continue
            point = chart.mapToPosition(QPointF(float(cursor_x), axis_y.min()))
            painter.setPen(QPen(pen_colors[cursor_index % len(pen_colors)], 1.6, Qt.PenStyle.SolidLine))
            painter.drawLine(QPointF(point.x(), plot_area.top()), QPointF(point.x(), plot_area.bottom()))
        painter.end()

    def _scale_axis(self, axis: QValueAxis, factor: float) -> None:
        lower = axis.min()
        upper = axis.max()
        center = (lower + upper) / 2.0
        half_range = max((upper - lower) * factor / 2.0, 1e-6)
        axis.setRange(center - half_range, center + half_range)

    def _visible_y_bounds(self) -> tuple[float, float] | None:
        axis_x, _axis_y = self._get_axes()
        chart = self.chart()
        if axis_x is None or chart is None:
            return None
        x_min = float(axis_x.min())
        x_max = float(axis_x.max())
        y_values: list[float] = []
        for series in chart.series():
            points = getattr(series, "pointsVector", None)
            if callable(points):
                iterable = points()
            else:
                iterable = getattr(series, "points", lambda: [])()
            for point in iterable:
                x_value = float(point.x())
                y_value = float(point.y())
                if x_min <= x_value <= x_max and math.isfinite(y_value):
                    y_values.append(y_value)
        if not y_values:
            return None
        lower = min(y_values)
        upper = max(y_values)
        if upper > lower:
            padding = max((upper - lower) * 0.08, 1e-6)
            return lower - padding, upper + padding
        padding = max(abs(lower) * 0.15, 1.0)
        return lower - padding, upper + padding


class ChartPanelFrame(QFrame):
    def __init__(
        self,
        panel_id: int,
        drop_callback,
        remove_callback,
        cursor_move_callback,
        signal_remove_callback,
        signal_color_callback,
        width_sync_callback,
        initial_signal_table_width: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.panel_id = panel_id
        self._remove_callback = remove_callback
        self._width_sync_callback = width_sync_callback
        self._target_signal_table_width = int(initial_signal_table_width)
        self._suppress_splitter_signal = False
        self.setObjectName("chartPanelCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.view = InteractiveChartView(cursor_move_callback, drop_callback)
        self.view.setFrameShape(QFrame.Shape.NoFrame)
        self.signal_table = PanelSignalTable(panel_id, signal_remove_callback, signal_color_callback, drop_callback)
        self.body_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.body_splitter.setChildrenCollapsible(False)
        self.body_splitter.setHandleWidth(1)
        self.body_splitter.setStyleSheet("QSplitter::handle { background: #e2eaf2; }")
        self.body_splitter.addWidget(self.view)
        self.body_splitter.addWidget(self.signal_table)
        self.body_splitter.setStretchFactor(0, 1)
        self.body_splitter.setStretchFactor(1, 0)
        self.body_splitter.splitterMoved.connect(self._on_splitter_moved)

        layout.addWidget(self.body_splitter, 1)

        self.close_button = QToolButton(self)
        self.close_button.setText("✕")
        self.close_button.setToolTip("删除当前显示框")
        self.close_button.setStyleSheet(
            "min-width: 16px; max-width: 16px; min-height: 16px; max-height: 16px;"
            "padding: 0; color: white; background: #dc2626; border: 1px solid #b91c1c; border-radius: 9px;"
        )
        self.close_button.clicked.connect(lambda _checked=False: self._remove_callback())
        self.close_button.raise_()
        QTimer.singleShot(0, self._position_close_button)
        QTimer.singleShot(0, self._apply_target_signal_table_width)

        self.setStyleSheet("QFrame#chartPanelCard { background: transparent; border: none; }")
        self.body_splitter.setSizes([1280, self._target_signal_table_width])

    def _on_splitter_moved(self, _position: int, _index: int) -> None:
        if self._suppress_splitter_signal:
            return
        self._target_signal_table_width = int(self.signal_table.width())
        self._position_close_button()
        if callable(self._width_sync_callback):
            self._width_sync_callback(self.panel_id, self._target_signal_table_width)

    def _apply_target_signal_table_width(self) -> None:
        splitter_width = self.body_splitter.width()
        if splitter_width <= 0:
            return
        target_width = max(self.signal_table.minimumWidth(), min(self.signal_table.maximumWidth(), int(self._target_signal_table_width)))
        handle_width = self.body_splitter.handleWidth()
        left_width = max(1, splitter_width - target_width - handle_width)
        self._suppress_splitter_signal = True
        self.body_splitter.setSizes([left_width, target_width])
        self._suppress_splitter_signal = False
        self._position_close_button()

    def set_signal_table_width(self, width: int) -> None:
        self._target_signal_table_width = int(width)
        self._apply_target_signal_table_width()

    def _position_close_button(self) -> None:
        button_x = max(4, self.width() - self.close_button.width() - 8)
        self.close_button.move(button_x, 6)

    def resizeEvent(self, event) -> None:  # noqa: ANN001
        super().resizeEvent(event)
        self._position_close_button()
        self._apply_target_signal_table_width()

    def showEvent(self, event) -> None:  # noqa: ANN001
        super().showEvent(event)
        QTimer.singleShot(0, self._position_close_button)
        QTimer.singleShot(0, self._apply_target_signal_table_width)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.engine = AnalysisEngine(runtime_logger=self._emit_runtime_log)
        self.derived_signal_entries = []
        self.kpi_spec_entries = []
        self.kpi_groups: list[dict[str, object]] = []
        self.template_entries = []
        self.plot_signal_names: list[str] = []
        self.queue_entries: list[dict[str, str]] = []
        self.results_by_key: dict[str, AnalysisResult] = {}
        self.result_order: list[str] = []
        self.selected_chart_path: str | None = None
        self.output_dir = Path.cwd() / "outputs_gui"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.derived_signal_editor_path: Path | None = None
        self.kpi_editor_path: Path | None = None
        self.template_editor_path: Path | None = None
        self._chart_view_state = load_chart_view_state()
        self.chart_sheets: list[dict[str, object]] = []
        self.active_chart_sheet_index = 0
        self.chart_panels: list[dict[str, object]] = []
        self.cursor_mode = 0
        self.cursor_positions: list[float | None] = [None, None]
        self._next_cursor_slot = 0
        self._chart_colors = [
            QColor("#0f766e"),
            QColor("#2563eb"),
            QColor("#c2410c"),
            QColor("#b91c1c"),
            QColor("#7c3aed"),
            QColor("#0891b2"),
            QColor("#059669"),
        ]
        self._signal_browser_all: list[str] = []
        self._derived_signal_names: list[str] = []
        self._formula_signal_names: list[str] = []
        self._interface_signal_names: list[str] = []
        self._kpi_signal_names: list[str] = []
        self._kpi_path_by_name: dict[str, Path] = {}
        self._derived_signal_path_by_name: dict[str, Path] = {}
        self._editor_loading = False
        self._derived_signal_editor_dirty = False
        self._kpi_editor_dirty = False
        self._signal_color_map: dict[str, QColor] = {}
        self._shared_chart_x_range: tuple[float, float] | None = None
        self._chart_frame_cache: dict[str, object] = {}
        self._chart_sample_cache: dict[str, object] = {}
        self._loading_kpi_group = False
        self._persisting_mapping = False
        self._log_link_targets: dict[str, dict[str, object]] = {}
        self._log_link_counter = 0
        self._next_chart_panel_id = 0
        self._signal_table_width_sync_in_progress = False
        self._mapping_persist_timer = QTimer(self)
        self._mapping_persist_timer.setSingleShot(True)
        self._mapping_persist_timer.timeout.connect(self._persist_mapping_editor_state)

        self.setWindowTitle("自动化数据分析工具 V1.2")
        self.resize(1720, 1060)
        self.setStyleSheet(APP_STYLE)
        self._build_ui()
        self._bind_shortcuts()
        app = QApplication.instance()
        if app is not None:
            app.focusChanged.connect(self._on_application_focus_changed)
        self.reload_runtime_configs(log_message=False)

    def _sort_text_key(self, text: str) -> str:
        normalized = str(text or "").strip()
        if lazy_pinyin is None:
            return normalized.lower()
        return "".join(lazy_pinyin(normalized)).lower()

    def _make_result_key(self, path: str, group_key: str) -> str:
        return f"{group_key}::{path}"

    def _result_output_stem(self, result: AnalysisResult) -> str:
        stem = result.context.source_path.stem
        group_key = str(result.context.metadata.get("kpi_group_key", "__all_kpis__"))
        if group_key == "__all_kpis__":
            return stem
        suffix = "".join(character if character.isalnum() or character in {"-", "_"} else "_" for character in group_key)
        return f"{stem}_{suffix}"

    def _build_ui(self) -> None:
        root = QWidget(self)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_home_tab(), "主页")
        self.tabs.addTab(self._build_results_tab(), "结果")
        self.tabs.addTab(self._build_charts_tab(), "曲线")
        self.tabs.addTab(self._build_config_workbench_tab(), "配置工作台")
        self.tabs.currentChanged.connect(self._clear_editor_transient_highlights)

        layout.addWidget(self.tabs, 1)
        self.setCentralWidget(root)

    def _build_home_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        queue_group = QGroupBox("文件与执行")
        queue_layout = QVBoxLayout(queue_group)
        group_row = QHBoxLayout()
        self.queue_group_combo = QComboBox()
        group_row.addWidget(QLabel("分析组"))
        group_row.addWidget(self.queue_group_combo, 1)
        queue_layout.addLayout(group_row)

        toolbar = QHBoxLayout()
        for button in [
            self._make_button("添加文件", QStyle.StandardPixmap.SP_FileDialogDetailedView),
            self._make_button("添加目录", QStyle.StandardPixmap.SP_DirOpenIcon),
            self._make_button("移除选中", QStyle.StandardPixmap.SP_TrashIcon),
            self._make_button("清空", QStyle.StandardPixmap.SP_DialogResetButton),
            self._make_button("分析选中", QStyle.StandardPixmap.SP_MediaPlay),
            self._make_button("分析全部", QStyle.StandardPixmap.SP_ArrowForward),
        ]:
            toolbar.addWidget(button)
        _accent_btn_style = (
            "QPushButton { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #3b82f6, stop:1 #2563eb);"
            " color: #ffffff; border: 1px solid #1d4ed8; font-weight: 600; }"
            " QPushButton:hover { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #60a5fa, stop:1 #3b82f6); }"
            " QPushButton:pressed { background: #1d4ed8; }"
        )
        toolbar.itemAt(4).widget().setStyleSheet(_accent_btn_style)
        toolbar.itemAt(5).widget().setStyleSheet(_accent_btn_style)
        toolbar.itemAt(0).widget().clicked.connect(self.add_files)
        toolbar.itemAt(1).widget().clicked.connect(self.add_folder)
        toolbar.itemAt(2).widget().clicked.connect(self.remove_selected_queue_items)
        toolbar.itemAt(3).widget().clicked.connect(self.clear_queue)
        toolbar.itemAt(4).widget().clicked.connect(self.analyze_selected)
        toolbar.itemAt(5).widget().clicked.connect(self.analyze_all)
        toolbar.addStretch(1)

        self.queue_stats_label = QLabel("当前 0 个文件，已完成分析 0 个")
        self.queue_stats_label.setStyleSheet("color: #5b738c; padding-left: 4px;")
        self.file_list = QueueListWidget()
        self.file_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.file_list.set_delete_callback(self.remove_selected_queue_items)
        self.file_list.itemSelectionChanged.connect(self.on_file_selection_changed)

        queue_layout.addLayout(toolbar)
        queue_layout.addWidget(self.queue_stats_label)
        self.analysis_progress_bar = QProgressBar()
        self.analysis_progress_bar.setRange(0, 100)
        self.analysis_progress_bar.setValue(0)
        self.analysis_progress_bar.setFormat("等待分析")
        queue_layout.addWidget(self.analysis_progress_bar)

        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        content_splitter.addWidget(self.file_list)

        dbc_panel = QGroupBox("DBC")
        dbc_layout = QVBoxLayout(dbc_panel)
        dbc_toolbar = QHBoxLayout()
        add_dbc_button = QToolButton()
        add_dbc_button.setText("+")
        add_dbc_button.setToolTip("添加 DBC 文件")
        add_dbc_button.clicked.connect(self.add_dbc_files)
        remove_dbc_button = QToolButton()
        remove_dbc_button.setText("-")
        remove_dbc_button.setToolTip("删除选中的 DBC 文件")
        remove_dbc_button.clicked.connect(self.remove_selected_dbc_files)
        dbc_toolbar.addWidget(add_dbc_button)
        dbc_toolbar.addWidget(remove_dbc_button)
        dbc_toolbar.addStretch(1)
        self.dbc_list = QListWidget()
        self.dbc_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        dbc_hint = QLabel("总线 BLF/MF4 解码需要 DBC。")
        dbc_hint.setStyleSheet("color: #5b738c; font-size: 11px;")
        dbc_layout.addLayout(dbc_toolbar)
        dbc_layout.addWidget(self.dbc_list, 1)
        dbc_layout.addWidget(dbc_hint)
        content_splitter.addWidget(dbc_panel)
        content_splitter.setStretchFactor(0, 5)
        content_splitter.setStretchFactor(1, 2)
        content_splitter.setSizes([900, 260])
        queue_layout.addWidget(content_splitter, 1)

        log_group = QGroupBox("运行日志")
        log_layout = QVBoxLayout(log_group)
        log_header = QHBoxLayout()
        log_header.addStretch(1)
        clear_log_button = QPushButton("清空")
        clear_log_button.setFixedHeight(30)
        clear_log_button.clicked.connect(self.clear_runtime_log)
        log_header.addWidget(clear_log_button)
        log_layout.addLayout(log_header)
        self.log_area = QTextBrowser()
        self.log_area.setReadOnly(True)
        self.log_area.setOpenLinks(False)
        self.log_area.anchorClicked.connect(self._on_log_anchor_clicked)
        log_layout.addWidget(self.log_area)

        layout.addWidget(queue_group, 1)
        layout.addWidget(log_group, 1)
        return tab

    def _build_results_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        filter_row = QHBoxLayout()
        self.rule_status_filter = QComboBox()
        self.rule_status_filter.addItem("ALL", "all")
        self.rule_status_filter.addItem("达标", "pass")
        self.rule_status_filter.addItem("未达标", "fail")
        self.rule_status_filter.currentIndexChanged.connect(self.refresh_result_views)
        filter_row.addWidget(QLabel("结果筛选"))
        filter_row.addWidget(self.rule_status_filter)
        filter_row.addStretch(1)
        self.rule_table = QTableWidget(0, 6)
        self.rule_table.setHorizontalHeaderLabels(["KPI", "描述", "单位", "数值", "达标要求", "结果"])
        self._configure_readonly_table(self.rule_table)
        self.rule_table.cellDoubleClicked.connect(self.on_rule_table_cell_double_clicked)
        layout.addLayout(filter_row)
        layout.addWidget(self.rule_table)
        return tab

    def _build_charts_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        tools_group = QFrame()
        tools_group.setObjectName("chartToolsBar")
        tools_group.setStyleSheet("QFrame#chartToolsBar { background: rgba(255, 255, 255, 0.52); border: none; border-radius: 6px; }")
        tools_layout = QGridLayout(tools_group)
        tools_layout.setContentsMargins(2, 2, 2, 0)
        tools_layout.setHorizontalSpacing(2)
        tools_layout.setVerticalSpacing(1)
        self.result_scope_combo = QComboBox()
        self.result_scope_combo.currentIndexChanged.connect(self.on_result_scope_changed)
        self.result_scope_combo.setMinimumWidth(260)
        prev_button = QToolButton()
        prev_button.setText("←")
        prev_button.setToolTip("上一个文件")
        prev_button.clicked.connect(self.select_previous_result)
        next_button = QToolButton()
        next_button.setText("→")
        next_button.setToolTip("下一个文件")
        next_button.clicked.connect(self.select_next_result)
        add_panel_button = QToolButton()
        add_panel_button.setText("+")
        add_panel_button.setStyleSheet(TOOL_BUTTON_STYLE)
        add_panel_button.setToolTip("新增显示框")
        add_panel_button.clicked.connect(self.add_chart_panel)

        self.signal_library_button = QToolButton()
        self.signal_library_button.setText("≣")
        self.signal_library_button.setStyleSheet(TOOL_BUTTON_STYLE)
        self.signal_library_button.setToolTip("打开信号库")
        self.signal_library_button.setCheckable(True)
        self.signal_library_button.toggled.connect(self.toggle_signal_library)

        formula_signal_button = QToolButton()
        formula_signal_button.setText("ƒx")
        formula_signal_button.setStyleSheet(TOOL_BUTTON_STYLE)
        formula_signal_button.setToolTip("新增表达式信号，例如 C = A + B")
        formula_signal_button.clicked.connect(self.create_formula_signal)

        fit_all_button = QToolButton()
        fit_all_button.setText("⤢")
        fit_all_button.setStyleSheet(TOOL_BUTTON_STYLE)
        fit_all_button.setToolTip("最佳缩放")
        fit_all_button.clicked.connect(self.fit_all_charts)

        fit_x_button = QToolButton()
        fit_x_button.setText("↔")
        fit_x_button.setStyleSheet(TOOL_BUTTON_STYLE)
        fit_x_button.setToolTip("横向最佳缩放")
        fit_x_button.clicked.connect(self.fit_x_charts)

        fit_y_button = QToolButton()
        fit_y_button.setText("↕")
        fit_y_button.setStyleSheet(TOOL_BUTTON_STYLE)
        fit_y_button.setToolTip("纵向最佳缩放")
        fit_y_button.clicked.connect(self.fit_y_charts)

        self.cursor_mode_button = QToolButton()
        self.cursor_mode_button.setText("⌖")
        self.cursor_mode_button.setStyleSheet(TOOL_BUTTON_STYLE)
        self.cursor_mode_button.setToolTip("切换光标模式，Ctrl+W")
        self.cursor_mode_button.clicked.connect(self.cycle_cursor_mode)

        self.zoom_x_mode_button = QToolButton()
        self.zoom_x_mode_button.setText("⇆")
        self.zoom_x_mode_button.setStyleSheet(TOOL_BUTTON_STYLE)
        self.zoom_x_mode_button.setToolTip("横向缩放模式，Ctrl + 滚轮 可快速横向缩放")
        self.zoom_x_mode_button.setCheckable(True)
        self.zoom_x_mode_button.toggled.connect(self.on_zoom_mode_button_toggled)

        self.zoom_y_mode_button = QToolButton()
        self.zoom_y_mode_button.setText("⇅")
        self.zoom_y_mode_button.setStyleSheet(TOOL_BUTTON_STYLE)
        self.zoom_y_mode_button.setToolTip("纵向缩放模式，Shift + 滚轮 可快速纵向缩放")
        self.zoom_y_mode_button.setCheckable(True)
        self.zoom_y_mode_button.toggled.connect(self.on_zoom_mode_button_toggled)

        self.signal_library_popup = QFrame(self, Qt.WindowType.Popup)
        self.signal_library_popup.setVisible(False)
        self.signal_library_popup.setStyleSheet("background: #ffffff; border: 1px solid #d9e3ed; border-radius: 6px;")
        popup_layout = QVBoxLayout(self.signal_library_popup)
        popup_layout.setContentsMargins(10, 10, 10, 10)
        popup_layout.setSpacing(8)
        self.signal_search_edit = QLineEdit()
        self.signal_search_edit.setPlaceholderText("搜索信号")
        self.signal_search_edit.textChanged.connect(self.filter_signal_browser)
        popup_layout.addWidget(self.signal_search_edit)
        browser_columns = QHBoxLayout()
        browser_columns.setSpacing(10)

        interface_column = QVBoxLayout()
        interface_label = QLabel("接口信号")
        interface_label.setStyleSheet("font-weight: 700; color: #12324d;")
        self.interface_signal_browser = DraggableSignalListWidget()
        self.interface_signal_browser.setMinimumHeight(320)
        interface_column.addWidget(interface_label)
        interface_column.addWidget(self.interface_signal_browser, 1)

        kpi_column = QVBoxLayout()
        kpi_label = QLabel("KPI 信号")
        kpi_label.setStyleSheet("font-weight: 700; color: #12324d;")
        self.kpi_signal_browser = DraggableSignalListWidget()
        self.kpi_signal_browser.setMinimumHeight(320)
        kpi_column.addWidget(kpi_label)
        kpi_column.addWidget(self.kpi_signal_browser, 1)

        derived_column = QVBoxLayout()
        derived_label = QLabel("派生量")
        derived_label.setStyleSheet("font-weight: 700; color: #12324d;")
        self.derived_signal_browser = DraggableSignalListWidget()
        self.derived_signal_browser.setMinimumHeight(320)
        derived_column.addWidget(derived_label)
        derived_column.addWidget(self.derived_signal_browser, 1)

        custom_column = QVBoxLayout()
        custom_label = QLabel("自定义信号")
        custom_label.setStyleSheet("font-weight: 700; color: #12324d;")
        self.custom_signal_browser = FormulaSignalListWidget(self.edit_formula_signal, self.delete_formula_signal, self)
        self.custom_signal_browser.setMinimumHeight(320)
        custom_column.addWidget(custom_label)
        custom_column.addWidget(self.custom_signal_browser, 1)

        browser_columns.addLayout(interface_column, 1)
        browser_columns.addLayout(kpi_column, 1)
        browser_columns.addLayout(derived_column, 1)
        browser_columns.addLayout(custom_column, 1)
        popup_layout.addLayout(browser_columns, 1)

        tools_layout.setHorizontalSpacing(4)
        tools_layout.setVerticalSpacing(4)
        tools_layout.addWidget(QLabel("文件"), 0, 0)
        tools_layout.addWidget(self.result_scope_combo, 0, 1)
        tools_layout.addWidget(prev_button, 0, 2)
        tools_layout.addWidget(next_button, 0, 3)
        tools_layout.addWidget(self.signal_library_button, 0, 4)
        tools_layout.addWidget(formula_signal_button, 0, 5)
        tools_layout.addWidget(add_panel_button, 0, 6)
        tools_layout.addWidget(fit_all_button, 0, 7)
        tools_layout.addWidget(fit_x_button, 0, 8)
        tools_layout.addWidget(fit_y_button, 0, 9)
        tools_layout.addWidget(self.zoom_x_mode_button, 0, 10)
        tools_layout.addWidget(self.zoom_y_mode_button, 0, 11)
        tools_layout.addWidget(self.cursor_mode_button, 0, 12)
        tools_layout.setColumnStretch(13, 1)

        sheets_row = QHBoxLayout()
        sheets_row.setContentsMargins(0, 0, 0, 0)
        sheets_row.setSpacing(6)

        self.chart_sheet_tabs = QTabWidget()
        self.chart_sheet_tabs.setDocumentMode(True)
        self.chart_sheet_tabs.setMovable(False)
        self.chart_sheet_tabs.currentChanged.connect(self.on_chart_sheet_changed)
        self.chart_sheet_tabs.tabBarDoubleClicked.connect(self.on_chart_sheet_tab_double_clicked)
        self.chart_sheet_tabs.setStyleSheet(
            "QTabWidget::pane { border: none; background: transparent; }"
            "QTabBar::tab { background: rgba(233, 240, 247, 0.48); border: 1px solid rgba(205, 217, 229, 0.7); padding: 4px 12px; margin-right: 4px; border-radius: 7px; color: #627487; font-weight: 600; }"
            "QTabBar::tab:selected { background: #12344d; border-color: #12344d; color: #ffffff; }"
            "QTabBar::tab:hover:!selected { background: rgba(255, 255, 255, 0.86); color: #17324a; }"
        )
        sheets_row.addWidget(self.chart_sheet_tabs, 1)

        add_sheet_button = QToolButton()
        add_sheet_button.setText("＋")
        add_sheet_button.setStyleSheet(TOOL_BUTTON_STYLE)
        add_sheet_button.setToolTip("新增工作表")
        add_sheet_button.clicked.connect(self.add_chart_sheet)

        rename_sheet_button = QToolButton()
        rename_sheet_button.setText("✎")
        rename_sheet_button.setStyleSheet(TOOL_BUTTON_STYLE)
        rename_sheet_button.setToolTip("重命名当前工作表")
        rename_sheet_button.clicked.connect(self.rename_current_chart_sheet)

        delete_sheet_button = QToolButton()
        delete_sheet_button.setText("－")
        delete_sheet_button.setStyleSheet(TOOL_BUTTON_STYLE)
        delete_sheet_button.setToolTip("删除当前工作表")
        delete_sheet_button.clicked.connect(self.remove_current_chart_sheet)

        sheets_row.addWidget(add_sheet_button)
        sheets_row.addWidget(rename_sheet_button)
        sheets_row.addWidget(delete_sheet_button)

        self.chart_status_label = QLabel("光标未启用")
        self.chart_status_label.setStyleSheet("color: #73879a; padding: 0; font-weight: 600; min-height: 12px; font-size: 10px;")

        self.chart_splitter = QSplitter(Qt.Orientation.Vertical)
        self.chart_splitter.setChildrenCollapsible(False)
        self.chart_splitter.setHandleWidth(1)
        self.chart_splitter.setStyleSheet("QSplitter::handle { background: #d5e2ef; }")
        layout.addWidget(tools_group)
        layout.addLayout(sheets_row)
        layout.addWidget(self.chart_status_label)
        layout.addWidget(self.chart_splitter, 1)
        return tab

    def _build_config_workbench_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.config_tabs = QTabWidget()
        self.config_tabs.currentChanged.connect(self._clear_editor_transient_highlights)
        self.config_tabs.addTab(self._build_derived_signal_editor_tab(), "派生量编辑")
        self.config_tabs.addTab(self._build_kpi_editor_tab(), "KPI 编辑")
        self.config_tabs.addTab(self._build_kpi_group_tab(), "KPI 分组")
        self.config_tabs.addTab(self._build_mapping_editor_tab(), "接口映射")
        self.config_tabs.addTab(self._build_template_editor_tab(), "导出与模板")
        layout.addWidget(self.config_tabs)
        return tab

    def _build_kpi_group_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        toolbar = QHBoxLayout()
        self.kpi_group_editor_combo = QComboBox()
        self.kpi_group_editor_combo.currentIndexChanged.connect(self.load_kpi_group_from_combo)
        toolbar.addWidget(self.kpi_group_editor_combo, 1)
        create_button = self._make_button("新增分组", QStyle.StandardPixmap.SP_FileIcon)
        delete_button = self._make_button("删除分组", QStyle.StandardPixmap.SP_TrashIcon)
        create_button.clicked.connect(self.create_kpi_group)
        delete_button.clicked.connect(self.delete_current_kpi_group)
        toolbar.addWidget(create_button)
        toolbar.addWidget(delete_button)
        self.kpi_group_name_edit = QLineEdit()
        self.kpi_group_name_edit.setPlaceholderText("分组名称")
        self.kpi_group_name_edit.editingFinished.connect(self.on_kpi_group_name_editing_finished)
        self.kpi_group_kpi_list = QListWidget()
        self.kpi_group_kpi_list.itemChanged.connect(self.on_kpi_group_item_changed)
        self.kpi_group_kpi_list.itemDoubleClicked.connect(self.open_kpi_from_group_item)
        self.kpi_group_notice = QLabel("勾选组内需要参与分析的 KPI。默认组展示全部 KPI，只读。")
        self.kpi_group_notice.setStyleSheet("color: #58708b;")
        layout.addLayout(toolbar)
        layout.addWidget(self.kpi_group_name_edit)
        layout.addWidget(self.kpi_group_notice)
        layout.addWidget(self.kpi_group_kpi_list, 1)
        return tab

    def _build_derived_signal_editor_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        toolbar = QHBoxLayout()
        self.derived_signal_editor_combo = QComboBox()
        self.derived_signal_editor_combo.currentIndexChanged.connect(self.load_derived_signal_from_editor_combo)
        toolbar.addWidget(self.derived_signal_editor_combo, 1)
        self.derived_signal_create_button = self._make_button("新增派生量", QStyle.StandardPixmap.SP_FileIcon)
        self.derived_signal_delete_button = self._make_button("删除", QStyle.StandardPixmap.SP_TrashIcon)
        self.derived_signal_create_button.clicked.connect(self.create_derived_signal_file)
        self.derived_signal_delete_button.clicked.connect(self.delete_derived_signal_file)
        for button in [self.derived_signal_create_button, self.derived_signal_delete_button]:
            toolbar.addWidget(button)
        self.derived_signal_editor_path_label = QLabel("未加载派生量文件")
        self.derived_signal_editor_notice = QLabel("")
        self.derived_signal_editor_notice.setStyleSheet("color: #58708b;")
        self.derived_signal_editor_notice.setText("派生量用于承载多个 KPI 共用、且只需计算一次的透明中间序列。")
        self.derived_signal_editor = JumpAwarePlainTextEdit(self._open_derived_from_derived_editor_token, highlight_config_keys=True)
        self.derived_signal_editor.textChanged.connect(self._on_derived_signal_editor_text_changed)
        self.derived_signal_search_panel = SearchReplaceBar(self.derived_signal_editor)
        layout.addLayout(toolbar)
        layout.addWidget(self.derived_signal_editor_path_label)
        layout.addWidget(self.derived_signal_editor_notice)
        layout.addWidget(self.derived_signal_search_panel)
        layout.addWidget(self.derived_signal_editor, 1)
        return tab

    def _build_kpi_editor_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        toolbar = QHBoxLayout()
        self.kpi_editor_combo = QComboBox()
        self.kpi_editor_combo.currentIndexChanged.connect(self.load_kpi_from_editor_combo)
        toolbar.addWidget(self.kpi_editor_combo, 1)
        self.kpi_create_button = self._make_button("新增 KPI", QStyle.StandardPixmap.SP_FileIcon)
        self.kpi_delete_button = self._make_button("删除", QStyle.StandardPixmap.SP_TrashIcon)
        self.kpi_create_button.clicked.connect(self.create_kpi_file)
        self.kpi_delete_button.clicked.connect(self.delete_kpi_file)
        for button in [self.kpi_create_button, self.kpi_delete_button]:
            toolbar.addWidget(button)
        self.kpi_editor_path_label = QLabel("未加载 KPI 文件")
        self.kpi_editor_notice = QLabel("")
        self.kpi_editor_notice.setStyleSheet("color: #58708b;")
        self.kpi_editor_notice.setText("每个 KPI 文件同时维护数值计算、规则说明、派生量依赖和达标判定。")
        self.kpi_editor = JumpAwarePlainTextEdit(self._open_derived_from_kpi_editor_token, highlight_config_keys=True)
        self.kpi_editor.textChanged.connect(self._on_kpi_editor_text_changed)
        self.kpi_search_panel = SearchReplaceBar(self.kpi_editor)
        layout.addLayout(toolbar)
        layout.addWidget(self.kpi_editor_path_label)
        layout.addWidget(self.kpi_editor_notice)
        layout.addWidget(self.kpi_search_panel)
        layout.addWidget(self.kpi_editor, 1)
        return tab

    def _build_template_editor_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        settings_group = QGroupBox("导出设置")
        settings_layout = QGridLayout(settings_group)
        self.output_dir_edit = QLineEdit(str(self.output_dir))
        choose_output_button = self._make_button("选择目录", QStyle.StandardPixmap.SP_DirOpenIcon)
        choose_output_button.clicked.connect(self.choose_output_dir)
        self.report_title_edit = QLineEdit("TCS 打滑控制自动分析报告")
        self.active_template_combo = QComboBox()
        self.export_html_checkbox = QCheckBox("HTML")
        self.export_html_checkbox.setChecked(True)
        self.export_word_checkbox = QCheckBox("Word")
        self.export_word_checkbox.setChecked(True)
        export_row = QHBoxLayout()
        for widget in [self.export_html_checkbox, self.export_word_checkbox]:
            export_row.addWidget(widget)
        export_row.addStretch(1)
        export_current_button = self._make_button("导出当前结果", QStyle.StandardPixmap.SP_DialogSaveButton)
        export_current_button.clicked.connect(self.export_selected_results)
        open_output_button = self._make_button("打开输出目录", QStyle.StandardPixmap.SP_DirIcon)
        open_output_button.clicked.connect(self.open_output_dir)
        export_row.addWidget(export_current_button)
        export_row.addWidget(open_output_button)
        settings_layout.addWidget(QLabel("报告目录"), 0, 0)
        settings_layout.addWidget(self.output_dir_edit, 0, 1)
        settings_layout.addWidget(choose_output_button, 0, 2)
        settings_layout.addWidget(QLabel("报告标题"), 1, 0)
        settings_layout.addWidget(self.report_title_edit, 1, 1, 1, 2)
        settings_layout.addWidget(QLabel("当前模板"), 2, 0)
        settings_layout.addWidget(self.active_template_combo, 2, 1, 1, 2)
        settings_layout.addWidget(QLabel("自动导出"), 3, 0)
        settings_layout.addLayout(export_row, 3, 1, 1, 2)

        toolbar = QHBoxLayout()
        self.template_editor_combo = QComboBox()
        self.template_editor_combo.currentIndexChanged.connect(self.load_template_from_editor_combo)
        toolbar.addWidget(self.template_editor_combo, 1)
        self.template_create_button = self._make_button("新增模板", QStyle.StandardPixmap.SP_FileIcon)
        self.template_save_button = self._make_button("保存", QStyle.StandardPixmap.SP_DialogSaveButton)
        self.template_delete_button = self._make_button("删除", QStyle.StandardPixmap.SP_TrashIcon)
        self.template_create_button.clicked.connect(self.create_template_file)
        self.template_save_button.clicked.connect(self.save_template_file)
        self.template_delete_button.clicked.connect(self.delete_template_file)
        for button in [self.template_create_button, self.template_save_button, self.template_delete_button]:
            toolbar.addWidget(button)
        self.template_editor_path_label = QLabel("未加载模板文件")
        self.template_editor_notice = QLabel("")
        self.template_editor_notice.setStyleSheet("color: #9a3412;")
        self.template_editor = JumpAwarePlainTextEdit(highlight_config_keys=False)
        self.template_search_panel = SearchReplaceBar(self.template_editor)
        layout.addWidget(settings_group)
        layout.addLayout(toolbar)
        layout.addWidget(self.template_editor_path_label)
        layout.addWidget(self.template_editor_notice)
        layout.addWidget(self.template_search_panel)
        layout.addWidget(self.template_editor, 1)
        return tab

    def _build_mapping_editor_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        toolbar = QHBoxLayout()
        add_custom_button = self._make_button("新增自定义信号", QStyle.StandardPixmap.SP_FileIcon)
        add_custom_button.clicked.connect(self.add_custom_mapping_row)
        delete_custom_button = self._make_button("删除自定义信号", QStyle.StandardPixmap.SP_TrashIcon)
        delete_custom_button.clicked.connect(self.delete_selected_custom_mapping_row)
        for button in [add_custom_button, delete_custom_button]:
            toolbar.addWidget(button)
        toolbar.addStretch(1)
        self.mapping_tabs = QTabWidget()
        self.system_mapping_table = MappingEditorTable(read_only_columns={0, 1})
        self.system_mapping_table.setColumnCount(len(SYSTEM_MAPPING_HEADERS))
        self.system_mapping_table.setHorizontalHeaderLabels(SYSTEM_MAPPING_HEADERS)
        self._configure_mapping_table(self.system_mapping_table)
        self.system_mapping_table._after_paste_callback = self._refresh_and_schedule_mapping_persist
        self.system_mapping_table.cellChanged.connect(self._on_mapping_table_changed)
        self.system_mapping_table.cellDoubleClicked.connect(self.open_mapping_source_from_cell)
        self.custom_mapping_table = MappingEditorTable(read_only_columns=set())
        self.custom_mapping_table.setColumnCount(len(CUSTOM_MAPPING_HEADERS))
        self.custom_mapping_table.setHorizontalHeaderLabels(CUSTOM_MAPPING_HEADERS)
        self._configure_mapping_table(self.custom_mapping_table)
        self.custom_mapping_table._after_paste_callback = self._refresh_and_schedule_mapping_persist
        self.custom_mapping_table.cellChanged.connect(self._on_mapping_table_changed)
        system_tab = QWidget()
        system_layout = QVBoxLayout(system_tab)
        system_layout.addWidget(self.system_mapping_table)
        custom_tab = QWidget()
        custom_layout = QVBoxLayout(custom_tab)
        custom_layout.addWidget(self.custom_mapping_table)
        self.mapping_tabs.addTab(system_tab, "系统信号")
        self.mapping_tabs.addTab(custom_tab, "自定义信号")
        layout.addLayout(toolbar)
        layout.addWidget(self.mapping_tabs, 1)
        return tab

    def _bind_shortcuts(self) -> None:
        shortcut = QShortcut(QKeySequence("Ctrl+W"), self)
        shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        shortcut.activated.connect(self.cycle_cursor_mode)
        save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        save_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        save_shortcut.activated.connect(self.save_current_text_editor)
        find_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        find_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        find_shortcut.activated.connect(self.open_current_find_panel)

    def _editor_owner_for_widget(self, widget: QWidget | None) -> str | None:
        if widget is None:
            return None

        def belongs(container: QWidget | None) -> bool:
            current = widget
            while current is not None:
                if current is container:
                    return True
                current = current.parentWidget()
            return False

        if belongs(getattr(self, "derived_signal_editor", None)) or belongs(getattr(self, "derived_signal_search_panel", None)):
            return "derived"
        if belongs(getattr(self, "kpi_editor", None)) or belongs(getattr(self, "kpi_search_panel", None)):
            return "kpi"
        if belongs(getattr(self, "template_editor", None)) or belongs(getattr(self, "template_search_panel", None)):
            return "template"
        return None

    def _clear_editor_transient_highlights(self, *_args) -> None:
        for editor in [
            getattr(self, "derived_signal_editor", None),
            getattr(self, "kpi_editor", None),
            getattr(self, "template_editor", None),
        ]:
            if isinstance(editor, JumpAwarePlainTextEdit):
                editor.clear_transient_highlights()

    def _on_application_focus_changed(self, old: QWidget | None, new: QWidget | None) -> None:
        old_owner = self._editor_owner_for_widget(old)
        new_owner = self._editor_owner_for_widget(new)
        if old_owner is not None and old_owner != new_owner:
            self._clear_editor_transient_highlights()

    def open_current_find_panel(self) -> None:
        if self.tabs.currentIndex() != 3:
            return
        current_index = self.config_tabs.currentIndex()
        if current_index == 0:
            self.derived_signal_search_panel.show_panel()
            return
        if current_index == 1:
            self.kpi_search_panel.show_panel()
            return
        if current_index == 4:
            self.template_search_panel.show_panel()

    def save_current_text_editor(self) -> None:
        if not hasattr(self, "config_tabs"):
            return
        current_index = self.config_tabs.currentIndex()
        if current_index == 0:
            self.save_derived_signal_file()
            return
        if current_index == 1:
            self.save_kpi_file()
            return
        if current_index == 4:
            self.save_template_file()

    def _make_button(self, text: str, icon: QStyle.StandardPixmap) -> QPushButton:
        button = QPushButton(text)
        button.setIcon(self.style().standardIcon(icon))
        return button

    def _emit_runtime_log(self, level: str, message: str) -> None:
        if hasattr(self, "log_area"):
            self.log(level, message)

    def _register_log_link(self, target: dict[str, object]) -> str:
        self._log_link_counter += 1
        link_id = str(self._log_link_counter)
        self._log_link_targets[link_id] = dict(target)
        return link_id

    def _on_log_anchor_clicked(self, url: QUrl) -> None:
        raw = url.toString()
        if not raw.startswith("configjump:"):
            return
        link_id = raw.split(":", 1)[1]
        target = self._log_link_targets.get(link_id)
        if not target:
            return
        self._open_config_path_with_location(
            Path(str(target.get("path", ""))),
            line=target.get("line"),
            column=target.get("column"),
        )

    def clear_runtime_log(self) -> None:
        self.log_area.clear()
        self._log_link_targets.clear()
        self._log_link_counter = 0

    def _should_display_log_message(self, message: str) -> bool:
        suppressed_prefixes = (
            "输出目录已更新:",
            "已从目录载入 ",
            "已开始新的分析批次",
            "已从队列移除 ",
            "文件队列已清空",
            "已添加 ",
            "已删除 ",
            "已创建 KPI 分组:",
            "KPI 分组已保存:",
            "已删除 KPI 分组:",
            "分析已完成，当前未勾选自动导出格式。",
            "光标模式已切换为:",
            "KPI、模板、接口映射和表达式信号配置已重新加载。",
            "表达式信号已保存:",
            "已更新自定义信号:",
            "已删除自定义信号:",
            "已载入派生量文件:",
            "已载入 KPI 文件:",
            "已载入报告模板:",
            "KPI 文件已保存:",
            "派生量文件已保存:",
            "模板文件已保存:",
            "接口映射已保存。",
            "已导出 ",
        )
        return not any(message.startswith(prefix) for prefix in suppressed_prefixes)

    def _clear_editor_issue_markers(self, editor: JumpAwarePlainTextEdit) -> None:
        editor.clear_issue_locations()

    def _apply_editor_issue_markers(self, editor: JumpAwarePlainTextEdit, issues) -> None:  # noqa: ANN001
        editor.set_issue_locations([(getattr(issue, "line", None), getattr(issue, "column", None)) for issue in issues])

    def _issue_path_label(self, path: Path) -> str:
        if path.parent.name == "kpi_specs":
            return "KPI"
        if path.parent.name == "derived_signals":
            return "派生量"
        return "配置"

    def _issue_summary_text(self, issue) -> str:  # noqa: ANN001
        line_text = "未知行" if getattr(issue, "line", None) is None else f"第{issue.line}行"
        column = getattr(issue, "column", None)
        column_text = "" if column is None else f" 第{column}列"
        return f"{self._issue_path_label(Path(issue.path))} {Path(issue.path).name} {line_text}{column_text}: {issue.message}"

    def _present_validation_issues(self, title: str, issues, *, open_first: bool = True) -> None:  # noqa: ANN001
        if not issues:
            return
        first_issue = issues[0]
        if open_first:
            self._open_config_path_with_location(Path(first_issue.path), line=first_issue.line, column=first_issue.column, issues=issues)
        summary_lines = [self._issue_summary_text(issue) for issue in issues[:5]]
        if len(issues) > 5:
            summary_lines.append(f"其余 {len(issues) - 5} 个问题请在编辑器红色高亮处继续修正。")
        self.log(
            "error",
            f"{title}: {self._issue_summary_text(first_issue)}",
            link_target={"path": str(first_issue.path), "line": first_issue.line, "column": first_issue.column},
        )
        QMessageBox.warning(self, title, "\n".join(summary_lines))

    def _open_config_path_with_location(
        self,
        path: Path,
        *,
        line: int | None = None,
        column: int | None = None,
        issues=None,
    ) -> bool:  # noqa: ANN001
        if not path.exists() or not self._confirm_current_editor_navigation():
            return False
        self.tabs.setCurrentIndex(3)
        if path.parent.name == "kpi_specs":
            self.config_tabs.setCurrentIndex(1)
            self.load_kpi_file(path, log_message=False)
            if issues is not None:
                self._apply_editor_issue_markers(self.kpi_editor, [issue for issue in issues if Path(issue.path) == path])
            self.kpi_editor.focus_location(line, column)
            return True
        if path.parent.name == "derived_signals":
            self.config_tabs.setCurrentIndex(0)
            self.load_derived_signal_file(path, log_message=False)
            if issues is not None:
                self._apply_editor_issue_markers(self.derived_signal_editor, [issue for issue in issues if Path(issue.path) == path])
            self.derived_signal_editor.focus_location(line, column)
            return True
        return False

    def _validate_runtime_definitions_before_analysis(self) -> bool:
        issues = validate_runtime_definition_files()
        if not issues:
            return True
        self._present_validation_issues("KPI/派生量静态检查未通过", issues)
        return False

    def _log_runtime_execution_error(self, source_path: Path, error: ConfigExecutionError) -> None:
        context = error.context
        for line in context.output_lines:
            self.log("info", f"[{context.owner_kind}:{context.owner_name}:{context.stage}] {line}")
        line_text = "" if context.line is None else f" 第{context.line}行"
        self.log(
            "error",
            f"分析失败: {source_path.name}，{context.owner_kind} {context.owner_name} 的 {context.stage} 执行报错{line_text}: {context.message}",
            link_target={"path": str(context.path), "line": context.line},
        )

    def _configure_readonly_table(self, table: QTableWidget) -> None:
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setAlternatingRowColors(True)
        table.setShowGrid(True)
        table.verticalHeader().setVisible(False)
        header = table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        table.setStyleSheet(
            "QTableWidget { gridline-color: #e6edf5; selection-background-color: #dbeafe; }"
            "QTableWidget::item { padding: 6px; }"
        )

    def _configure_mapping_table(self, table: QTableWidget) -> None:
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        table.verticalHeader().setVisible(False)
        header = table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        if table is self.system_mapping_table:
            for index in range(len(SYSTEM_MAPPING_HEADERS)):
                if index == 0:
                    header.resizeSection(index, 180)
                elif index == 1:
                    header.resizeSection(index, 320)
                else:
                    header.resizeSection(index, 220)
            return
        for index in range(len(CUSTOM_MAPPING_HEADERS)):
            header.resizeSection(index, 180 if index == 0 else 220)

    def choose_output_dir(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "选择输出目录", str(self.output_dir))
        if not selected:
            return
        self.output_dir = Path(selected)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir_edit.setText(str(self.output_dir))
        self.log("info", f"输出目录已更新: {self.output_dir}")

    def add_files(self) -> None:
        selected, _ = QFileDialog.getOpenFileNames(self, "选择日志文件", "", FILE_DIALOG_FILTER)
        if selected:
            self._add_paths([Path(path) for path in selected])

    def add_folder(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "选择日志目录", "")
        if not selected:
            return
        paths = self.engine.collect_supported_files(selected, recursive=True)
        self._add_paths(paths)
        self.log("info", f"已从目录载入 {len(paths)} 个文件: {selected}")

    def _has_existing_analysis_session(self) -> bool:
        return bool(self.results_by_key or self.result_order or self.selected_chart_path)

    def _reset_analysis_session(self, log_message: bool = True) -> None:
        self.queue_entries.clear()
        self.results_by_key.clear()
        self.result_order.clear()
        self.selected_chart_path = None
        self._shared_chart_x_range = None
        self._chart_frame_cache.clear()
        self._chart_sample_cache.clear()
        self.file_list.clear()
        self.rule_table.clearSpans()
        self.rule_table.setRowCount(0)
        self._refresh_result_scope_combo()
        self._update_queue_stats()
        self.analysis_progress_bar.setValue(0)
        self.analysis_progress_bar.setFormat("等待分析")
        self.refresh_result_views()
        if log_message:
            self.log("warning", "已开始新的分析批次，上一批次的队列与结果已清空。")

    def remove_selected_queue_items(self) -> None:
        items = [item for item in self.file_list.selectedItems() if not bool(item.data(QUEUE_HEADER_ROLE))]
        if not items:
            return
        removed_entries: set[tuple[str, str]] = set()
        for item in items:
            removed_entries.add((str(item.data(QUEUE_PATH_ROLE)), str(item.data(QUEUE_GROUP_ROLE) or "__all_kpis__")))
        self.queue_entries = [
            entry for entry in self.queue_entries if (entry["path"], entry["group_key"]) not in removed_entries
        ]
        self._rebuild_queue_list_widget()
        self._update_queue_stats()
        self.log("warning", f"已从队列移除 {len(removed_entries)} 个文件。")

    def clear_queue(self) -> None:
        self.queue_entries.clear()
        self.file_list.clear()
        self._update_queue_stats()
        self.analysis_progress_bar.setValue(0)
        self.analysis_progress_bar.setFormat("等待分析")
        self.log("warning", "文件队列已清空，分析结果已保留。")

    def _add_paths(self, paths: list[Path]) -> None:
        group_key = self.queue_group_combo.currentData() or "__all_kpis__"
        group_name = self._group_name(group_key)
        existing = {(entry["path"], entry["group_key"]) for entry in self.queue_entries}
        added_count = 0
        for path in paths:
            normalized = str(path.resolve())
            if (normalized, str(group_key)) in existing:
                continue
            self.queue_entries.append({"path": normalized, "group_key": str(group_key), "group_name": group_name})
            existing.add((normalized, str(group_key)))
            added_count += 1
        if added_count:
            self._rebuild_queue_list_widget()
            self._update_queue_stats()
            self.log("info", f"已添加 {added_count} 个文件到分析队列，当前分析组: {group_name}。")

    def _update_queue_stats(self) -> None:
        analyzed_count = sum(
            1
            for entry in self.queue_entries
            if self._make_result_key(entry["path"], entry["group_key"]) in self.results_by_key
        )
        self.queue_stats_label.setText(f"当前 {len(self.queue_entries)} 个文件，已完成分析 {analyzed_count} 个")

    def _rebuild_queue_list_widget(self) -> None:
        self.file_list.blockSignals(True)
        self.file_list.clear()
        grouped: dict[str, list[dict[str, str]]] = {}
        for entry in self.queue_entries:
            grouped.setdefault(entry["group_key"], []).append(entry)
        ordered_groups = sorted(grouped.items(), key=lambda item: self._sort_text_key(self._group_name(item[0])))
        for group_key, entries in ordered_groups:
            header = QListWidgetItem(self._group_name(group_key))
            header.setData(QUEUE_HEADER_ROLE, True)
            header.setFlags(Qt.ItemFlag.ItemIsEnabled)
            header.setForeground(QColor("#0f4c81"))
            self.file_list.addItem(header)
            for entry in sorted(entries, key=lambda item: self._sort_text_key(Path(item["path"]).name)):
                item = QListWidgetItem(Path(entry["path"]).name)
                item.setToolTip(f"{entry['path']}\n分析组: {self._group_name(entry['group_key'])}")
                item.setData(QUEUE_PATH_ROLE, entry["path"])
                item.setData(QUEUE_GROUP_ROLE, entry["group_key"])
                self.file_list.addItem(item)
        self.file_list.blockSignals(False)

    def _group_name(self, group_key: str | None) -> str:
        normalized_key = str(group_key or "__all_kpis__")
        for group in self.kpi_groups:
            if str(group.get("key")) == normalized_key:
                return str(group.get("name"))
        return "默认组（全部 KPI）"

    def refresh_dbc_list(self) -> None:
        CAN_DATABASE_DIR.mkdir(parents=True, exist_ok=True)
        self.dbc_list.clear()
        for dbc_path in sorted(CAN_DATABASE_DIR.glob("*.dbc"), key=lambda item: self._sort_text_key(item.name)):
            item = QListWidgetItem(dbc_path.name)
            item.setToolTip(str(dbc_path))
            item.setData(Qt.ItemDataRole.UserRole, str(dbc_path))
            self.dbc_list.addItem(item)

    def add_dbc_files(self) -> None:
        selected, _ = QFileDialog.getOpenFileNames(self, "选择 DBC 文件", "", "DBC 文件 (*.dbc)")
        if not selected:
            return
        CAN_DATABASE_DIR.mkdir(parents=True, exist_ok=True)
        added_count = 0
        for path_text in selected:
            source = Path(path_text)
            target = CAN_DATABASE_DIR / source.name
            if source.resolve() == target.resolve():
                continue
            shutil.copy2(source, target)
            added_count += 1
        self.refresh_dbc_list()
        if added_count:
            self.log("success", f"已添加 {added_count} 个 DBC 文件。")

    def remove_selected_dbc_files(self) -> None:
        items = self.dbc_list.selectedItems()
        if not items:
            return
        removed_count = 0
        for item in items:
            dbc_path = Path(str(item.data(Qt.ItemDataRole.UserRole)))
            if dbc_path.exists():
                dbc_path.unlink()
                removed_count += 1
        self.refresh_dbc_list()
        if removed_count:
            self.log("warning", f"已删除 {removed_count} 个 DBC 文件。")

    def _populate_group_combo(self, combo: QComboBox, selected_key: str | None = None) -> None:
        combo.blockSignals(True)
        combo.clear()
        selected_index = 0
        ordered_groups = sorted(
            self.kpi_groups,
            key=lambda item: (not bool(item.get("is_builtin")), self._sort_text_key(str(item.get("name", "")))),
        )
        for index, group in enumerate(ordered_groups):
            combo.addItem(str(group.get("name")), str(group.get("key")))
            if selected_key and str(group.get("key")) == selected_key:
                selected_index = index
        if combo.count() > 0:
            combo.setCurrentIndex(selected_index)
        combo.blockSignals(False)

    def load_kpi_group_from_combo(self, *_args) -> None:
        group_key = str(self.kpi_group_editor_combo.currentData() or "__all_kpis__")
        selected_group = next((group for group in self.kpi_groups if str(group.get("key")) == group_key), None)
        if selected_group is None:
            return
        self._loading_kpi_group = True
        self.kpi_group_name_edit.setText(str(selected_group.get("name", "")))
        selected_kpis = {str(item) for item in selected_group.get("kpis", [])}
        is_builtin = bool(selected_group.get("is_builtin"))
        for row_index in range(self.kpi_group_kpi_list.count()):
            item = self.kpi_group_kpi_list.item(row_index)
            item.setCheckState(Qt.CheckState.Checked if item.data(Qt.ItemDataRole.UserRole) in selected_kpis or is_builtin else Qt.CheckState.Unchecked)
            flags = item.flags() | Qt.ItemFlag.ItemIsEnabled
            if is_builtin:
                item.setFlags(flags & ~Qt.ItemFlag.ItemIsUserCheckable)
            else:
                item.setFlags(flags | Qt.ItemFlag.ItemIsUserCheckable)
        self.kpi_group_name_edit.setReadOnly(is_builtin)
        self._loading_kpi_group = False

    def create_kpi_group(self) -> None:
        name, ok = QInputDialog.getText(self, "新增 KPI 分组", "请输入分组名称")
        if not ok or not name.strip():
            return
        save_kpi_group(name.strip(), [])
        self.reload_runtime_configs(log_message=False)
        self._set_combo_value(self.kpi_group_editor_combo, name.strip(), use_text=True)
        self.log("success", f"已创建 KPI 分组: {name.strip()}")

    def save_current_kpi_group(self) -> None:
        self._persist_current_kpi_group(log_message=True)

    def _persist_current_kpi_group(self, log_message: bool = False) -> None:
        if self._loading_kpi_group:
            return
        group_key = str(self.kpi_group_editor_combo.currentData() or "__all_kpis__")
        if group_key == "__all_kpis__":
            return
        name = self.kpi_group_name_edit.text().strip()
        if not name:
            return
        selected_kpis: list[str] = []
        for row_index in range(self.kpi_group_kpi_list.count()):
            item = self.kpi_group_kpi_list.item(row_index)
            if item.checkState() == Qt.CheckState.Checked:
                selected_kpis.append(str(item.data(Qt.ItemDataRole.UserRole)))
        save_kpi_group(name, selected_kpis, key=group_key)
        current_queue_group = str(self.queue_group_combo.currentData() or "__all_kpis__")
        self.kpi_groups = load_kpi_groups()
        self._populate_group_combo(self.queue_group_combo, current_queue_group)
        self._populate_group_combo(self.kpi_group_editor_combo, group_key)
        self._set_combo_value(self.kpi_group_editor_combo, group_key)
        if log_message:
            self.log("success", f"KPI 分组已保存: {name}")

    def on_kpi_group_item_changed(self, _item: QListWidgetItem) -> None:
        self._persist_current_kpi_group(log_message=False)

    def on_kpi_group_name_editing_finished(self) -> None:
        self._persist_current_kpi_group(log_message=False)

    def delete_current_kpi_group(self) -> None:
        group_key = str(self.kpi_group_editor_combo.currentData() or "__all_kpis__")
        if group_key == "__all_kpis__":
            QMessageBox.information(self, "禁止删除", "默认组不能删除。")
            return
        group_name = self._group_name(group_key)
        if QMessageBox.question(self, "删除 KPI 分组", f"确认删除 KPI 分组？\n{group_name}") != QMessageBox.StandardButton.Yes:
            return
        delete_kpi_group(group_key)
        self.reload_runtime_configs(log_message=False)
        self.log("warning", f"已删除 KPI 分组: {group_name}")

    def _set_combo_value(self, combo: QComboBox, value: str, use_text: bool = False) -> None:
        for index in range(combo.count()):
            candidate = combo.itemText(index) if use_text else combo.itemData(index)
            if candidate == value:
                combo.setCurrentIndex(index)
                return

    def on_file_selection_changed(self) -> None:
        return

    def analyze_selected(self) -> None:
        if not self._ensure_mapping_ready_for_analysis():
            return
        if not self._validate_runtime_definitions_before_analysis():
            return
        items = [item for item in self.file_list.selectedItems() if not bool(item.data(QUEUE_HEADER_ROLE))]
        if not items:
            QMessageBox.information(self, "未选择文件", "请先在主页中选择一个或多个文件。")
            return
        entries = [
            {"path": str(item.data(QUEUE_PATH_ROLE)), "group_key": str(item.data(QUEUE_GROUP_ROLE) or "__all_kpis__")}
            for item in items
        ]
        self._analyze_paths(entries)

    def analyze_all(self) -> None:
        if not self._ensure_mapping_ready_for_analysis():
            return
        if not self._validate_runtime_definitions_before_analysis():
            return
        if not self.queue_entries:
            QMessageBox.information(self, "无文件", "请先添加待分析文件。")
            return
        self._analyze_paths(list(self.queue_entries))

    def _selected_export_targets(self) -> list[str]:
        targets: list[str] = []
        if self.export_html_checkbox.isChecked():
            targets.append("html")
        if self.export_word_checkbox.isChecked():
            targets.append("word")
        return targets

    def _analyze_paths(self, entries: list[dict[str, str]]) -> None:
        self.clear_runtime_log()
        self.reload_runtime_configs(log_message=False)
        output_dir = Path(self.output_dir_edit.text().strip() or self.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir = output_dir
        export_targets = self._selected_export_targets()
        template_path = self.active_template_combo.currentData()
        report_title = self.report_title_edit.text().strip() or "TCS 打滑控制自动分析报告"
        analyzed_paths: list[str] = []
        analyzed_results: list[AnalysisResult] = []
        total_count = len(entries)
        self.analysis_progress_bar.setRange(0, total_count)
        self.analysis_progress_bar.setValue(0)
        self.analysis_progress_bar.setFormat("分析准备中 %v/%m")
        QApplication.processEvents()
        for index, entry in enumerate(entries, start=1):
            path = Path(entry["path"])
            try:
                group_key = str(entry.get("group_key", "__all_kpis__"))
                group_name = self._group_name(group_key)
                result_key = self._make_result_key(str(path), group_key)
                cache_key = str(path)
                self._chart_frame_cache.pop(cache_key, None)
                self._chart_sample_cache.pop(cache_key, None)
                self.analysis_progress_bar.setFormat(f"分析中 {path.name} %v/%m")
                QApplication.processEvents()
                result = self.engine.analyze_file(path, kpi_group_key=group_key)
                self.results_by_key[result_key] = result
                if result_key not in self.result_order:
                    self.result_order.append(result_key)
                analyzed_paths.append(str(path))
                analyzed_results.append(result)
                self.log("success", f"分析成功: {path.name}，分析组: {group_name}")
            except ConfigExecutionError as exc:
                self._log_runtime_execution_error(path, exc)
            except Exception as exc:  # noqa: BLE001
                self.log("error", f"分析失败: {path.name}: {exc}")
            self.analysis_progress_bar.setValue(index)
            QApplication.processEvents()
        self._update_queue_stats()
        self._refresh_result_scope_combo()
        if analyzed_paths:
            self._set_result_scope(analyzed_paths[0])
            self._warm_chart_cache_for_paths(analyzed_paths)
        if analyzed_results and "html" in export_targets:
            self._export_batch_html(analyzed_results, output_dir, template_path, report_title)
        if analyzed_results and "word" in export_targets:
            self._export_batch_word(analyzed_results, output_dir, report_title)
        if not export_targets:
            self.log("warning", "分析已完成，当前未勾选自动导出格式。")
        self.analysis_progress_bar.setFormat(f"分析完成 {self.analysis_progress_bar.value()}/{total_count}")

    def _export_batch_html(self, results: list[AnalysisResult], output_dir: Path, template_path, report_title: str) -> None:
        output = export_html(results, output_dir / batch_report_filename(report_title), template_path=template_path, report_title=report_title)
        self.log("info", f"HTML 汇总导出: {output}")

    def _export_batch_word(self, results: list[AnalysisResult], output_dir: Path, report_title: str) -> None:
        output = export_word(results, output_dir / batch_word_filename(report_title), report_title=report_title)
        self.log("info", f"Word 汇总导出: {output}")

    def export_selected_results(self) -> None:
        results = self._display_results()
        if not results:
            QMessageBox.information(self, "无结果", "请先完成分析。")
            return
        export_targets = self._selected_export_targets()
        if not export_targets:
            QMessageBox.information(self, "未选择导出格式", "请至少勾选一种导出格式。")
            return
        output_dir = Path(self.output_dir_edit.text().strip() or self.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir = output_dir
        template_path = self.active_template_combo.currentData()
        report_title = self.report_title_edit.text().strip() or "TCS 打滑控制自动分析报告"
        if "html" in export_targets:
            self._export_batch_html(results, output_dir, template_path, report_title)
        if "word" in export_targets:
            self._export_batch_word(results, output_dir, report_title)
        self.log("success", f"已导出 {len(results)} 个结果。")

    def _warm_chart_cache_for_paths(self, paths: list[str]) -> None:
        unique_paths = list(dict.fromkeys(paths))
        for path in unique_paths:
            result = self._chart_result_for_path(path)
            if result is None:
                continue
            frame = self._prepare_chart_frame(result)
            self._chart_sample_cache[path] = self._downsample_frame(frame)

    def _get_queue_order_paths(self) -> list[str]:
        return [entry["path"] for entry in self.queue_entries]

    def _get_result_order_paths(self) -> list[str]:
        return [result_key for result_key in self.result_order if result_key in self.results_by_key]

    def _get_chart_scope_paths(self) -> list[str]:
        ordered_paths: list[str] = []
        seen_paths: set[str] = set()
        for result_key in self._get_result_order_paths():
            path = str(self.results_by_key[result_key].context.source_path)
            if path in seen_paths:
                continue
            ordered_paths.append(path)
            seen_paths.add(path)
        return ordered_paths

    def _chart_result_for_path(self, path: str) -> AnalysisResult | None:
        for result_key in reversed(self._get_result_order_paths()):
            result = self.results_by_key[result_key]
            if str(result.context.source_path) == path:
                return result
        return None

    def _chart_results_for_path(self, path: str) -> list[AnalysisResult]:
        results: list[AnalysisResult] = []
        for result_key in self._get_result_order_paths():
            result = self.results_by_key[result_key]
            if str(result.context.source_path) == path:
                results.append(result)
        return results

    def _refresh_result_scope_combo(self) -> None:
        ordered_paths = self._get_chart_scope_paths()
        self.result_scope_combo.blockSignals(True)
        self.result_scope_combo.clear()
        name_counts: dict[str, int] = {}
        for path in ordered_paths:
            file_name = Path(path).name
            name_counts[file_name] = name_counts.get(file_name, 0) + 1
            suffix = f" ({name_counts[file_name]})" if name_counts[file_name] > 1 else ""
            self.result_scope_combo.addItem(f"{file_name}{suffix}", path)
        index = 0
        for candidate in range(self.result_scope_combo.count()):
            if self.result_scope_combo.itemData(candidate) == self.selected_chart_path:
                index = candidate
                break
        if ordered_paths and self.selected_chart_path not in ordered_paths:
            self.selected_chart_path = ordered_paths[0]
            index = 0
        if not ordered_paths:
            self.selected_chart_path = None
        self.result_scope_combo.setCurrentIndex(index)
        self.result_scope_combo.blockSignals(False)

    def _set_result_scope(self, path: str) -> None:
        self.selected_chart_path = path
        for index in range(self.result_scope_combo.count()):
            if self.result_scope_combo.itemData(index) == path:
                self.result_scope_combo.setCurrentIndex(index)
                break
        self.refresh_result_views()

    def on_result_scope_changed(self, *_args) -> None:
        key = self.result_scope_combo.currentData()
        if key is None:
            return
        self.selected_chart_path = str(key)
        self.refresh_result_views()

    def select_previous_result(self) -> None:
        if self.result_scope_combo.count() <= 1:
            return
        next_index = self.result_scope_combo.currentIndex() - 1
        if next_index < 0:
            next_index = self.result_scope_combo.count() - 1
        self.result_scope_combo.setCurrentIndex(next_index)

    def select_next_result(self) -> None:
        if self.result_scope_combo.count() <= 1:
            return
        self.result_scope_combo.setCurrentIndex((self.result_scope_combo.currentIndex() + 1) % self.result_scope_combo.count())

    def _display_results(self) -> list[AnalysisResult]:
        return [self.results_by_key[result_key] for result_key in self._get_result_order_paths()]

    def _chart_result(self) -> AnalysisResult | None:
        if self.selected_chart_path is not None:
            return self._chart_result_for_path(self.selected_chart_path)
        ordered_paths = self._get_chart_scope_paths()
        if not ordered_paths:
            return None
        return self._chart_result_for_path(ordered_paths[0])

    def refresh_result_views(self) -> None:
        results = self._display_results()
        if not results:
            self.rule_table.clearSpans()
            self.rule_table.setRowCount(0)
            self.refresh_chart_panels()
            return
        self.refresh_rule_table(results)
        self.refresh_chart_panels()

    def refresh_rule_table(self, results: list[AnalysisResult] | None = None) -> None:
        display_results = self._display_results() if results is None else results
        selected_status = str(self.rule_status_filter.currentData() or "all")
        self.rule_table.clearSpans()
        self.rule_table.setRowCount(0)
        grouped_results: dict[str, list[AnalysisResult]] = {}
        for result in display_results:
            group_key = str(result.context.metadata.get("kpi_group_key", "__all_kpis__"))
            grouped_results.setdefault(group_key, []).append(result)
        ordered_groups = sorted(grouped_results.items(), key=lambda item: self._sort_text_key(self._group_name(item[0])))
        for group_index, (group_key, group_results) in enumerate(ordered_groups):
            group_row = self.rule_table.rowCount()
            self.rule_table.insertRow(group_row)
            group_item = QTableWidgetItem(self._group_name(group_key))
            group_item.setData(RESULT_ROW_KIND_ROLE, "group")
            group_item.setBackground(QColor("#e0f2fe"))
            group_item.setForeground(QColor("#0c4a6e"))
            self.rule_table.setItem(group_row, 0, group_item)
            self.rule_table.setSpan(group_row, 0, 1, self.rule_table.columnCount())
            self.rule_table.setRowHeight(group_row, 30)
            ordered_results = sorted(group_results, key=lambda item: self._sort_text_key(item.context.source_path.name))
            for result_index, result in enumerate(ordered_results):
                rows = [item for item in result.kpis if selected_status == "all" or item.status == selected_status]
                file_row = self.rule_table.rowCount()
                self.rule_table.insertRow(file_row)
                file_item = QTableWidgetItem(result.context.source_path.name)
                file_item.setData(RESULT_ROW_KIND_ROLE, "file")
                file_item.setData(RESULT_ROW_PATH_ROLE, str(result.context.source_path))
                file_item.setBackground(QColor("#f8fafc"))
                file_item.setForeground(QColor("#334155"))
                file_item.setToolTip(f"双击跳转曲线页并选中该文件\n{result.context.source_path}")
                self.rule_table.setItem(file_row, 0, file_item)
                self.rule_table.setSpan(file_row, 0, 1, self.rule_table.columnCount())
                self.rule_table.setRowHeight(file_row, 28)
                for item in rows:
                    row_index = self.rule_table.rowCount()
                    self.rule_table.insertRow(row_index)
                    values = [item.title, item.description, item.unit, f"{item.value:.4f}", item.rule_description, item.result_label]
                    for column_index, value in enumerate(values):
                        table_item = QTableWidgetItem(value)
                        table_item.setData(RESULT_ROW_KIND_ROLE, "kpi")
                        if column_index == 0:
                            table_item.setData(Qt.ItemDataRole.UserRole, item.name)
                        if column_index == 5:
                            self._style_status_item(table_item, item.status)
                        self.rule_table.setItem(row_index, column_index, table_item)
                if result_index < len(ordered_results) - 1:
                    spacer_row = self.rule_table.rowCount()
                    self.rule_table.insertRow(spacer_row)
                    self.rule_table.setRowHeight(spacer_row, 6)
            if group_index < len(ordered_groups) - 1:
                spacer_row = self.rule_table.rowCount()
                self.rule_table.insertRow(spacer_row)
                self.rule_table.setRowHeight(spacer_row, 14)

    def _style_status_item(self, item: QTableWidgetItem, status: str) -> None:
        palette = {"pass": QColor("#166534"), "warning": QColor("#b45309"), "fail": QColor("#b91c1c")}
        item.setForeground(palette.get(status, QColor("#1f2937")))
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        if status == "pass":
            item.setBackground(QColor("#ecfdf5"))
        elif status == "fail":
            item.setBackground(QColor("#fff1f2"))

    def filter_signal_browser(self, text: str) -> None:
        keyword = text.strip().lower()
        self.interface_signal_browser.clear()
        self.kpi_signal_browser.clear()
        self.derived_signal_browser.clear()
        self.custom_signal_browser.clear()
        for signal_name in sorted(self._interface_signal_names, key=str.lower):
            if keyword and keyword not in signal_name.lower():
                continue
            item = QListWidgetItem(signal_name)
            self.interface_signal_browser.addItem(item)
        for signal_name in sorted(self._kpi_signal_names, key=str.lower):
            if keyword and keyword not in signal_name.lower():
                continue
            item = QListWidgetItem(signal_name)
            self.kpi_signal_browser.addItem(item)
        for signal_name in sorted(self._derived_signal_names, key=str.lower):
            if keyword and keyword not in signal_name.lower():
                continue
            item = QListWidgetItem(signal_name)
            self.derived_signal_browser.addItem(item)
        formula_lookup = {item["name"]: item["expression"] for item in load_formula_signal_definitions()}
        for signal_name in sorted(self._formula_signal_names, key=str.lower):
            expression = formula_lookup.get(signal_name, "")
            if keyword and keyword not in signal_name.lower() and keyword not in expression.lower():
                continue
            item = QListWidgetItem(signal_name)
            item.setToolTip(expression)
            self.custom_signal_browser.addItem(item)

    def toggle_signal_library(self, visible: bool) -> None:
        if visible:
            popup_point = self.signal_library_button.mapToGlobal(QPoint(0, self.signal_library_button.height() + 6))
            self.signal_library_popup.setGeometry(popup_point.x(), popup_point.y(), 780, 560)
            self.signal_library_popup.show()
            self.signal_search_edit.setFocus()
            return
        self.signal_library_popup.hide()

    def on_zoom_mode_button_toggled(self, checked: bool) -> None:
        sender = self.sender()
        if sender is self.zoom_x_mode_button and checked:
            self.zoom_y_mode_button.blockSignals(True)
            self.zoom_y_mode_button.setChecked(False)
            self.zoom_y_mode_button.blockSignals(False)
        if sender is self.zoom_y_mode_button and checked:
            self.zoom_x_mode_button.blockSignals(True)
            self.zoom_x_mode_button.setChecked(False)
            self.zoom_x_mode_button.blockSignals(False)
        self.apply_zoom_mode_to_all_panels()

    def cycle_cursor_mode(self) -> None:
        previous_mode = self.cursor_mode
        self.cursor_mode = (self.cursor_mode + 1) % 3
        if self.cursor_mode == 0:
            self.cursor_positions = [None, None]
            mode_text = "无光标"
        elif self.cursor_mode == 1:
            if previous_mode == 0:
                self.cursor_positions = [None, None]
            else:
                self.cursor_positions[1] = None
            mode_text = "单光标"
        else:
            if previous_mode == 0:
                self.cursor_positions = [None, None]
            mode_text = "双光标"
        self._next_cursor_slot = 0
        self.cursor_mode_button.setToolTip(f"当前: {mode_text}，Ctrl+W 切换")
        self.log("info", f"光标模式已切换为: {mode_text}")
        self._ensure_default_cursor_positions()
        self.refresh_cursor_displays()

    def _current_visible_x_range(self) -> tuple[float, float] | None:
        if self.chart_panels:
            x_range, _y_range = self.chart_panels[0]["frame"].view.current_axis_ranges()
            if x_range is not None:
                return x_range
        return self._shared_chart_x_range

    def _ensure_default_cursor_positions(self) -> None:
        if self.cursor_mode == 0:
            return
        result = self._chart_result()
        if result is None or result.normalized_frame.empty or "time_s" not in result.normalized_frame.columns:
            return
        visible_range = self._current_visible_x_range()
        if visible_range is not None:
            min_x, max_x = visible_range
        else:
            min_x = float(result.normalized_frame["time_s"].min())
            max_x = float(result.normalized_frame["time_s"].max())
        if max_x <= min_x:
            max_x = min_x + 1e-6
        if self.cursor_mode == 1 and self.cursor_positions[0] is None:
            self.cursor_positions[0] = (min_x + max_x) / 2.0
            self.cursor_positions[1] = None
        if self.cursor_mode == 2 and (self.cursor_positions[0] is None or self.cursor_positions[1] is None):
            span = max_x - min_x
            if self.cursor_positions[0] is None:
                self.cursor_positions[0] = min_x + span / 3.0
            if self.cursor_positions[1] is None:
                self.cursor_positions[1] = min(max_x, float(self.cursor_positions[0]) + span / 3.0)

    def _snap_cursor_x(self, cursor_x: float) -> float:
        result = self._chart_result()
        if result is None or result.normalized_frame.empty or "time_s" not in result.normalized_frame.columns:
            return cursor_x
        time_series = result.normalized_frame["time_s"].dropna()
        if time_series.empty:
            return cursor_x
        nearest_index = (time_series - cursor_x).abs().idxmin()
        return float(time_series.loc[nearest_index])

    def _clamp_cursor_x(self, cursor_x: float) -> float:
        result = self._chart_result()
        if result is None or result.normalized_frame.empty or "time_s" not in result.normalized_frame.columns:
            return cursor_x
        min_x = float(result.normalized_frame["time_s"].min())
        max_x = float(result.normalized_frame["time_s"].max())
        return max(min_x, min(max_x, cursor_x))

    def _downsample_frame(self, frame, max_points: int = 1000):
        if frame.empty or len(frame) <= max_points:
            return frame
        step = max(1, math.ceil(len(frame) / max_points))
        return frame.iloc[::step].copy()

    def _sampled_chart_frame(self, result: AnalysisResult, frame):  # noqa: ANN001
        cache_key = str(result.context.source_path)
        cached = self._chart_sample_cache.get(cache_key)
        if cached is not None:
            return cached
        sampled = self._downsample_frame(frame)
        self._chart_sample_cache[cache_key] = sampled
        return sampled

    def _nearest_signal_value(self, frame, signal_name: str, cursor_x: float | None) -> str:
        if cursor_x is None or frame.empty or signal_name not in frame.columns or "time_s" not in frame.columns:
            return "-"
        series = frame[["time_s", signal_name]].dropna()
        if series.empty:
            return "-"
        nearest_index = (series["time_s"] - cursor_x).abs().idxmin()
        value = series.loc[nearest_index, signal_name]
        try:
            return f"{float(value):.4f}"
        except (TypeError, ValueError):
            return str(value)

    def _signal_color(self, signal_name: str) -> QColor:
        color = self._signal_color_map.get(signal_name)
        if color is None:
            palette_index = len(self._signal_color_map) % len(self._chart_colors)
            color = QColor(self._chart_colors[palette_index])
            self._signal_color_map[signal_name] = color
        return QColor(color)

    def choose_signal_color(self, signal_name: str) -> None:
        selected = QColorDialog.getColor(self._signal_color(signal_name), self, f"设置颜色: {signal_name}")
        if not selected.isValid():
            return
        self._signal_color_map[signal_name] = QColor(selected)
        self.refresh_chart_panels()

    def sync_x_range_across_panels(self, x_range: tuple[float, float], source_view: InteractiveChartView | None = None) -> None:
        result = self._chart_result()
        if result is None or result.normalized_frame.empty or "time_s" not in result.normalized_frame.columns:
            return
        self._shared_chart_x_range = x_range
        self._active_chart_sheet()["x_range"] = x_range
        bounds = (float(result.normalized_frame["time_s"].min()), float(result.normalized_frame["time_s"].max()))
        for panel in self.chart_panels:
            frame: ChartPanelFrame = panel["frame"]
            frame.view.set_x_range(x_range, bounds)

    def _apply_shared_x_range(self) -> None:
        if self._shared_chart_x_range is None:
            return
        result = self._chart_result()
        if result is None or result.normalized_frame.empty or "time_s" not in result.normalized_frame.columns:
            return
        bounds = (float(result.normalized_frame["time_s"].min()), float(result.normalized_frame["time_s"].max()))
        for panel in self.chart_panels:
            frame: ChartPanelFrame = panel["frame"]
            frame.view.set_x_range(self._shared_chart_x_range, bounds)

    def _build_signal_chart(self, frame, signal_names: list[str], colors: list[QColor], show_x_axis: bool) -> tuple[QChart, tuple[float, float] | None, tuple[float, float] | None]:
        chart = QChart()
        chart.setBackgroundVisible(False)
        chart.setMargins(QMargins(0, 0, 0, 0))
        chart.setPlotAreaBackgroundVisible(False)
        chart.setBackgroundRoundness(0)
        if frame.empty or "time_s" not in frame.columns or not signal_names:
            return chart, None, None
        y_values: list[float] = []
        for index, signal_name in enumerate(signal_names):
            if signal_name not in frame.columns:
                continue
            series = QLineSeries()
            series.setName(signal_name)
            series.setColor(self._signal_color(signal_name))
            has_values = False
            for time_value, y_value in zip(frame["time_s"], frame[signal_name]):
                try:
                    x = float(time_value)
                    y = float(y_value)
                except (TypeError, ValueError):
                    continue
                series.append(x, y)
                y_values.append(y)
                has_values = True
            if has_values:
                chart.addSeries(series)
        if not chart.series() or not y_values:
            return chart, None, None
        min_x = float(frame["time_s"].min())
        max_x = float(frame["time_s"].max())
        x_bounds = (min_x, max_x if max_x > min_x else min_x + 1e-6)
        y_min = min(y_values)
        y_max = max(y_values)
        if y_max > y_min:
            padding = max((y_max - y_min) * 0.08, 1e-6)
            y_bounds = (y_min - padding, y_max + padding)
        else:
            padding = max(abs(y_min) * 0.15, 1.0)
            y_bounds = (y_min - padding, y_min + padding)
        axis_x = QValueAxis()
        axis_x.setTitleText("")
        axis_x.setLabelsColor(QColor("#627588"))
        axis_x.setGridLineColor(QColor("#eff4f8"))
        axis_x.setRange(*x_bounds)
        axis_x.setLabelsVisible(show_x_axis)
        axis_x.setMinorGridLineVisible(False)
        axis_x.setLineVisible(False)
        axis_y = QValueAxis()
        axis_y.setTitleText("")
        axis_y.setLabelsColor(QColor("#627588"))
        axis_y.setGridLineColor(QColor("#f3f6f9"))
        axis_y.setRange(*y_bounds)
        axis_y.setMinorGridLineVisible(False)
        axis_y.setLineVisible(False)
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        for series in chart.series():
            series.attachAxis(axis_x)
            series.attachAxis(axis_y)
        chart.legend().setVisible(False)
        return chart, x_bounds, y_bounds

    def _default_chart_sheet_name(self, index: int | None = None) -> str:
        sheet_index = (index if index is not None else len(self.chart_sheets)) + 1
        return f"工作表 {sheet_index}"

    def _new_chart_panel_state(self, default_signals: list[str] | None = None) -> dict[str, object]:
        panel_id = self._next_chart_panel_id
        self._next_chart_panel_id += 1
        return {"panel_id": panel_id, "signals": list(default_signals or [])}

    def _load_chart_sheets_from_view_state(self) -> None:
        sheets: list[dict[str, object]] = []
        for index, sheet_state in enumerate(self._chart_view_state.get("sheets", []), start=1):
            if not isinstance(sheet_state, dict):
                continue
            panels: list[dict[str, object]] = []
            for panel_state in sheet_state.get("panels", []):
                if not isinstance(panel_state, dict):
                    continue
                signals = [str(signal).strip() for signal in panel_state.get("signals", []) if str(signal).strip()]
                panels.append(self._new_chart_panel_state(signals))
            sheets.append({
                "name": str(sheet_state.get("name", "")).strip() or self._default_chart_sheet_name(index - 1),
                "panels": panels,
                "x_range": None,
                "signal_table_width": int(sheet_state.get("signal_table_width", 220) or 220),
            })
        if not sheets:
            sheets = [{"name": self._default_chart_sheet_name(0), "panels": [], "x_range": None, "signal_table_width": 220}]
        active_sheet = self._chart_view_state.get("active_sheet", 0)
        if not isinstance(active_sheet, int):
            active_sheet = 0
        active_sheet = max(0, min(active_sheet, len(sheets) - 1))
        self.chart_sheets = sheets
        self.active_chart_sheet_index = active_sheet
        self.chart_panels = self.chart_sheets[active_sheet]["panels"]
        self._shared_chart_x_range = self.chart_sheets[active_sheet].get("x_range")

    def _active_chart_sheet(self) -> dict[str, object]:
        if not self.chart_sheets:
            self.chart_sheets = [{"name": self._default_chart_sheet_name(0), "panels": [], "x_range": None, "signal_table_width": 220}]
            self.active_chart_sheet_index = 0
        return self.chart_sheets[self.active_chart_sheet_index]

    def _signal_table_width_for_active_sheet(self) -> int:
        return int(self._active_chart_sheet().get("signal_table_width", 220) or 220)

    def _store_active_chart_sheet_state(self) -> None:
        if not self.chart_sheets:
            return
        self.chart_sheets[self.active_chart_sheet_index]["x_range"] = self._shared_chart_x_range

    def _refresh_chart_sheet_tabs(self) -> None:
        if not hasattr(self, "chart_sheet_tabs"):
            return
        self.chart_sheet_tabs.blockSignals(True)
        self.chart_sheet_tabs.clear()
        for sheet in self.chart_sheets:
            self.chart_sheet_tabs.addTab(QWidget(), str(sheet.get("name", self._default_chart_sheet_name())))
        self.chart_sheet_tabs.setCurrentIndex(self.active_chart_sheet_index)
        self.chart_sheet_tabs.blockSignals(False)

    def _create_chart_panel_frame(self, panel_state: dict[str, object]) -> ChartPanelFrame:
        frame = ChartPanelFrame(
            int(panel_state.get("panel_id", -1)),
            drop_callback=lambda signal_names, source_panel_id=None, target=panel_state: self.add_signals_to_panel(target, signal_names, source_panel_id),
            remove_callback=lambda target=panel_state: self.remove_chart_panel(target),
            cursor_move_callback=self.update_cursor_position,
            signal_remove_callback=lambda signal_name, target=panel_state: self.remove_signal_from_panel(target, signal_name),
            signal_color_callback=self.choose_signal_color,
            width_sync_callback=self.sync_signal_table_width_across_panels,
            initial_signal_table_width=self._signal_table_width_for_active_sheet(),
        )
        frame.view._x_range_sync_callback = self.sync_x_range_across_panels
        return frame

    def sync_signal_table_width_across_panels(self, source_panel_id: int, width: int) -> None:
        if self._signal_table_width_sync_in_progress:
            return
        self._signal_table_width_sync_in_progress = True
        try:
            self._active_chart_sheet()["signal_table_width"] = int(width)
            for panel in self.chart_panels:
                frame: ChartPanelFrame = panel.get("frame")
                if frame is None:
                    continue
                if source_panel_id >= 0 and int(panel.get("panel_id", -1)) == int(source_panel_id):
                    continue
                frame.set_signal_table_width(width)
        finally:
            self._signal_table_width_sync_in_progress = False

    def _auto_adjust_signal_table_width(self) -> None:
        if not self.chart_panels or self._signal_table_width_sync_in_progress:
            return
        desired_width = self._signal_table_width_for_active_sheet()
        for panel in self.chart_panels:
            frame: ChartPanelFrame = panel.get("frame")
            if frame is None:
                continue
            desired_width = max(desired_width, frame.signal_table.desired_table_width())
        self.sync_signal_table_width_across_panels(-1, desired_width)

    def _rebuild_chart_splitter_widgets(self) -> None:
        while self.chart_splitter.count():
            widget = self.chart_splitter.widget(0)
            if widget is None:
                break
            widget.setParent(None)
            widget.deleteLater()
        for sheet in self.chart_sheets:
            for panel in sheet.get("panels", []):
                if isinstance(panel, dict):
                    panel.pop("frame", None)
        for panel_state in self.chart_panels:
            frame = self._create_chart_panel_frame(panel_state)
            panel_state["frame"] = frame
            self.chart_splitter.addWidget(frame)
        self._rebalance_chart_splitter()

    def _switch_chart_sheet(self, index: int, *, refresh: bool = True) -> None:
        if not self.chart_sheets:
            return
        self._store_active_chart_sheet_state()
        index = max(0, min(index, len(self.chart_sheets) - 1))
        self.active_chart_sheet_index = index
        active_sheet = self._active_chart_sheet()
        self.chart_panels = active_sheet["panels"]
        self._shared_chart_x_range = active_sheet.get("x_range")
        self._rebuild_chart_splitter_widgets()
        self.apply_zoom_mode_to_all_panels()
        if refresh:
            self.refresh_chart_panels()

    def on_chart_sheet_changed(self, index: int) -> None:
        if index < 0:
            return
        self._switch_chart_sheet(index)
        self._persist_chart_view_state()

    def on_chart_sheet_tab_double_clicked(self, index: int) -> None:
        if index >= 0:
            self.chart_sheet_tabs.setCurrentIndex(index)
            self.rename_current_chart_sheet()

    def add_chart_sheet(self) -> None:
        sheet_name, ok = QInputDialog.getText(self, "新增工作表", "请输入工作表名称", text=self._default_chart_sheet_name())
        if not ok:
            return
        normalized_name = sheet_name.strip() or self._default_chart_sheet_name()
        self._store_active_chart_sheet_state()
        self.chart_sheets.append({"name": normalized_name, "panels": [self._new_chart_panel_state()], "x_range": None})
        self.chart_sheets[-1]["signal_table_width"] = 220
        self.active_chart_sheet_index = len(self.chart_sheets) - 1
        self.chart_panels = self.chart_sheets[self.active_chart_sheet_index]["panels"]
        self._refresh_chart_sheet_tabs()
        self._switch_chart_sheet(self.active_chart_sheet_index)
        self._persist_chart_view_state()

    def rename_current_chart_sheet(self) -> None:
        if not self.chart_sheets:
            return
        current_sheet = self._active_chart_sheet()
        sheet_name, ok = QInputDialog.getText(
            self,
            "重命名工作表",
            "请输入新的工作表名称",
            text=str(current_sheet.get("name", self._default_chart_sheet_name(self.active_chart_sheet_index))),
        )
        if not ok:
            return
        current_sheet["name"] = sheet_name.strip() or self._default_chart_sheet_name(self.active_chart_sheet_index)
        self._refresh_chart_sheet_tabs()
        self._persist_chart_view_state()

    def remove_current_chart_sheet(self) -> None:
        if len(self.chart_sheets) <= 1:
            QMessageBox.information(self, "无法删除", "至少保留一个工作表。")
            return
        self.chart_sheets.pop(self.active_chart_sheet_index)
        self.active_chart_sheet_index = max(0, min(self.active_chart_sheet_index, len(self.chart_sheets) - 1))
        self.chart_panels = self.chart_sheets[self.active_chart_sheet_index]["panels"]
        self._refresh_chart_sheet_tabs()
        self._switch_chart_sheet(self.active_chart_sheet_index)
        self._persist_chart_view_state()

    def add_chart_panel(self, default_signals: list[str] | None = None) -> None:
        panel_state = self._new_chart_panel_state(default_signals)
        frame = self._create_chart_panel_frame(panel_state)
        panel_state["frame"] = frame
        self.chart_panels.append(panel_state)
        self.chart_splitter.addWidget(frame)
        self.apply_zoom_mode_to_all_panels()
        self._rebalance_chart_splitter()
        self._persist_chart_view_state()
        self.refresh_chart_panels()

    def remove_chart_panel(self, panel_state: dict[str, object]) -> None:
        if len(self.chart_panels) <= 1:
            QMessageBox.information(self, "无法删除", "至少保留一个显示框。")
            return
        self.chart_panels.remove(panel_state)
        frame: ChartPanelFrame = panel_state["frame"]
        frame.setParent(None)
        frame.deleteLater()
        self._rebalance_chart_splitter()
        self._persist_chart_view_state()
        self.refresh_chart_panels()

    def add_signals_to_panel(self, panel_state: dict[str, object], signal_names: list[str], source_panel_id: int | None = None) -> None:
        valid_signal_names = [signal_name for signal_name in signal_names if signal_name in self.plot_signal_names]
        if not valid_signal_names:
            return
        signals: list[str] = panel_state["signals"]
        for signal_name in valid_signal_names:
            if signal_name not in signals:
                signals.append(signal_name)
        if source_panel_id is not None:
            source_panel = self._find_chart_panel_state(source_panel_id)
            if source_panel is not None and source_panel is not panel_state:
                source_signals: list[str] = source_panel["signals"]
                source_panel["signals"] = [signal_name for signal_name in source_signals if signal_name not in valid_signal_names]
        self._persist_chart_view_state()
        self.refresh_chart_panels()

    def _find_chart_panel_state(self, panel_id: int) -> dict[str, object] | None:
        for panel in self.chart_panels:
            if int(panel.get("panel_id", -1)) == panel_id:
                return panel
        return None

    def remove_signal_from_panel(self, panel_state: dict[str, object], signal_name: str) -> None:
        signals: list[str] = panel_state["signals"]
        if signal_name in signals:
            signals.remove(signal_name)
        self._persist_chart_view_state()
        self.refresh_chart_panels()

    def _persist_chart_view_state(self) -> None:
        self._store_active_chart_sheet_state()
        payload = {
            "active_sheet": self.active_chart_sheet_index,
            "sheets": [
                {
                    "name": str(sheet.get("name", self._default_chart_sheet_name(index))).strip() or self._default_chart_sheet_name(index),
                    "signal_table_width": int(sheet.get("signal_table_width", 220) or 220),
                    "panels": [
                        {"signals": [str(signal) for signal in panel.get("signals", []) if str(signal).strip()]}
                        for panel in sheet.get("panels", [])
                        if isinstance(panel, dict)
                    ],
                }
                for index, sheet in enumerate(self.chart_sheets)
            ],
        }
        save_chart_view_state(payload)
        self._chart_view_state = payload

    def update_cursor_position(self, cursor_index: int, cursor_x: float) -> None:
        if self.cursor_mode == 0:
            return
        cursor_x = self._snap_cursor_x(self._clamp_cursor_x(cursor_x))
        if cursor_index == 0:
            self.cursor_positions[0] = cursor_x
        elif cursor_index == 1 and self.cursor_mode >= 2:
            self.cursor_positions[1] = cursor_x
        self.refresh_cursor_displays()

    def _cursor_summary_text(self, frame_data) -> str:  # noqa: ANN001
        if self.cursor_mode == 0:
            return "光标未启用"
        if self.cursor_mode == 1 and self.cursor_positions[0] is not None:
            return f"光标1: t={self.cursor_positions[0]:.4f}s"
        if self.cursor_mode == 2 and self.cursor_positions[0] is not None and self.cursor_positions[1] is not None:
            delta = abs(float(self.cursor_positions[1]) - float(self.cursor_positions[0]))
            return f"光标1: {self.cursor_positions[0]:.4f}s    光标2: {self.cursor_positions[1]:.4f}s    Δt: {delta:.4f}s"
        return "等待放置光标"

    def apply_zoom_mode_to_all_panels(self) -> None:
        if self.zoom_x_mode_button.isChecked():
            zoom_mode = "x"
        elif self.zoom_y_mode_button.isChecked():
            zoom_mode = "y"
        else:
            zoom_mode = "both"
        self._style_zoom_mode_buttons(zoom_mode)
        for panel in self.chart_panels:
            frame: ChartPanelFrame = panel["frame"]
            frame.view.zoom_mode = zoom_mode

    def _style_zoom_mode_buttons(self, zoom_mode: str) -> None:
        active_style = "background: #dbeafe; border-color: #60a5fa; color: #0f4c81;"
        normal_style = ""
        self.zoom_x_mode_button.setStyleSheet(active_style if zoom_mode == "x" else normal_style)
        self.zoom_y_mode_button.setStyleSheet(active_style if zoom_mode == "y" else normal_style)

    def fit_all_charts(self) -> None:
        for panel in self.chart_panels:
            panel["frame"].view.fit_all()
        if self.chart_panels:
            view = self.chart_panels[0]["frame"].view
            x_range, _y_range = view.current_axis_ranges()
            if x_range is not None:
                self._shared_chart_x_range = x_range
                self._active_chart_sheet()["x_range"] = x_range
                self._apply_shared_x_range()

    def fit_x_charts(self) -> None:
        for panel in self.chart_panels:
            panel["frame"].view.fit_x()
        if self.chart_panels:
            view = self.chart_panels[0]["frame"].view
            x_range, _y_range = view.current_axis_ranges()
            if x_range is not None:
                self._shared_chart_x_range = x_range
                self._active_chart_sheet()["x_range"] = x_range
                self._apply_shared_x_range()

    def fit_y_charts(self) -> None:
        result = self._chart_result()
        if result is None:
            return
        frame_data = self._prepare_chart_frame(result)
        visible_x_range = self._current_visible_x_range()
        for panel in self.chart_panels:
            y_range = self._visible_y_range_for_panel(frame_data, panel.get("signals", []), visible_x_range)
            if y_range is not None:
                panel["frame"].view.set_y_range(y_range, panel["frame"].view._y_bounds)
            else:
                panel["frame"].view.fit_y()

    def _rebalance_chart_splitter(self) -> None:
        if self.chart_panels:
            self.chart_splitter.setSizes([1600 // len(self.chart_panels)] * len(self.chart_panels))

    def _visible_y_range_for_panel(self, frame_data, signal_names: list[str], visible_x_range: tuple[float, float] | None) -> tuple[float, float] | None:  # noqa: ANN001
        if frame_data.empty or "time_s" not in frame_data.columns or not signal_names:
            return None
        visible_frame = frame_data
        if visible_x_range is not None:
            lower, upper = visible_x_range
            visible_frame = frame_data[(frame_data["time_s"] >= lower) & (frame_data["time_s"] <= upper)]
            if visible_frame.empty:
                visible_frame = frame_data
        y_values: list[float] = []
        for signal_name in signal_names:
            if signal_name not in visible_frame.columns:
                continue
            values = pd.to_numeric(visible_frame[signal_name], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
            if not values.empty:
                y_values.extend(float(value) for value in values)
        if not y_values:
            return None
        lower = min(y_values)
        upper = max(y_values)
        if upper > lower:
            padding = max((upper - lower) * 0.08, 1e-6)
            return lower - padding, upper + padding
        padding = max(abs(lower) * 0.15, 1.0)
        return lower - padding, upper + padding

    def refresh_cursor_displays(self) -> None:
        result = self._chart_result()
        if result is None:
            self.chart_status_label.setText("光标未启用")
            for panel in self.chart_panels:
                frame: ChartPanelFrame = panel["frame"]
                frame.signal_table.set_cursor_column_visibility(0)
                frame.view.set_cursor_state(0, [None, None])
            return
        frame_data = self._prepare_chart_frame(result)
        self.chart_status_label.setText(self._cursor_summary_text(frame_data))
        for panel in self.chart_panels:
            frame: ChartPanelFrame = panel["frame"]
            signals: list[str] = panel["signals"]
            frame.view.set_cursor_state(self.cursor_mode, self.cursor_positions)
            frame.signal_table.set_cursor_column_visibility(self.cursor_mode)
            frame.signal_table.setRowCount(len(signals))
            for row_index, signal_name in enumerate(signals):
                signal_item = frame.signal_table.item(row_index, 0)
                if signal_item is None or signal_item.text() != signal_name:
                    signal_item = QTableWidgetItem(signal_name)
                    signal_item.setForeground(self._signal_color(signal_name))
                    frame.signal_table.setItem(row_index, 0, signal_item)
                frame.signal_table.setItem(row_index, 1, QTableWidgetItem(self._nearest_signal_value(frame_data, signal_name, self.cursor_positions[0] if self.cursor_mode >= 1 else None)))
                frame.signal_table.setItem(row_index, 2, QTableWidgetItem(self._nearest_signal_value(frame_data, signal_name, self.cursor_positions[1] if self.cursor_mode >= 2 else None)))
        self._auto_adjust_signal_table_width()

    def refresh_chart_panels(self) -> None:
        result = self._chart_result()
        if result is None:
            self.chart_status_label.setText("光标未启用")
            self._shared_chart_x_range = None
            self._chart_frame_cache.clear()
            self._chart_sample_cache.clear()
            self._chart_sample_cache.clear()
            for panel in self.chart_panels:
                frame: ChartPanelFrame = panel["frame"]
                frame.view.setChart(QChart())
                frame.view.set_data_bounds(None, None)
                frame.view.set_cursor_state(0, [None, None])
                frame.signal_table.set_cursor_column_visibility(0)
                frame.signal_table.setRowCount(0)
            return
        self._ensure_default_cursor_positions()
        frame_data = self._prepare_chart_frame(result)
        sampled_frame = self._sampled_chart_frame(result, frame_data)
        self._signal_browser_all = sorted({*self.plot_signal_names, *[str(column) for column in frame_data.columns]})
        self.filter_signal_browser(self.signal_search_edit.text())
        reference_x_range = self._shared_chart_x_range
        if reference_x_range is None and self.chart_panels:
            reference_x_range = self.chart_panels[0]["frame"].view.current_axis_ranges()[0]
        for panel_index, panel in enumerate(self.chart_panels):
            frame: ChartPanelFrame = panel["frame"]
            signals: list[str] = panel["signals"]
            previous_x_range, previous_y_range = frame.view.current_axis_ranges()
            chart, x_bounds, y_bounds = self._build_signal_chart(sampled_frame, signals, self._chart_colors[panel_index:] + self._chart_colors[:panel_index], show_x_axis=panel_index == len(self.chart_panels) - 1)
            frame.view.setChart(chart)
            frame.view.set_data_bounds(x_bounds, y_bounds)
            frame.view.set_cursor_state(self.cursor_mode, self.cursor_positions)
            frame.signal_table.set_cursor_column_visibility(self.cursor_mode)
            frame.view.restore_axis_ranges(reference_x_range or previous_x_range, previous_y_range, x_bounds, y_bounds)
            if panel_index == 0:
                self._shared_chart_x_range = frame.view.current_axis_ranges()[0]
            frame.signal_table.setRowCount(len(signals))
            for row_index, signal_name in enumerate(signals):
                color = self._signal_color(signal_name)
                signal_item = QTableWidgetItem(signal_name)
                signal_item.setForeground(color)
                frame.signal_table.setItem(row_index, 0, signal_item)
                frame.signal_table.setItem(row_index, 1, QTableWidgetItem(self._nearest_signal_value(frame_data, signal_name, self.cursor_positions[0] if self.cursor_mode >= 1 else None)))
                frame.signal_table.setItem(row_index, 2, QTableWidgetItem(self._nearest_signal_value(frame_data, signal_name, self.cursor_positions[1] if self.cursor_mode >= 2 else None)))
            self._apply_shared_x_range()
        self._auto_adjust_signal_table_width()
        self.chart_status_label.setText(self._cursor_summary_text(frame_data))

    def open_output_dir(self) -> None:
        output_dir = Path(self.output_dir_edit.text().strip() or self.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(output_dir)))

    def reload_runtime_configs(self, log_message: bool = True, preserve_editors: set[str] | None = None) -> None:
        preserved = preserve_editors or set()
        self._chart_view_state = load_chart_view_state()
        self._load_chart_sheets_from_view_state()
        current_derived = str(self.derived_signal_editor_path) if self.derived_signal_editor_path else None
        current_kpi = str(self.kpi_editor_path) if self.kpi_editor_path else None
        current_template = str(self.template_editor_path) if self.template_editor_path else None
        current_group = str(self.kpi_group_editor_combo.currentData()) if hasattr(self, "kpi_group_editor_combo") and self.kpi_group_editor_combo.count() else "__all_kpis__"
        current_queue_group = str(self.queue_group_combo.currentData()) if hasattr(self, "queue_group_combo") and self.queue_group_combo.count() else "__all_kpis__"
        self.derived_signal_entries = list_derived_signal_spec_entries()
        self.kpi_spec_entries = list_kpi_spec_entries()
        self.kpi_groups = load_kpi_groups()
        self.template_entries = list_report_template_entries()
        self.engine = AnalysisEngine(settings=load_analysis_settings(), runtime_logger=self._emit_runtime_log)
        self._chart_frame_cache.clear()
        self._chart_sample_cache.clear()
        derived_signals = [str(item.get("name", "")).strip() for item in self.engine.derived_signal_definitions if str(item.get("name", "")).strip()]
        formula_signals = [item["name"] for item in load_formula_signal_definitions()]
        kpi_signals = [str(item.get("name", "")).strip() for item in self.engine.kpi_definitions if str(item.get("name", "")).strip()]
        self.plot_signal_names = sorted({*get_plot_signal_names(), *derived_signals, *formula_signals, *kpi_signals})
        self._derived_signal_names = sorted(set(derived_signals))
        self._formula_signal_names = sorted(formula_signals)
        self._interface_signal_names = sorted(get_plot_signal_names())
        self._kpi_signal_names = sorted(set(kpi_signals))
        self._signal_browser_all = list(self.plot_signal_names)
        self.filter_signal_browser(self.signal_search_edit.text())
        self._rebuild_kpi_path_index()
        self._populate_group_combo(self.queue_group_combo, current_queue_group)
        self._populate_group_combo(self.kpi_group_editor_combo, current_group)
        self._rebuild_queue_list_widget()
        self.refresh_dbc_list()
        self.kpi_group_kpi_list.clear()
        ordered_kpis = sorted(
            self.engine.kpi_definitions,
            key=lambda item: self._sort_text_key(str(item.get("title", item.get("name", "")))),
        )
        for definition in ordered_kpis:
            item = QListWidgetItem(str(definition.get("title", definition.get("name", ""))))
            item.setData(Qt.ItemDataRole.UserRole, str(definition.get("name", "")))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.kpi_group_kpi_list.addItem(item)
        if self.engine.invalid_runtime_issues:
            for issue in self.engine.invalid_runtime_issues[:5]:
                self.log(
                    "warning",
                    f"已跳过无效配置: {self._issue_summary_text(issue)}",
                    link_target={"path": str(issue.path), "line": issue.line, "column": issue.column},
                )
            if len(self.engine.invalid_runtime_issues) > 5:
                self.log("warning", f"另有 {len(self.engine.invalid_runtime_issues) - 5} 个无效配置已被跳过，可在配置工作台中继续修复。")
        self.load_kpi_group_from_combo()
        self._populate_entry_combo(self.derived_signal_editor_combo, self.derived_signal_entries, current_derived)
        self._populate_entry_combo(self.kpi_editor_combo, self.kpi_spec_entries, current_kpi)
        self._populate_entry_combo(self.template_editor_combo, self.template_entries, current_template)
        self._populate_entry_combo(self.active_template_combo, self.template_entries, current_template)
        self._refresh_result_scope_combo()
        self.load_mapping_editor()
        if current_derived and "derived" not in preserved:
            self.load_derived_signal_file(Path(current_derived), log_message=False)
        elif current_derived and "derived" in preserved:
            self.derived_signal_editor_path = Path(current_derived)
            self.derived_signal_editor_path_label.setText(current_derived)
            self._set_combo_to_path(self.derived_signal_editor_combo, Path(current_derived))
            self._apply_editor_protection(Path(current_derived), self.derived_signal_editor, self.derived_signal_delete_button, self.derived_signal_editor_notice, PROTECTED_DERIVED_FILES)
            self._set_derived_signal_editor_dirty(False)
        elif self.derived_signal_entries:
            self.load_derived_signal_file(Path(self.derived_signal_entries[0]["path"]), log_message=False)
        if current_kpi and "kpi" not in preserved:
            self.load_kpi_file(Path(current_kpi), log_message=False)
        elif current_kpi and "kpi" in preserved:
            self.kpi_editor_path = Path(current_kpi)
            self.kpi_editor_path_label.setText(current_kpi)
            self._set_combo_to_path(self.kpi_editor_combo, Path(current_kpi))
            self._apply_editor_protection(Path(current_kpi), self.kpi_editor, self.kpi_delete_button, self.kpi_editor_notice, PROTECTED_KPI_FILES)
            self._set_kpi_editor_dirty(False)
        elif self.kpi_spec_entries:
            self.load_kpi_file(Path(self.kpi_spec_entries[0]["path"]), log_message=False)
        if current_template and "template" not in preserved:
            self.load_template_file(Path(current_template), log_message=False)
        elif current_template and "template" in preserved:
            self.template_editor_path = Path(current_template)
            self.template_editor_path_label.setText(current_template)
            self._set_combo_to_path(self.template_editor_combo, Path(current_template))
            self._set_combo_to_path(self.active_template_combo, Path(current_template))
            self._apply_editor_protection(Path(current_template), self.template_editor, self.template_delete_button, self.template_editor_notice, PROTECTED_TEMPLATE_FILES, self.template_save_button)
        elif self.template_entries:
            self.load_template_file(Path(self.template_entries[0]["path"]), log_message=False)
        self._refresh_chart_sheet_tabs()
        if not self.chart_panels:
            defaults: list[list[str]] = []
            for name in ["vehicle_speed", "wheel_speed_rl", "tcs_active"]:
                if name in self.plot_signal_names:
                    if not defaults:
                        defaults.append([name])
            if not defaults:
                defaults = [[self.plot_signal_names[0]]] if self.plot_signal_names else []
            for signals in defaults:
                self.add_chart_panel(signals)
        else:
            self._switch_chart_sheet(self.active_chart_sheet_index, refresh=False)
            for panel in self.chart_panels:
                signals = [signal for signal in panel["signals"] if signal in self.plot_signal_names]
                panel["signals"] = signals
            self._persist_chart_view_state()
        self._update_queue_stats()
        self.refresh_result_views()
        if log_message:
            self.log("info", "KPI、模板、接口映射和表达式信号配置已重新加载。")

    def _prepare_chart_frame(self, result: AnalysisResult):  # noqa: ANN001
        cache_key = str(result.context.source_path)
        cached = self._chart_frame_cache.get(cache_key)
        if cached is not None:
            return cached
        frame_data = result.normalized_frame.copy()
        related_results = self._chart_results_for_path(str(result.context.source_path))
        for related_result in related_results:
            populate_kpi_signal_values(
                related_result.normalized_frame,
                related_result.kpis,
                group_key=str(related_result.context.metadata.get("kpi_group_key", "__all_kpis__")),
            )
            for item in related_result.kpis:
                if item.signal_values is not None:
                    frame_data[item.name] = item.signal_values.reindex(frame_data.index)
                else:
                    frame_data[item.name] = float(item.value)
        local_context: dict[str, object] = {column: frame_data[column] for column in frame_data.columns}
        for definition in load_formula_signal_definitions():
            expression = str(definition.get("expression", "")).strip()
            name = str(definition.get("name", "")).strip()
            if not expression or not name:
                continue
            try:
                value = eval(expression, {"__builtins__": {}}, {**local_context, "math": math, "min": min, "max": max, "abs": abs})
            except Exception:
                continue
            if hasattr(value, "reindex"):
                frame_data[name] = value.reindex(frame_data.index)
            else:
                frame_data[name] = value
            local_context[name] = frame_data[name]
        self._chart_frame_cache[cache_key] = frame_data
        self._chart_sample_cache[cache_key] = self._downsample_frame(frame_data)
        return frame_data

    def create_formula_signal(self) -> None:
        dialog = FormulaSignalDialog(self._signal_browser_all, self, title="新增自定义信号")
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        name, expression = dialog.values()
        if not name or not expression:
            QMessageBox.information(self, "信息不完整", "请填写信号名称和公式表达式。")
            return
        try:
            save_formula_signal_definition(name, expression)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "保存失败", str(exc))
            return
        self._chart_frame_cache.clear()
        self._chart_sample_cache.clear()
        self._chart_sample_cache.clear()
        self.reload_runtime_configs(log_message=False)
        self.log("success", f"表达式信号已保存: {name} = {expression}")

    def edit_formula_signal(self, item: QListWidgetItem) -> None:
        signal_name = item.text().strip()
        definitions = {entry["name"]: entry["expression"] for entry in load_formula_signal_definitions()}
        dialog = FormulaSignalDialog(
            self._signal_browser_all,
            self,
            title=f"编辑自定义信号: {signal_name}",
            name=signal_name,
            expression=definitions.get(signal_name, ""),
            allow_rename=False,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        _name, expression = dialog.values()
        if not expression:
            QMessageBox.information(self, "信息不完整", "公式表达式不能为空。")
            return
        save_formula_signal_definition(signal_name, expression)
        self._chart_frame_cache.clear()
        self._chart_sample_cache.clear()
        self._chart_sample_cache.clear()
        self.reload_runtime_configs(log_message=False)
        self.log("success", f"已更新自定义信号: {signal_name} = {expression}")

    def delete_formula_signal(self, item: QListWidgetItem) -> None:
        signal_name = item.text().strip()
        if QMessageBox.question(self, "删除自定义信号", f"确认删除自定义信号？\n{signal_name}") != QMessageBox.StandardButton.Yes:
            return
        delete_formula_signal_definition(signal_name)
        for panel in self.chart_panels:
            signals: list[str] = panel["signals"]
            if signal_name in signals:
                signals.remove(signal_name)
        self._chart_frame_cache.clear()
        self._chart_sample_cache.clear()
        self._chart_sample_cache.clear()
        self.reload_runtime_configs(log_message=False)
        self.log("warning", f"已删除自定义信号: {signal_name}")

    def _rebuild_kpi_path_index(self) -> None:
        self._kpi_path_by_name = {}
        self._derived_signal_path_by_name = {}
        for definition in self.engine.kpi_definitions:
            kpi_name = str(definition.get("name", "")).strip()
            module_path = str(definition.get("module_path", "")).strip()
            if kpi_name:
                self._kpi_path_by_name[kpi_name] = Path(module_path)
        for definition in load_derived_signal_definitions():
            signal_name = str(definition.get("name", "")).strip()
            module_path = str(definition.get("module_path", "")).strip()
            if signal_name:
                self._derived_signal_path_by_name[signal_name] = Path(module_path)

    def _confirm_current_editor_navigation(self) -> bool:
        if not hasattr(self, "config_tabs"):
            return True
        current_index = self.config_tabs.currentIndex()
        if current_index == 0:
            return self._confirm_pending_editor_changes("derived")
        if current_index == 1:
            return self._confirm_pending_editor_changes("kpi")
        return True

    def _open_kpi_editor_by_name(self, kpi_name: str, raw_input_name: str | None = None) -> bool:
        target = self._kpi_path_by_name.get(str(kpi_name).strip())
        if target is None or not self._confirm_current_editor_navigation():
            return False
        self.tabs.setCurrentIndex(3)
        self.config_tabs.setCurrentIndex(1)
        self.load_kpi_file(target, raw_input_name=raw_input_name)
        return True

    def _open_derived_editor_by_name(self, signal_name: str, raw_input_name: str | None = None) -> bool:
        target = self._derived_signal_path_by_name.get(str(signal_name).strip())
        if target is None or not self._confirm_current_editor_navigation():
            return False
        self.tabs.setCurrentIndex(3)
        self.config_tabs.setCurrentIndex(0)
        self.load_derived_signal_file(target, raw_input_name=raw_input_name)
        return True

    def _format_requirement_owner(self, owner: str) -> str:
        normalized = str(owner).strip()
        if normalized.startswith("KPI:"):
            return f"KPI: {normalized.split(':', 1)[1]}"
        if normalized.startswith("DERIVED:"):
            return f"派生量: {normalized.split(':', 1)[1]}"
        return normalized

    def _open_definition_owner(self, owner: str, raw_input_name: str | None = None) -> bool:
        normalized = str(owner).strip()
        if normalized.startswith("KPI:"):
            return self._open_kpi_editor_by_name(normalized.split(":", 1)[1], raw_input_name=raw_input_name)
        if normalized.startswith("DERIVED:"):
            return self._open_derived_editor_by_name(normalized.split(":", 1)[1], raw_input_name=raw_input_name)
        return False

    def _open_derived_from_kpi_editor_token(self, token: str) -> bool:
        return token in self._derived_signal_path_by_name and self._open_derived_editor_by_name(token)

    def _open_derived_from_derived_editor_token(self, token: str) -> bool:
        return token in self._derived_signal_path_by_name and self._open_derived_editor_by_name(token)

    def open_kpi_from_result_row(self, row: int, _column: int) -> None:
        item = self.rule_table.item(row, 0)
        if item is None:
            return
        kpi_name = str(item.data(Qt.ItemDataRole.UserRole) or "").strip()
        self._open_kpi_editor_by_name(kpi_name)

    def on_rule_table_cell_double_clicked(self, row: int, column: int) -> None:
        item = self.rule_table.item(row, 0)
        if item is None:
            return
        row_kind = str(item.data(RESULT_ROW_KIND_ROLE) or "")
        if row_kind == "file":
            result_path = str(item.data(RESULT_ROW_PATH_ROLE) or "").strip()
            if result_path:
                self.open_result_in_chart_tab(result_path)
            return
        if row_kind == "kpi":
            self.open_kpi_from_result_row(row, column)

    def open_result_in_chart_tab(self, result_path: str) -> None:
        if not result_path:
            return
        self.tabs.setCurrentIndex(2)
        self._set_result_scope(result_path)

    def open_kpi_from_group_item(self, item: QListWidgetItem) -> None:
        self._open_kpi_editor_by_name(str(item.data(Qt.ItemDataRole.UserRole) or "").strip())

    def open_mapping_source_from_cell(self, row: int, column: int) -> None:
        if column != 1:
            return
        item = self.system_mapping_table.item(row, column)
        signal_item = self.system_mapping_table.item(row, 0)
        if item is None:
            return
        raw_input_name = "" if signal_item is None else signal_item.text().strip()
        owners = item.data(Qt.ItemDataRole.UserRole) or []
        if isinstance(owners, str):
            owners = [owners]
        if not owners:
            return
        if len(owners) == 1:
            self._open_definition_owner(str(owners[0]), raw_input_name=raw_input_name)
            return
        labels = [self._format_requirement_owner(str(owner)) for owner in owners]
        selected, ok = QInputDialog.getItem(self, "选择来源定义", "该系统信号被多个定义引用，选择要跳转的目标：", labels, 0, False)
        if not ok or not selected:
            return
        selected_index = labels.index(selected)
        self._open_definition_owner(str(owners[selected_index]), raw_input_name=raw_input_name)

    def _populate_entry_combo(self, combo: QComboBox, entries: list[dict[str, object]], selected_path: str | None = None) -> None:
        combo.blockSignals(True)
        combo.clear()
        selected_index = 0
        for index, entry in enumerate(entries):
            entry_path = str(entry["path"])
            combo.addItem(str(entry["display_name"]), entry_path)
            if selected_path and entry_path == selected_path:
                selected_index = index
        if entries:
            combo.setCurrentIndex(selected_index)
        combo.blockSignals(False)

    def _entry_display_name(self, entries: list[dict[str, object]], entry_path: str | None) -> str:
        for entry in entries:
            if str(entry.get("path")) == str(entry_path):
                return str(entry.get("display_name", ""))
        return Path(str(entry_path)).stem if entry_path else ""

    def _set_editor_plain_text(self, editor: QPlainTextEdit, content: str) -> None:
        self._editor_loading = True
        try:
            editor.setPlainText(content)
        finally:
            self._editor_loading = False

    def _update_editor_combo_marker(self, combo: QComboBox, entries: list[dict[str, object]], path: Path | None, dirty: bool) -> None:
        target = str(path) if path else None
        for index in range(combo.count()):
            entry_path = str(combo.itemData(index) or "")
            base_name = self._entry_display_name(entries, entry_path)
            combo.setItemText(index, f"{base_name} *" if dirty and entry_path == target else base_name)

    def _set_derived_signal_editor_dirty(self, dirty: bool) -> None:
        self._derived_signal_editor_dirty = dirty
        self._update_editor_combo_marker(self.derived_signal_editor_combo, self.derived_signal_entries, self.derived_signal_editor_path, dirty)

    def _set_kpi_editor_dirty(self, dirty: bool) -> None:
        self._kpi_editor_dirty = dirty
        self._update_editor_combo_marker(self.kpi_editor_combo, self.kpi_spec_entries, self.kpi_editor_path, dirty)

    def _on_derived_signal_editor_text_changed(self) -> None:
        if not self._editor_loading and self.derived_signal_editor_path is not None:
            self._clear_editor_issue_markers(self.derived_signal_editor)
            self._set_derived_signal_editor_dirty(True)

    def _on_kpi_editor_text_changed(self) -> None:
        if not self._editor_loading and self.kpi_editor_path is not None:
            self._clear_editor_issue_markers(self.kpi_editor)
            self._set_kpi_editor_dirty(True)

    def _confirm_editor_switch(self, title: str, message: str, save_callback) -> bool:
        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Icon.Question)
        dialog.setWindowTitle(title)
        dialog.setText(message)
        save_button = dialog.addButton("保存", QMessageBox.ButtonRole.AcceptRole)
        discard_button = dialog.addButton("不保存", QMessageBox.ButtonRole.DestructiveRole)
        cancel_button = dialog.addButton("取消", QMessageBox.ButtonRole.RejectRole)
        dialog.setDefaultButton(save_button)
        dialog.exec()
        clicked = dialog.clickedButton()
        if clicked == save_button:
            save_callback()
            return True
        if clicked == discard_button:
            return True
        if clicked == cancel_button or clicked is None:
            return False
        return True

    def _confirm_pending_editor_changes(self, editor_kind: str) -> bool:
        if editor_kind == "kpi" and self._kpi_editor_dirty:
            return self._confirm_editor_switch("未保存的 KPI", "当前 KPI 文件尚未保存，是否先保存？", self.save_kpi_file)
        if editor_kind == "derived" and self._derived_signal_editor_dirty:
            return self._confirm_editor_switch("未保存的派生量", "当前派生量文件尚未保存，是否先保存？", self.save_derived_signal_file)
        return True

    def load_kpi_from_editor_combo(self, *_args) -> None:
        selected = self.kpi_editor_combo.currentData()
        if not selected:
            return
        target = Path(str(selected))
        if self.kpi_editor_path is not None and target == self.kpi_editor_path:
            return
        if self._kpi_editor_dirty and not self._confirm_editor_switch("切换 KPI", "当前 KPI 文件尚未保存，是否先保存？", self.save_kpi_file):
            if self.kpi_editor_path is not None:
                self._set_combo_to_path(self.kpi_editor_combo, self.kpi_editor_path)
            return
        self.load_kpi_file(target)

    def load_derived_signal_from_editor_combo(self, *_args) -> None:
        selected = self.derived_signal_editor_combo.currentData()
        if not selected:
            return
        target = Path(str(selected))
        if self.derived_signal_editor_path is not None and target == self.derived_signal_editor_path:
            return
        if self._derived_signal_editor_dirty and not self._confirm_editor_switch("切换派生量", "当前派生量文件尚未保存，是否先保存？", self.save_derived_signal_file):
            if self.derived_signal_editor_path is not None:
                self._set_combo_to_path(self.derived_signal_editor_combo, self.derived_signal_editor_path)
            return
        self.load_derived_signal_file(target)

    def load_template_from_editor_combo(self, *_args) -> None:
        selected = self.template_editor_combo.currentData()
        if selected:
            self.load_template_file(Path(selected))
            self._set_combo_to_path(self.active_template_combo, Path(selected))

    def _apply_editor_protection(
        self,
        path: Path,
        editor: QPlainTextEdit,
        delete_button: QPushButton,
        notice_label: QLabel,
        protected_names: set[str],
        save_button: QPushButton | None = None,
    ) -> None:
        is_protected = path.name in protected_names
        editor.setReadOnly(is_protected)
        if save_button is not None:
            save_button.setEnabled(not is_protected)
        delete_button.setEnabled(not is_protected)
        notice_label.setText("示例与详解为系统保护文件，不可编辑也不可删除。" if is_protected else "")

    def load_derived_signal_file(self, path: Path, log_message: bool = True, raw_input_name: str | None = None) -> None:
        self.derived_signal_editor_path = path
        self.derived_signal_editor_path_label.setText(str(path))
        self._set_editor_plain_text(self.derived_signal_editor, read_text_config_file(path))
        self._clear_editor_issue_markers(self.derived_signal_editor)
        self.derived_signal_editor.focus_named_input(raw_input_name, raw_inputs_only=bool(raw_input_name))
        self._set_combo_to_path(self.derived_signal_editor_combo, path)
        self._apply_editor_protection(path, self.derived_signal_editor, self.derived_signal_delete_button, self.derived_signal_editor_notice, PROTECTED_DERIVED_FILES)
        self._set_derived_signal_editor_dirty(False)
        if log_message:
            self.log("info", f"已载入派生量文件: {path}")

    def load_kpi_file(self, path: Path, log_message: bool = True, raw_input_name: str | None = None) -> None:
        self.kpi_editor_path = path
        self.kpi_editor_path_label.setText(str(path))
        self._set_editor_plain_text(self.kpi_editor, read_text_config_file(path))
        self._clear_editor_issue_markers(self.kpi_editor)
        self.kpi_editor.focus_named_input(raw_input_name, raw_inputs_only=bool(raw_input_name))
        self._set_combo_to_path(self.kpi_editor_combo, path)
        self._apply_editor_protection(path, self.kpi_editor, self.kpi_delete_button, self.kpi_editor_notice, PROTECTED_KPI_FILES)
        self._set_kpi_editor_dirty(False)
        if log_message:
            self.log("info", f"已载入 KPI 文件: {path}")

    def load_template_file(self, path: Path, log_message: bool = True) -> None:
        self.template_editor_path = path
        self.template_editor_path_label.setText(str(path))
        self._set_editor_plain_text(self.template_editor, read_text_config_file(path))
        self.template_editor.focus_named_input(None)
        self._set_combo_to_path(self.template_editor_combo, path)
        self._set_combo_to_path(self.active_template_combo, path)
        self._apply_editor_protection(path, self.template_editor, self.template_delete_button, self.template_editor_notice, PROTECTED_TEMPLATE_FILES, self.template_save_button)
        if log_message:
            self.log("info", f"已载入报告模板: {path}")

    def _set_combo_to_path(self, combo: QComboBox, path: Path) -> None:
        target = str(path)
        for index in range(combo.count()):
            if combo.itemData(index) == target:
                combo.setCurrentIndex(index)
                return

    def create_kpi_file(self) -> None:
        if not self._confirm_pending_editor_changes("kpi"):
            return
        try:
            path = create_kpi_draft_file()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "创建失败", str(exc))
            return
        self.reload_runtime_configs(log_message=False)
        self.load_kpi_file(path)

    def create_derived_signal_file(self) -> None:
        if not self._confirm_pending_editor_changes("derived"):
            return
        signal_name, ok = QInputDialog.getText(self, "新增派生量", "请输入派生量 name（英文）")
        if not ok:
            return
        normalized_name = signal_name.strip()
        if not normalized_name:
            QMessageBox.information(self, "名称为空", "请先输入派生量 name。")
            return
        try:
            path = create_derived_signal_draft_file(normalized_name)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "创建失败", str(exc))
            return
        self.reload_runtime_configs(log_message=False)
        self.load_derived_signal_file(path)

    def create_template_file(self) -> None:
        text, ok = QInputDialog.getText(self, "新增模板", "请输入模板名称")
        if ok and text.strip():
            try:
                path = create_report_template_file(text.strip())
            except Exception as exc:  # noqa: BLE001
                QMessageBox.warning(self, "创建失败", str(exc))
                return
            self.reload_runtime_configs(log_message=False)
            self.load_template_file(path)

    def save_kpi_file(self) -> None:
        if self.kpi_editor_path is None:
            return
        try:
            original_text = read_text_config_file(self.kpi_editor_path)
            updated_text = self.kpi_editor.toPlainText()
            issues = validate_python_config_content(self.kpi_editor_path, updated_text)
            original_name = extract_kpi_name_from_text(original_text)
            updated_name = extract_kpi_name_from_text(updated_text)
            write_text_config_file(self.kpi_editor_path, updated_text)
            renamed_path = align_python_config_file_name(self.kpi_editor_path, updated_name)
            self.kpi_editor_path = renamed_path
            self.kpi_editor_path_label.setText(str(renamed_path))
            self.kpi_editor.document().setModified(False)
            self._set_kpi_editor_dirty(False)
            if issues:
                self._apply_editor_issue_markers(self.kpi_editor, issues)
                self.kpi_editor.focus_location(issues[0].line, issues[0].column)
                self.log(
                    "warning",
                    f"KPI 文件已保存，但静态检查未通过: {self._issue_summary_text(issues[0])}",
                    link_target={"path": str(renamed_path), "line": issues[0].line, "column": issues[0].column},
                )
                summary_lines = [self._issue_summary_text(issue) for issue in issues[:5]]
                if len(issues) > 5:
                    summary_lines.append(f"其余 {len(issues) - 5} 个问题已在编辑器中用红色高亮。")
                QMessageBox.warning(
                    self,
                    "KPI 静态检查未通过",
                    "文件已保存，但以下问题必须修复后才能开始分析：\n\n" + "\n".join(summary_lines),
                )
                return
            self._clear_editor_issue_markers(self.kpi_editor)
            rename_kpi_references(original_name, updated_name)
            self.reload_runtime_configs(log_message=False, preserve_editors={"kpi"})
            self.log("success", f"KPI 文件已保存: {self.kpi_editor_path}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "保存失败", str(exc))

    def save_derived_signal_file(self) -> None:
        if self.derived_signal_editor_path is None:
            return
        try:
            original_text = read_text_config_file(self.derived_signal_editor_path)
            updated_text = self.derived_signal_editor.toPlainText()
            issues = validate_python_config_content(self.derived_signal_editor_path, updated_text)
            original_name = extract_derived_signal_name_from_text(original_text)
            updated_name = extract_derived_signal_name_from_text(updated_text)
            write_text_config_file(self.derived_signal_editor_path, updated_text)
            renamed_path = align_python_config_file_name(self.derived_signal_editor_path, updated_name)
            self.derived_signal_editor_path = renamed_path
            self.derived_signal_editor_path_label.setText(str(renamed_path))
            self.derived_signal_editor.document().setModified(False)
            self._set_derived_signal_editor_dirty(False)
            if issues:
                self._apply_editor_issue_markers(self.derived_signal_editor, issues)
                self.derived_signal_editor.focus_location(issues[0].line, issues[0].column)
                self.log(
                    "warning",
                    f"派生量文件已保存，但静态检查未通过: {self._issue_summary_text(issues[0])}",
                    link_target={"path": str(renamed_path), "line": issues[0].line, "column": issues[0].column},
                )
                QMessageBox.warning(self, "派生量静态检查未通过", "文件已保存，但存在基础错误，已用红色高亮。修复后才能开始分析。")
                return
            self._clear_editor_issue_markers(self.derived_signal_editor)
            rename_derived_signal_references(original_name, updated_name)
            self.reload_runtime_configs(log_message=False, preserve_editors={"derived"})
            self.log("success", f"派生量文件已保存: {self.derived_signal_editor_path}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "保存失败", str(exc))

    def save_template_file(self) -> None:
        if self.template_editor_path is None:
            return
        try:
            write_text_config_file(self.template_editor_path, self.template_editor.toPlainText())
            self.reload_runtime_configs(log_message=False, preserve_editors={"template"})
            self.template_editor.document().setModified(False)
            self.log("success", f"模板文件已保存: {self.template_editor_path}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "保存失败", str(exc))

    def _delete_text_config(self, path: Path | None, protected_names: set[str], title: str) -> bool:
        if path is None:
            return False
        if path.name in protected_names:
            QMessageBox.information(self, "禁止删除", f"{path.name} 为系统保护文件，不能删除。")
            return False
        if QMessageBox.question(self, title, f"确认删除文件？\n{path}") != QMessageBox.StandardButton.Yes:
            return False
        delete_config_file(path)
        return True

    def delete_kpi_file(self) -> None:
        if not self._confirm_pending_editor_changes("kpi"):
            return
        if self._delete_text_config(self.kpi_editor_path, PROTECTED_KPI_FILES, "删除 KPI"):
            self.kpi_editor_path = None
            self.reload_runtime_configs(log_message=False)

    def delete_derived_signal_file(self) -> None:
        if not self._confirm_pending_editor_changes("derived"):
            return
        if self._delete_text_config(self.derived_signal_editor_path, PROTECTED_DERIVED_FILES, "删除派生量"):
            self.derived_signal_editor_path = None
            self.reload_runtime_configs(log_message=False)

    def closeEvent(self, event) -> None:  # noqa: N802
        if not self._confirm_pending_editor_changes("derived"):
            event.ignore()
            return
        if not self._confirm_pending_editor_changes("kpi"):
            event.ignore()
            return
        super().closeEvent(event)

    def delete_template_file(self) -> None:
        if self._delete_text_config(self.template_editor_path, PROTECTED_TEMPLATE_FILES, "删除模板"):
            self.template_editor_path = None
            self.reload_runtime_configs(log_message=False)

    def load_mapping_editor(self) -> None:
        tables = load_interface_signal_tables()
        self._populate_mapping_table(self.system_mapping_table, tables.get("system", []), False)
        self._populate_mapping_table(self.custom_mapping_table, tables.get("custom", []), True)
        self._refresh_mapping_validation()

    def _refresh_and_schedule_mapping_persist(self) -> None:
        self._refresh_mapping_validation()
        self._mapping_persist_timer.start(250)

    def _populate_mapping_table(self, table: QTableWidget, rows: list[dict[str, object]], first_column_editable: bool) -> None:
        table.blockSignals(True)
        table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            is_system_table = table is self.system_mapping_table
            actual_names = list(row.get("actual_names", []))[:5]
            values = [str(row.get("standard_signal", ""))]
            if is_system_table:
                values.append("\n".join(self._format_requirement_owner(owner) for owner in row.get("required_by", [])))
            values.extend(actual_names)
            while len(values) < table.columnCount():
                values.append("")
            for column_index, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column_index == 0 and not first_column_editable:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if is_system_table and column_index == 1:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    item.setData(Qt.ItemDataRole.UserRole, list(row.get("required_by", [])))
                    item.setToolTip("双击跳转到来源定义\n" + "\n".join(self._format_requirement_owner(owner) for owner in row.get("required_by", [])))
                table.setItem(row_index, column_index, item)
            if is_system_table:
                owner_count = max(1, len(row.get("required_by", [])))
                table.setRowHeight(row_index, max(30, 18 * owner_count))
        table.blockSignals(False)

    def _on_mapping_table_changed(self, *_args) -> None:
        self._refresh_and_schedule_mapping_persist()

    def _extract_mapping_rows(self, table: QTableWidget) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        actual_name_start = 2 if table is self.system_mapping_table else 1
        for row_index in range(table.rowCount()):
            signal_name = (table.item(row_index, 0).text() if table.item(row_index, 0) is not None else "").strip()
            actual_names = []
            for column_index in range(actual_name_start, table.columnCount()):
                cell = table.item(row_index, column_index)
                value = "" if cell is None else cell.text().strip()
                if value:
                    actual_names.append(value)
            if signal_name:
                rows.append({"standard_signal": signal_name, "actual_names": actual_names})
        return rows

    def save_mapping_editor(self) -> None:
        self._persist_mapping_editor_state()
        self.log("success", "接口映射已保存。")

    def _persist_mapping_editor_state(self) -> None:
        if self._persisting_mapping:
            return
        self._persisting_mapping = True
        try:
            save_interface_signal_tables(self._extract_mapping_rows(self.system_mapping_table), self._extract_mapping_rows(self.custom_mapping_table))
            self._interface_signal_names = sorted(get_plot_signal_names())
            self.plot_signal_names = sorted({*self._interface_signal_names, *self._derived_signal_names, *self._formula_signal_names, *self._kpi_signal_names})
            self._signal_browser_all = list(self.plot_signal_names)
            self.filter_signal_browser(self.signal_search_edit.text())
        finally:
            self._persisting_mapping = False

    def add_custom_mapping_row(self) -> None:
        row_index = self.custom_mapping_table.rowCount()
        self.custom_mapping_table.blockSignals(True)
        self.custom_mapping_table.insertRow(row_index)
        for column_index in range(len(CUSTOM_MAPPING_HEADERS)):
            self.custom_mapping_table.setItem(row_index, column_index, QTableWidgetItem(""))
        self.custom_mapping_table.blockSignals(False)
        self.mapping_tabs.setCurrentIndex(1)
        self._refresh_and_schedule_mapping_persist()

    def delete_selected_custom_mapping_row(self) -> None:
        selected_rows = sorted({index.row() for index in self.custom_mapping_table.selectedIndexes()}, reverse=True)
        for row_index in selected_rows:
            self.custom_mapping_table.removeRow(row_index)
        self._refresh_and_schedule_mapping_persist()

    def _invalid_mapping_rows(self, table: QTableWidget) -> set[int]:
        invalid_rows: set[int] = set()
        actual_name_start = 2 if table is self.system_mapping_table else 1
        for row_index in range(table.rowCount()):
            signal_item = table.item(row_index, 0)
            signal_name = "" if signal_item is None else signal_item.text().strip()
            if not signal_name:
                continue
            has_actual_name = False
            for column_index in range(actual_name_start, table.columnCount()):
                cell = table.item(row_index, column_index)
                if cell is not None and cell.text().strip():
                    has_actual_name = True
                    break
            if not has_actual_name:
                invalid_rows.add(row_index)
        return invalid_rows

    def _apply_mapping_row_highlight(self, table: QTableWidget, invalid_rows: set[int]) -> None:
        for row_index in range(table.rowCount()):
            is_invalid = row_index in invalid_rows
            background = QColor("#fee2e2") if is_invalid else QColor("#ffffff")
            foreground = QColor("#991b1b") if is_invalid else QColor("#0f172a")
            for column_index in range(table.columnCount()):
                item = table.item(row_index, column_index)
                if item is None:
                    item = QTableWidgetItem("")
                    table.setItem(row_index, column_index, item)
                item.setBackground(background)
                item.setForeground(foreground)

    def _refresh_mapping_validation(self, *_args) -> None:
        self._apply_mapping_row_highlight(self.system_mapping_table, self._invalid_mapping_rows(self.system_mapping_table))
        self._apply_mapping_row_highlight(self.custom_mapping_table, self._invalid_mapping_rows(self.custom_mapping_table))

    def _ensure_mapping_ready_for_analysis(self) -> bool:
        invalid_system_rows = self._invalid_mapping_rows(self.system_mapping_table)
        invalid_custom_rows = self._invalid_mapping_rows(self.custom_mapping_table)
        self._apply_mapping_row_highlight(self.system_mapping_table, invalid_system_rows)
        self._apply_mapping_row_highlight(self.custom_mapping_table, invalid_custom_rows)
        if not invalid_system_rows and not invalid_custom_rows:
            return True
        missing_names: list[str] = []
        for table, invalid_rows in [(self.system_mapping_table, invalid_system_rows), (self.custom_mapping_table, invalid_custom_rows)]:
            for row_index in sorted(invalid_rows):
                signal_item = table.item(row_index, 0)
                if signal_item is not None and signal_item.text().strip():
                    missing_names.append(signal_item.text().strip())
        self.config_tabs.setCurrentIndex(3)
        self.mapping_tabs.setCurrentIndex(0 if invalid_system_rows else 1)
        self.log("error", f"接口映射缺少实际信号名，无法开始分析。请补全这些 raw_inputs 的实际信号名: {', '.join(missing_names)}")
        QMessageBox.warning(self, "接口映射未完成", "存在未填写实际信号名的接口映射行，已用红色高亮。请先补全后再开始分析。")
        return False

    def log(self, level: str, message: str, *, link_target: dict[str, object] | None = None) -> None:
        if not self._should_display_log_message(message):
            return
        palette = {
            "info": ("#1d4ed8", "#eff6ff", "信息"),
            "success": ("#166534", "#ecfdf5", "成功"),
            "warning": ("#b45309", "#fff7ed", "提示"),
            "error": ("#b91c1c", "#fef2f2", "失败"),
        }
        color, background, label = palette.get(level, palette["info"])
        anchor_html = ""
        if link_target is not None:
            link_id = self._register_log_link(link_target)
            anchor_html = f' <a href="configjump:{link_id}" style="color:{color};font-weight:700;text-decoration:underline;">跳转</a>'
        self.log_area.append(
            f'<div style="margin:4px 0;padding:8px 10px;border-radius:10px;background:{background};color:{color};">'
            f'<span style="font-weight:700;">[{label}]</span> {html.escape(message)}{anchor_html}</div>'
        )


def launch_app() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()