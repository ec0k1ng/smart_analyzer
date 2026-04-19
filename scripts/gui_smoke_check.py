from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication

from tcs_smart_analyzer.config.editable_configs import delete_kpi_group, save_kpi_group
from tcs_smart_analyzer.ui.main_window import MainWindow


def main() -> None:
    app = QApplication([])
    save_kpi_group("冒烟分组", ["peak_slip_ratio"], key="smoke_group")
    try:
        window = MainWindow()
        demo = Path(__file__).resolve().parents[1] / "sample_data" / "tcs_demo.csv"

        window._add_paths([demo])
        window.queue_group_combo.setCurrentIndex(min(1, window.queue_group_combo.count() - 1))
        window._add_paths([demo])
        queue_paths = [(entry["path"], entry["group_key"]) for entry in window.queue_entries]
        print("duplicate_path_across_groups", len(queue_paths) == 2 and len(set(queue_paths)) == 2)
        print("grouped_queue", window.file_list.count() >= 3)
        print("derived_editor_loaded", window.derived_signal_editor_combo.count() > 0 and window.config_tabs.tabText(0) == "派生量编辑")

        window._analyze_paths(list(window.queue_entries))
        print("result_table_visible", window.rule_table.rowCount() > 0)
        before = len(window.results_by_key)
        combo_before = window.result_scope_combo.count()
        print("chart_scope_deduped", window.result_scope_combo.count() == 1)
        window.clear_queue()
        print("results_preserved", len(window.results_by_key) == before)
        print("scope_preserved", window.result_scope_combo.count() == combo_before)
        print("scope_plain_name", all("[" not in window.result_scope_combo.itemText(index) for index in range(window.result_scope_combo.count())))

        window.add_chart_panel(["vehicle_speed"])
        window.add_chart_panel()
        print("new_panel_empty", len(window.chart_panels[-1]["signals"]) == 0)
        window.fit_x_charts()
        narrowed = (0.2, 0.5)
        window.sync_x_range_across_panels(narrowed)
        window.refresh_chart_panels()
        x0 = window.chart_panels[0]["frame"].view.current_axis_ranges()[0]
        x1 = window.chart_panels[1]["frame"].view.current_axis_ranges()[0]
        print("x_synced", x0 == x1 == narrowed)

        from_item = window.system_mapping_table.item(0, 1)
        mapping_item = window.system_mapping_table.item(0, 2)
        if mapping_item is None:
            raise RuntimeError("system mapping table missing expected item")
        print("mapping_from_visible", from_item is not None and bool(from_item.text().strip()))
        original_text = mapping_item.text()
        mapping_item.setText("")
        window._on_mapping_table_changed()
        invalid_color = window.system_mapping_table.item(0, 0).background().color().name()
        mapping_item.setText(original_text or "vehicle_speed")
        window._on_mapping_table_changed()
        valid_color = window.system_mapping_table.item(0, 0).background().color().name()
        print("mapping_highlight_realtime", invalid_color != valid_color)
    finally:
        delete_kpi_group("smoke_group")


if __name__ == "__main__":
    main()