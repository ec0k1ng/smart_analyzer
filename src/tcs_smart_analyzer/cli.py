from __future__ import annotations

import argparse
from pathlib import Path

from tcs_smart_analyzer.config.analysis_settings import load_analysis_settings
from tcs_smart_analyzer.core.engine import AnalysisEngine
from tcs_smart_analyzer.reporting.exporters import (
    batch_report_filename,
    export_html,
    batch_word_filename,
    export_word,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run TCS smart analysis on a file or folder.")
    parser.add_argument("--input", required=True, help="Input file path or folder path")
    parser.add_argument("--output-dir", default="outputs", help="Directory for generated reports")
    parser.add_argument("--config", help="Optional JSON analysis profile for rule thresholds and rule enablement")
    parser.add_argument("--html-template", help="Optional Jinja2 HTML report template path for export_html")
    parser.add_argument(
        "--exit-on",
        default="error",
        choices=["never", "error", "fail", "warning"],
        help="Control CLI exit code policy: error only, fail+error, warning+fail+error, or never",
    )
    parser.add_argument("--recursive", action="store_true", help="Recursively scan supported files when input is a folder")
    return parser


def resolve_exit_code(batch_rows: list[dict[str, object]], exit_on: str) -> int:
    statuses = {str(row.get("overall_status", "error")) for row in batch_rows}
    if exit_on == "never":
        return 0
    if "error" in statuses:
        return 2
    if exit_on == "fail" and "fail" in statuses:
        return 1
    if exit_on == "warning" and statuses.intersection({"warning", "fail"}):
        return 1
    return 0


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    settings = load_analysis_settings(args.config)
    engine = AnalysisEngine(settings=settings)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    input_path = Path(args.input)
    files = engine.collect_supported_files(input_path, recursive=args.recursive)
    if not files:
        raise SystemExit(f"未找到可分析文件: {input_path}")

    print(f"Analysis profile: {settings.profile_name}")
    if settings.config_path is not None:
        print(f"Config file: {settings.config_path}")

    results = []
    batch_rows: list[dict[str, object]] = []
    html_output_path = output_dir / batch_report_filename("TCS 打滑控制自动分析报告")
    word_output_path = output_dir / batch_word_filename("TCS 打滑控制自动分析报告")
    for file_path in files:
        try:
            result = engine.analyze_file(file_path)
            results.append(result)

            row = engine.summarize_analysis(result)
            row["html_report"] = str(html_output_path)
            row["word_report"] = str(word_output_path)
            batch_rows.append(row)

            print(f"Analysis complete: {file_path}")
            print(f"KPI assessments: {len(result.kpis)}")
        except Exception as exc:  # noqa: BLE001
            batch_rows.append(
                {
                    "file_name": file_path.name,
                    "file_path": str(file_path),
                    "overall_status": "error",
                    "analysis_profile": settings.profile_name,
                    "config_path": str(settings.config_path) if settings.config_path else None,
                    "rule_count": 0,
                    "pass_count": 0,
                    "warning_count": 0,
                    "fail_count": 0,
                    "max_slip_kph": 0.0,
                    "max_jerk_mps3": 0.0,
                    "error_message": str(exc),
                }
            )
            print(f"Analysis failed: {file_path}")
            print(f"Reason: {exc}")

    if results:
        html_path = export_html(results, html_output_path, template_path=args.html_template)
        word_path = export_word(results, word_output_path)
        print(f"HTML: {html_path}")
        print(f"Word: {word_path}")

    exit_code = resolve_exit_code(batch_rows, args.exit_on)
    if exit_code:
        raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
