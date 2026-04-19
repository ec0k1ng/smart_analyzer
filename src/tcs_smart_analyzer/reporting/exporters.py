from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor
from jinja2 import Template
from openpyxl.utils import get_column_letter

from tcs_smart_analyzer.config.editable_configs import load_kpi_groups
from tcs_smart_analyzer.core.models import AnalysisResult


def _auto_fit_writer_sheets(writer) -> None:
    workbook = writer.book
    for worksheet in workbook.worksheets:
        for column_index, column_cells in enumerate(worksheet.iter_cols(), start=1):
            max_length = max((len("" if cell.value is None else str(cell.value)) for cell in column_cells), default=0)
            worksheet.column_dimensions[get_column_letter(column_index)].width = min(max(max_length + 2, 12), 60)


DEFAULT_HTML_TEMPLATE = Template(
    """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>{{ report_title }}</title>
  <style>
    :root {
      --ink: #183046;
      --muted: #5a7187;
      --line: #dbe7f1;
      --hero-a: #f8fbff;
      --hero-b: #e7f4ff;
      --group-bg: #d8eefc;
      --group-ink: #0c4a6e;
      --file-bg: #f6f9fc;
      --pass-bg: #ecfdf5;
      --pass-ink: #166534;
      --warning-bg: #fff7ed;
      --warning-ink: #b45309;
      --fail-bg: #fff1f2;
      --fail-ink: #b91c1c;
    }
    body { font-family: "Microsoft YaHei", sans-serif; margin: 0; background: linear-gradient(180deg, #f4f8fb, #eef4f7); color: var(--ink); }
    .page { max-width: 1180px; margin: 0 auto; padding: 28px; }
    .hero { padding: 22px 24px; border: 1px solid #cfe2ef; border-radius: 22px; background: linear-gradient(135deg, var(--hero-a), var(--hero-b)); box-shadow: 0 12px 32px rgba(24,48,70,0.08); margin-bottom: 22px; }
    .hero h1 { margin: 0 0 12px 0; font-size: 30px; color: #0c4a6e; }
    .hero-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 12px; }
    .hero-card { background: rgba(255,255,255,0.7); border: 1px solid rgba(207,226,239,0.9); border-radius: 16px; padding: 12px 14px; }
    .hero-card .label { font-size: 12px; color: var(--muted); margin-bottom: 4px; }
    .hero-card .value { font-weight: 700; color: var(--ink); }
    .section-title { margin: 26px 0 12px 0; font-size: 18px; color: #0f4c81; }
    .result-card { margin-bottom: 20px; border: 1px solid var(--line); border-radius: 18px; overflow: hidden; background: #fff; box-shadow: 0 8px 20px rgba(15, 76, 129, 0.05); }
    .group-bar { padding: 11px 16px; background: var(--group-bg); color: var(--group-ink); font-weight: 800; letter-spacing: 0.02em; }
    .file-bar { display: flex; justify-content: space-between; gap: 16px; padding: 12px 16px; background: var(--file-bg); color: #334155; border-top: 1px solid var(--line); }
    .file-name { font-weight: 700; }
    .file-summary { color: var(--muted); font-size: 13px; }
    table { border-collapse: collapse; width: 100%; table-layout: fixed; }
    th, td { border-top: 1px solid var(--line); padding: 9px 10px; font-size: 13px; vertical-align: top; }
    th { background: #f7fbff; text-align: left; color: #23415c; }
    td.col-unit, th.col-unit { width: 88px; text-align: center; }
    td.col-value, th.col-value { width: 120px; text-align: right; }
    td.col-result, th.col-result { width: 104px; text-align: center; }
    .result-pill { display: inline-block; min-width: 72px; padding: 4px 10px; border-radius: 999px; font-weight: 800; }
    .result-pill.pass { background: var(--pass-bg); color: var(--pass-ink); }
    .result-pill.warning { background: var(--warning-bg); color: var(--warning-ink); }
    .result-pill.fail { background: var(--fail-bg); color: var(--fail-ink); }
  </style>
</head>
<body>
  <div class="page">
    <section class="hero">
      <h1>{{ report_title }}</h1>
      <div class="hero-grid">
        <div class="hero-card"><div class="label">汇总文件数</div><div class="value">{{ file_count }}</div></div>
        <div class="hero-card"><div class="label">分析配置</div><div class="value">{{ analysis_profile }}</div></div>
        <div class="hero-card"><div class="label">分析摘要</div><div class="value">{{ report_summary }}</div></div>
        <div class="hero-card"><div class="label">生成时间</div><div class="value">{{ generated_at }}</div></div>
      </div>
    </section>

    <div class="section-title">分析结果</div>
    {% for item in results %}
    <section class="result-card">
      <div class="group-bar">{{ item.group_name }}</div>
      <div class="file-bar">
        <div class="file-name">{{ item.source_name }}</div>
        <div class="file-summary">KPI 项数：{{ item.kpi_count }}</div>
      </div>
      <table>
        <thead>
          <tr>
            <th>KPI</th>
            <th>描述</th>
            <th class="col-unit">单位</th>
            <th class="col-value">数值</th>
            <th>达标要求</th>
            <th class="col-result">结果</th>
          </tr>
        </thead>
        <tbody>
          {% for kpi in item.kpis %}
          <tr>
            <td>{{ kpi.title }}</td>
            <td>{{ kpi.description }}</td>
            <td class="col-unit">{{ kpi.unit }}</td>
            <td class="col-value">{{ kpi.value_text }}</td>
            <td>{{ kpi.rule_description }}</td>
            <td class="col-result"><span class="result-pill {{ kpi.status }}">{{ kpi.result_label }}</span></td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </section>
    {% endfor %}
  </div>
</body>
</html>
"""
)


def _set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def _set_rfonts(target, font_name: str) -> None:  # noqa: ANN001
    r_fonts = target.find(qn("w:rFonts"))
    if r_fonts is None:
        r_fonts = OxmlElement("w:rFonts")
        target.append(r_fonts)
    for key in ["ascii", "hAnsi", "eastAsia", "cs"]:
        r_fonts.set(qn(f"w:{key}"), font_name)


def _apply_run_style(run, *, font_name: str = "Microsoft YaHei", size: float | None = None, bold: bool | None = None, color: RGBColor | None = None) -> None:  # noqa: ANN001
    run.font.name = font_name
    _set_rfonts(run._element.get_or_add_rPr(), font_name)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if color is not None:
        run.font.color.rgb = color


def _apply_style_font(style, *, font_name: str = "Microsoft YaHei", size: float = 10.5) -> None:  # noqa: ANN001
    style.font.name = font_name
    style.font.size = Pt(size)
    _set_rfonts(style._element.get_or_add_rPr(), font_name)


def _style_cell_paragraphs(cell, *, size: float = 10.5, bold: bool | None = None) -> None:  # noqa: ANN001
    for paragraph in cell.paragraphs:
        for run in paragraph.runs:
            _apply_run_style(run, size=size, bold=bold)


def _group_name_lookup() -> dict[str, str]:
    groups = {"__all_kpis__": "默认组（全部 KPI）"}
    groups.update({str(item.get("key", "__all_kpis__")): str(item.get("name", "默认组（全部 KPI）")) for item in load_kpi_groups()})
    return groups


def _format_value(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{float(value):.4f}"


def _serialize_kpi(item) -> dict[str, Any]:  # noqa: ANN001
    return {
        "name": item.name,
        "title": item.title,
        "value": item.value,
        "value_text": _format_value(item.value),
        "unit": item.unit,
        "description": item.description,
        "rule_description": item.rule_description,
        "status": item.status,
        "result_label": item.result_label,
    }


def _serialize_rule(item) -> dict[str, Any]:  # noqa: ANN001
    return {
        "rule_id": item.rule_id,
        "title": item.title,
        "status": item.status,
        "measured_value": item.measured_value,
        "threshold_value": item.threshold_value,
        "message": item.message,
    }


def _serialize_result(result: AnalysisResult, report_title: str, group_names: dict[str, str]) -> dict[str, Any]:
    group_key = str(result.context.metadata.get("kpi_group_key", "__all_kpis__"))
    serialized = {
        "report_title": report_title,
        "source_path": str(result.context.source_path),
        "source_name": result.context.source_path.name,
        "source_stem": result.context.source_path.stem,
        "analysis_profile": result.context.metadata.get("analysis_profile", "default"),
        "generated_at": result.context.metadata.get("generated_at", ""),
        "mapped_columns": result.context.mapped_columns,
        "metadata": result.context.metadata,
        "group_key": group_key,
        "group_name": group_names.get(group_key, group_key),
        "kpi_count": len(result.kpis),
        "kpis": [_serialize_kpi(item) for item in result.kpis],
        "rules": [_serialize_rule(item) for item in result.rule_results],
    }
    return serialized


def build_report_context(result: AnalysisResult, report_title: str = "TCS 打滑控制自动分析报告") -> dict[str, Any]:
    group_names = _group_name_lookup()
    serialized = _serialize_result(result, report_title, group_names)
    context = dict(serialized)
    context["report_title"] = report_title
    context["file_count"] = 1
    context["report_summary"] = f"共输出 {len(serialized['kpis'])} 条 KPI 结果。"
    context["kpis"] = list(serialized["kpis"])
    context["rules"] = list(serialized["rules"])
    context["metadata"] = dict(serialized["metadata"])
    context["mapped_columns"] = dict(serialized["mapped_columns"])
    context["results"] = [serialized]
    context["files"] = context["results"]
    return context


def _flatten_batch_records(results: list[AnalysisResult]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    kpis: list[dict[str, Any]] = []
    rules: list[dict[str, Any]] = []
    group_names = _group_name_lookup()
    for result in results:
        serialized = _serialize_result(result, "", group_names)
        for item in serialized["kpis"]:
            kpis.append({
                "source_path": serialized["source_path"],
                "source_name": serialized["source_name"],
                "source_stem": serialized["source_stem"],
                "group_key": serialized["group_key"],
                "group_name": serialized["group_name"],
                **item,
            })
        for item in serialized["rules"]:
            rules.append({
                "source_path": serialized["source_path"],
                "source_name": serialized["source_name"],
                "group_key": serialized["group_key"],
                "group_name": serialized["group_name"],
                **item,
            })
    return kpis, rules


def build_batch_report_context(results: list[AnalysisResult], report_title: str = "TCS 打滑控制自动分析报告") -> dict[str, Any]:
    if not results:
        generated_at = datetime.now().astimezone().isoformat(timespec="seconds")
        return {
            "report_title": report_title,
            "generated_at": generated_at,
            "analysis_profile": "default",
            "source_path": "",
            "source_name": "",
            "source_stem": "",
            "report_summary": "",
            "mapped_columns": {},
            "metadata": {},
            "kpis": [],
            "rules": [],
            "results": [],
            "files": [],
            "file_count": 0,
        }

    group_names = _group_name_lookup()
    items = [_serialize_result(result, report_title=report_title, group_names=group_names) for result in results]
    kpis, rules = _flatten_batch_records(results)
    profiles = sorted({str(item.get("analysis_profile", "default")) for item in items})
    generated_at = max((str(item.get("generated_at", "")) for item in items), default="") or datetime.now().astimezone().isoformat(timespec="seconds")
    report_summary = f"共分析 {len(results)} 个文件，输出 {len(kpis)} 条 KPI 结果。"
    return {
        "report_title": report_title,
        "generated_at": generated_at,
        "analysis_profile": ", ".join(profiles),
        "source_path": "多文件汇总报告",
        "source_name": "",
        "source_stem": "",
        "report_summary": report_summary,
        "mapped_columns": {},
        "metadata": {
            "analysis_profiles": profiles,
            "file_count": len(results),
            "config_paths": sorted({str(item["metadata"].get("config_path")) for item in items if item["metadata"].get("config_path")}),
            "group_keys": sorted({str(item["metadata"].get("kpi_group_key", "__all_kpis__")) for item in items}),
        },
        "kpis": kpis,
        "rules": rules,
        "results": items,
        "files": items,
        "file_count": len(results),
    }


def batch_report_filename(report_title: str) -> str:
    stem = re.sub(r"[^a-zA-Z0-9_\-\u4e00-\u9fff]+", "_", report_title.strip()).strip("_")
    return f"{stem or 'tcs_batch_report'}_summary.html"


def batch_word_filename(report_title: str) -> str:
    stem = re.sub(r"[^a-zA-Z0-9_\-\u4e00-\u9fff]+", "_", report_title.strip()).strip("_")
    return f"{stem or 'tcs_batch_report'}_summary.docx"


def export_excel(result: AnalysisResult, output_path: str | Path) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    kpi_frame = pd.DataFrame(
        [
            {
                "name": item.name,
                "title": item.title,
                "value": item.value,
                "unit": item.unit,
                "description": item.description,
                "rule_description": item.rule_description,
                "status": item.status,
                "assessment_message": item.assessment_message,
                "threshold_value": item.threshold_value,
                "threshold_source": item.threshold_source,
                "pass_condition": item.pass_condition,
                "result_label": item.result_label,
            }
            for item in result.kpis
        ]
    )
    rule_frame = pd.DataFrame(
        [
            {
                "rule_id": item.rule_id,
                "category": item.category,
                "title": item.title,
                "status": item.status,
                "severity": item.severity,
                "measured_value": item.measured_value,
                "threshold_value": item.threshold_value,
                "unit": item.unit,
                "message": item.message,
                "threshold_source": item.threshold_source,
                "confidence": item.confidence,
            }
            for item in result.rule_results
        ]
    )

    with pd.ExcelWriter(output) as writer:
        kpi_frame.to_excel(writer, sheet_name="kpis", index=False)
        rule_frame.to_excel(writer, sheet_name="rules", index=False)
        result.normalized_frame.to_excel(writer, sheet_name="normalized_data", index=False)
        _auto_fit_writer_sheets(writer)

    return output


def export_html(
    result: AnalysisResult | list[AnalysisResult],
    output_path: str | Path,
    template_path: str | Path | None = None,
    report_title: str = "TCS 打滑控制自动分析报告",
) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    template = DEFAULT_HTML_TEMPLATE
    if template_path is not None:
        template = Template(Path(template_path).read_text(encoding="utf-8"))

    if isinstance(result, list):
        context = build_batch_report_context(result, report_title=report_title)
    else:
        context = build_report_context(result, report_title=report_title)
    html = template.render(**context)
    output.write_text(html, encoding="utf-8")
    return output


def export_word(
    result: AnalysisResult | list[AnalysisResult],
    output_path: str | Path,
    report_title: str = "TCS 打滑控制自动分析报告",
) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    context = build_batch_report_context(result, report_title=report_title) if isinstance(result, list) else build_report_context(result, report_title=report_title)
    document = Document()
    normal_style = document.styles["Normal"]
    _apply_style_font(normal_style)

    title = document.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run(report_title)
    _apply_run_style(run, size=20, bold=True, color=RGBColor(12, 74, 110))

    meta_table = document.add_table(rows=2, cols=2)
    meta_table.style = "Table Grid"
    meta_pairs = [
        ("汇总文件数", str(context.get("file_count", 0))),
        ("分析配置", str(context.get("analysis_profile", "default"))),
        ("分析摘要", str(context.get("report_summary", ""))),
        ("生成时间", str(context.get("generated_at", ""))),
    ]
    for index, (label, value) in enumerate(meta_pairs):
        row = index // 2
        col = (index % 2) * 1
        cell = meta_table.cell(row, col)
        cell.text = f"{label}: {value}"
        _set_cell_shading(cell, "E7F4FF")
        _style_cell_paragraphs(cell, size=10.5, bold=False)

    document.add_paragraph("")
    for result_item in context.get("results", []):
        group_paragraph = document.add_paragraph()
        group_run = group_paragraph.add_run(str(result_item.get("group_name", "")))
        _apply_run_style(group_run, size=13, bold=True, color=RGBColor(12, 74, 110))

        file_paragraph = document.add_paragraph()
        file_run = file_paragraph.add_run(str(result_item.get("source_name", "")))
        _apply_run_style(file_run, size=11.5, bold=True)
        count_run = file_paragraph.add_run(f"    KPI 项数: {result_item.get('kpi_count', 0)}")
        _apply_run_style(count_run, size=11.5, bold=True)

        table = document.add_table(rows=1, cols=6)
        table.style = "Table Grid"
        table.autofit = True
        headers = ["KPI", "描述", "单位", "数值", "达标要求", "结果"]
        for index, header in enumerate(headers):
            cell = table.rows[0].cells[index]
            cell.text = header
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            _set_cell_shading(cell, "D8EEFC")
            _style_cell_paragraphs(cell, size=10.5, bold=True)
        for item in result_item.get("kpis", []):
            row = table.add_row().cells
            row[0].text = str(item.get("title", ""))
            row[1].text = str(item.get("description", ""))
            row[2].text = str(item.get("unit", ""))
            row[3].text = str(item.get("value_text", "-"))
            row[4].text = str(item.get("rule_description", ""))
            row[5].text = str(item.get("result_label", ""))
            status = str(item.get("status", "pass"))
            if status == "pass":
                _set_cell_shading(row[5], "ECFDF5")
            elif status == "warning":
                _set_cell_shading(row[5], "FFF7ED")
            else:
                _set_cell_shading(row[5], "FFF1F2")
            for cell in row:
                _style_cell_paragraphs(cell, size=10.5, bold=False)
        document.add_paragraph("")

    document.save(output)
    return output


def export_json_summary(result: AnalysisResult, output_path: str | Path) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    time_start = None
    time_end = None
    if not result.normalized_frame.empty and "time_s" in result.normalized_frame.columns:
        time_start = float(result.normalized_frame["time_s"].min())
        time_end = float(result.normalized_frame["time_s"].max())

    payload = {
        "source_path": str(result.context.source_path),
        "generated_at": result.context.metadata.get("generated_at"),
        "analyzer_version": result.context.metadata.get("analyzer_version"),
        "analysis_profile": result.context.metadata.get("analysis_profile", "default"),
        "config_path": result.context.metadata.get("config_path"),
        "settings_metadata": result.context.metadata.get("settings_metadata", {}),
        "mapped_columns": result.context.mapped_columns,
        "rule_settings": result.context.metadata.get("rule_settings", {}),
        "data_overview": {
            "row_count": int(len(result.normalized_frame)),
            "time_start_s": time_start,
            "time_end_s": time_end,
        },
        "kpis": [
            {
                "name": item.name,
                "value": item.value,
                "unit": item.unit,
                "description": item.description,
            }
            for item in result.kpis
        ],
        "rules": [
            {
                "rule_id": item.rule_id,
                "category": item.category,
                "title": item.title,
                "status": item.status,
                "severity": item.severity,
                "measured_value": item.measured_value,
                "threshold_value": item.threshold_value,
                "unit": item.unit,
                "message": item.message,
                "threshold_source": item.threshold_source,
                "confidence": item.confidence,
            }
            for item in result.rule_results
        ],
    }

    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output
