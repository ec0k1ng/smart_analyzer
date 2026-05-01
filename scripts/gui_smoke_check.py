from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from tcs_smart_analyzer.config.editable_configs import (
    delete_kpi_group,
    get_config_file_paths,
    get_interface_mapping_actual_name_column_counts,
    load_interface_signal_tables,
    save_interface_signal_tables,
    save_kpi_group,
)
from tcs_smart_analyzer.ui.main_window import MainWindow


def _pump(app: QApplication, cycles: int = 12) -> None:
    for _ in range(cycles):
        app.processEvents()


def _wait_until(app: QApplication, predicate, cycles: int = 120) -> bool:  # noqa: ANN001
    for _ in range(cycles):
        app.processEvents()
        if predicate():
            return True
    return bool(predicate())


def _check(results: list[tuple[str, bool]], name: str, condition: bool) -> None:
    results.append((name, bool(condition)))
    print(name, bool(condition))


def main() -> None:
    app = QApplication([])
    config_paths = get_config_file_paths()
    chart_state_path = config_paths["chart_view_state"]
    interface_mapping_path = config_paths["interface_mapping"]
    kpi_groups_path = config_paths["kpi_groups"]
    backups = {
        "chart_view_state": chart_state_path.read_text(encoding="utf-8") if chart_state_path.exists() else None,
        "interface_mapping": interface_mapping_path.read_bytes() if interface_mapping_path.exists() else None,
        "kpi_groups": kpi_groups_path.read_text(encoding="utf-8") if kpi_groups_path.exists() else None,
    }
    save_kpi_group("冒烟分组", ["max_slip_kph"], key="smoke_group")
    results: list[tuple[str, bool]] = []
    try:
        window = MainWindow()
        window.show()
        window.export_html_checkbox.setChecked(False)
        window.export_word_checkbox.setChecked(False)
        demo = Path(__file__).resolve().parents[1] / "sample_data" / "tcs_demo.csv"

        window._add_paths([demo])
        for index in range(window.queue_group_combo.count()):
            if window.queue_group_combo.itemData(index) == "smoke_group":
                window.queue_group_combo.setCurrentIndex(index)
                break
        window._add_paths([demo])
        _pump(app)
        queue_paths = [(entry["path"], entry["group_key"]) for entry in window.queue_entries]
        _check(results, "duplicate_path_across_groups", len(queue_paths) == 2 and len(set(queue_paths)) == 2)
        _check(results, "grouped_queue", window.file_list.count() >= 3)
        _check(results, "derived_editor_loaded", window.derived_signal_editor_combo.count() > 0 and window.config_tabs.tabText(0) == "派生量编辑")

        mapping_counts = get_interface_mapping_actual_name_column_counts()
        tables = load_interface_signal_tables()
        sample_mapping = {
            "time_s": ["time_s"],
            "vehicle_speed_kph": ["vehicle_speed"],
            "wheel_speed_fl_kph": ["wheel_speed_fl"],
            "wheel_speed_fr_kph": ["wheel_speed_fr"],
            "wheel_speed_rl_kph": ["wheel_speed_rl"],
            "wheel_speed_rr_kph": ["wheel_speed_rr"],
            "accel_pedal_pct": ["accel_pedal_pct"],
            "brake_depth_pct": ["time_s*0"],
            "torque_request_nm": ["torque_request_nm"],
            "torque_actual_nm": ["torque_actual_nm"],
            "longitudinal_accel_mps2": ["longitudinal_accel_mps2"],
            "steering_wheel_angle_deg": ["time_s*0"],
            "yaw_rate_degps": ["time_s*0"],
            "tcs_active_fl": ["tcs_active"],
            "tcs_active_fr": ["tcs_active"],
            "tcs_active_rl": ["tcs_active"],
            "tcs_active_rr": ["tcs_active"],
        }
        for row in tables.get("system", []):
            signal_name = str(row.get("standard_signal", "")).strip()
            if signal_name in sample_mapping:
                row["actual_names"] = list(sample_mapping[signal_name])
        save_interface_signal_tables(
            tables.get("system", []),
            tables.get("custom", []),
            actual_name_column_count=max(mapping_counts.values()),
            system_actual_name_column_count=mapping_counts["system"],
            custom_actual_name_column_count=mapping_counts["custom"],
        )

        smoke_entries = [entry for entry in window.queue_entries if entry.get("group_key") == "smoke_group"]
        window._analyze_paths(smoke_entries)
        _wait_until(app, lambda: bool(window.results_by_key), 240)
        window.refresh_result_views()
        _pump(app, 20)
        _check(results, "result_table_visible", window.rule_table.rowCount() > 0)
        before = len(window.results_by_key)
        combo_before = window.result_scope_combo.count()
        _check(results, "chart_scope_available", window.result_scope_combo.count() >= 1)
        window.tabs.setCurrentIndex(2)
        _wait_until(app, lambda: bool(window.chart_panels) and window.chart_panels[0]["frame"].signal_table.rowCount() > 0, 160)
        first_view = window.chart_panels[0]["frame"].view if window.chart_panels else None
        viewport_width = 0 if first_view is None else first_view.viewport().width()
        plot_width = 0.0 if first_view is None else float(first_view.chart().plotArea().width())
        plot_ratio = 0.0 if viewport_width <= 0 else plot_width / viewport_width
        _check(results, "chart_plot_area_full_enough", plot_ratio >= 0.65)
        window.clear_queue()
        _check(results, "results_preserved", len(window.results_by_key) == before)
        _check(results, "scope_preserved", window.result_scope_combo.count() == combo_before)
        _check(results, "scope_plain_name", all("[" not in window.result_scope_combo.itemText(index) for index in range(window.result_scope_combo.count())))

        panel_state = window.chart_panels[0]
        first_signal, second_signal = "vehicle_speed_kph", "wheel_speed_rl_kph"
        if len(window.chart_panels) < 2:
            window.add_chart_panel([first_signal])
            _pump(app, 8)
        panel_state["signals"] = [first_signal, second_signal]
        panel_state["hidden_signals"] = []
        second_panel = window.chart_panels[1]
        second_panel["signals"] = [first_signal]
        second_panel["hidden_signals"] = []
        window.refresh_chart_panels()
        _pump(app, 10)
        window.add_signals_to_panel(panel_state, [second_signal], source_panel_id=panel_state["panel_id"], insert_index=0)
        _pump(app, 10)
        _check(results, "panel_signal_reordered", panel_state["signals"][:2] == [second_signal, first_signal])

        signal_table = panel_state["frame"].signal_table
        signal_table.setFocus()
        signal_table.setCurrentCell(0, 0)
        signal_table.selectRow(0)
        signal_table._refresh_row_styles()
        _pump(app, 4)
        selected_item = signal_table.item(0, 0)
        _check(results, "panel_selected_row_bold", selected_item is not None and selected_item.font().bold())

        window.toggle_selected_panel_signals_visibility()
        _pump(app, 8)
        _check(results, "panel_hide_local", panel_state["hidden_signals"] == [panel_state["signals"][0]] and second_panel["hidden_signals"] == [])
        hidden_value_item = signal_table.item(0, 1)
        other_value_item = second_panel["frame"].signal_table.item(0, 1)
        _check(results, "panel_hide_blanks_local_value", hidden_value_item is not None and hidden_value_item.text() == "")
        _check(results, "panel_hide_does_not_affect_other_panel", other_value_item is not None and other_value_item.text() != "")

        window.tabs.setCurrentIndex(3)
        window.config_tabs.setCurrentIndex(3)
        _pump(app, 10)
        _check(results, "mapping_add_button_visible", window.system_mapping_header_add_button.isVisible())
        time_desc_item = window.system_mapping_table.item(0, 1)
        _check(results, "mapping_time_s_description_updated", time_desc_item is not None and time_desc_item.text().strip() == "时间轴，单位 s。")
        system_count_before = window._system_mapping_actual_name_column_count
        custom_count_before = window._custom_mapping_actual_name_column_count
        window._set_mapping_actual_name_column_count(window.system_mapping_table, max(1, system_count_before - 1))
        _pump(app, 6)
        _check(results, "mapping_system_delete_keeps_custom_columns", window._custom_mapping_actual_name_column_count == custom_count_before)
        _check(results, "mapping_system_columns_shrink", window._system_mapping_actual_name_column_count == max(1, system_count_before - 1))
        window._set_mapping_actual_name_column_count(window.system_mapping_table, system_count_before)
        _pump(app, 6)

        from_item = window.system_mapping_table.item(0, 1)
        mapping_item = window.system_mapping_table.item(0, 3)
        if mapping_item is None:
            raise RuntimeError("system mapping table missing expected item")
        _check(results, "mapping_from_visible", from_item is not None and bool(from_item.text().strip()))
        original_text = mapping_item.text()
        mapping_item.setText("")
        window._on_mapping_table_changed()
        invalid_color = window.system_mapping_table.item(0, 0).background().color().name()
        mapping_item.setText(original_text or "vehicle_speed")
        window._on_mapping_table_changed()
        valid_color = window.system_mapping_table.item(0, 0).background().color().name()
        _check(results, "mapping_highlight_realtime", invalid_color != valid_color)

        failed = [name for name, passed in results if not passed]
        print("summary_passed", len(results) - len(failed), "/", len(results))
        if failed:
            print("summary_failed", ", ".join(failed))
            raise SystemExit(1)
    finally:
        if backups["chart_view_state"] is None:
            if chart_state_path.exists():
                chart_state_path.unlink()
        else:
            chart_state_path.write_text(backups["chart_view_state"], encoding="utf-8")
        if backups["interface_mapping"] is not None:
            interface_mapping_path.write_bytes(backups["interface_mapping"])
        if backups["kpi_groups"] is not None:
            kpi_groups_path.write_text(backups["kpi_groups"], encoding="utf-8")
        delete_kpi_group("smoke_group")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # pragma: no cover - smoke baseline should fail loudly
        print("smoke_script_error", exc)
        sys.exit(1)