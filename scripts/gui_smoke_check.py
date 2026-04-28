from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication

from tcs_smart_analyzer.config.editable_configs import delete_kpi_group, save_kpi_group
from tcs_smart_analyzer.ui.main_window import MainWindow


def main() -> None:
    app = QApplication([])
    save_kpi_group("冒烟分组", ["max_slip_kph"], key="smoke_group")
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
        for _ in range(10):
            app.processEvents()
        print("result_table_visible", window.rule_table.rowCount() > 0)
        before = len(window.results_by_key)
        combo_before = window.result_scope_combo.count()
        print("chart_scope_deduped", window.result_scope_combo.count() == 1)
        window.tabs.setCurrentIndex(2)
        for _ in range(10):
            app.processEvents()
        first_view = window.chart_panels[0]["frame"].view if window.chart_panels else None
        viewport_width = 0 if first_view is None else first_view.viewport().width()
        plot_width = 0.0 if first_view is None else float(first_view.chart().plotArea().width())
        plot_ratio = 0.0 if viewport_width <= 0 else plot_width / viewport_width
        print("chart_plot_area_full_enough", plot_ratio >= 0.65)
        window.clear_queue()
        print("results_preserved", len(window.results_by_key) == before)
        print("scope_preserved", window.result_scope_combo.count() == combo_before)
        print("scope_plain_name", all("[" not in window.result_scope_combo.itemText(index) for index in range(window.result_scope_combo.count())))

        window.add_chart_panel(["vehicle_speed"])
        window.add_chart_panel()
        print("new_panel_empty", len(window.chart_panels[-1]["signals"]) == 0)
        empty_axis_x = window.chart_panels[-1]["frame"].view.current_axis_ranges()[0]
        print("empty_last_panel_has_time_axis", empty_axis_x is not None)
        window.fit_x_charts()
        narrowed = (0.2, 0.5)
        window.sync_x_range_across_panels(narrowed)
        window.refresh_chart_panels()
        x0 = window.chart_panels[0]["frame"].view.current_axis_ranges()[0]
        x1 = window.chart_panels[1]["frame"].view.current_axis_ranges()[0]
        print("x_synced", x0 == x1 == narrowed)
        window.chart_panels[0]["frame"].body_splitter.setSizes([900, 220])
        window.chart_panels[1]["frame"].body_splitter.setSizes([600, 220])
        for _ in range(10):
            app.processEvents()
        resized_x0 = window.chart_panels[0]["frame"].view.current_axis_ranges()[0]
        resized_x1 = window.chart_panels[1]["frame"].view.current_axis_ranges()[0]
        print("x_stays_synced_after_resize", resized_x0 == resized_x1 == narrowed)

        window.cycle_cursor_mode()
        for _ in range(10):
            app.processEvents()
        cursor_lines = list(window.chart_cursor_overlay._cursor_lines)
        overlay_height = window.chart_overlay_host.height()
        full_height = bool(cursor_lines) and cursor_lines[0][1] < 80 and cursor_lines[0][2] > overlay_height - 80
        print("cursor_overlay_spans_all_panels", full_height)

        panel_state = window.chart_panels[0]
        panel_state["signals"] = ["vehicle_speed", "wheel_speed_rl"]
        window.refresh_chart_panels()
        window.add_signals_to_panel(panel_state, ["wheel_speed_rl"], source_panel_id=panel_state["panel_id"], insert_index=0)
        print("panel_signal_reordered", panel_state["signals"][:2] == ["wheel_speed_rl", "vehicle_speed"])

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