from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from docx import Document

from tcs_smart_analyzer.core.engine import AnalysisEngine
from tcs_smart_analyzer.reporting.exporters import build_batch_report_context, build_report_context, export_html, export_json_summary, export_word


class ExporterTests(unittest.TestCase):
    def test_json_summary_contains_traceability_metadata(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        demo_file = project_root / "sample_data" / "tcs_demo.csv"

        engine = AnalysisEngine()
        result = engine.analyze_file(demo_file)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "summary.json"
            export_json_summary(result, output_path)
            payload = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(payload["source_path"], str(demo_file))
        self.assertEqual(payload["analysis_profile"], "default")
        self.assertIn("rule_settings", payload)
        self.assertGreaterEqual(len(payload["rules"]), 4)
        self.assertGreater(payload["data_overview"]["row_count"], 0)
        self.assertNotIn("scenarios", payload)

    def test_html_export_accepts_custom_template(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        demo_file = project_root / "sample_data" / "tcs_demo.csv"

        engine = AnalysisEngine()
        result = engine.analyze_file(demo_file)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            template_path = temp_path / "custom_template.html"
            output_path = temp_path / "report.html"
            template_path.write_text("<html><body><h1>{{ report_title }}</h1><p>{{ source_path }}</p></body></html>", encoding="utf-8")

            export_html(result, output_path, template_path=template_path, report_title="自定义模板报告")
            content = output_path.read_text(encoding="utf-8")

        self.assertIn("自定义模板报告", content)
        self.assertIn(str(demo_file), content)

    def test_report_context_exposes_file_name_variables(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        demo_file = project_root / "sample_data" / "tcs_demo.csv"

        engine = AnalysisEngine()
        result = engine.analyze_file(demo_file)
        context = build_report_context(result)

        self.assertEqual(context["source_path"], str(demo_file))
        self.assertEqual(context["source_name"], demo_file.name)
        self.assertEqual(context["source_stem"], demo_file.stem)
        self.assertEqual(context["file_count"], 1)
        self.assertEqual(context["results"][0]["group_name"], "默认组（全部 KPI）")
        self.assertIn("report_summary", context)
        self.assertIn("value_text", context["results"][0]["kpis"][0])

    def test_batch_report_context_flattens_multiple_results(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        demo_file = project_root / "sample_data" / "tcs_demo.csv"

        engine = AnalysisEngine()
        first = engine.analyze_file(demo_file)
        second = engine.analyze_file(demo_file)
        context = build_batch_report_context([first, second])

        self.assertEqual(context["file_count"], 2)
        self.assertEqual(len(context["results"]), 2)
        self.assertGreaterEqual(len(context["kpis"]), len(first.kpis) * 2)
        self.assertIn("group_name", context["kpis"][0])

    def test_word_export_matches_report_structure(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        demo_file = project_root / "sample_data" / "tcs_demo.csv"

        engine = AnalysisEngine()
        result = engine.analyze_file(demo_file)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "report.docx"
            export_word(result, output_path, report_title="Word 报告")
            document = Document(output_path)

        text = "\n".join(paragraph.text for paragraph in document.paragraphs)
        self.assertIn("Word 报告", text)
        self.assertIn(demo_file.name, text)
        self.assertGreaterEqual(len(document.tables), 2)

    def test_word_export_keeps_file_heading_run_style_consistent(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        demo_file = project_root / "sample_data" / "tcs_demo.csv"

        engine = AnalysisEngine()
        result = engine.analyze_file(demo_file)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "report.docx"
            export_word(result, output_path, report_title="Word 报告")
            document = Document(output_path)

        target_paragraph = next(paragraph for paragraph in document.paragraphs if "KPI 项数" in paragraph.text)
        self.assertGreaterEqual(len(target_paragraph.runs), 2)
        font_names = {run.font.name for run in target_paragraph.runs}
        font_sizes = {None if run.font.size is None else round(run.font.size.pt, 1) for run in target_paragraph.runs}
        bold_values = {run.bold for run in target_paragraph.runs}

        self.assertEqual(font_names, {"Microsoft YaHei"})
        self.assertEqual(font_sizes, {11.5})
        self.assertEqual(bold_values, {True})


if __name__ == "__main__":
    unittest.main()