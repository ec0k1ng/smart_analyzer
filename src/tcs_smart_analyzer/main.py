def main() -> None:
    try:
        from tcs_smart_analyzer.ui.main_window import launch_app
    except ImportError as exc:
        message = (
            "GUI 启动失败。"
            "如果缺少 GUI 依赖，请先执行: python -m pip install -e .[gui]\n"
            f"实际导入错误: {exc}"
        )
        raise SystemExit(message) from exc

    launch_app()


if __name__ == "__main__":
    main()
