from __future__ import annotations

import os
import subprocess
import sys
import zipfile
from pathlib import Path
from tkinter import BooleanVar, StringVar, Tk, filedialog, ttk


APP_NAME = "自动化数据分析工具"
APP_VERSION = "V1.2"
APP_EXE_NAME = f"{APP_NAME}.exe"
PAYLOAD_ZIP_NAME = "app_payload.zip"
DEFAULT_INSTALL_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Programs" / APP_NAME
START_MENU_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
WIZARD_STEPS = ["欢迎", "安装选项", "安装过程"]


def _bundle_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parent


def _payload_zip_path() -> Path:
    return _bundle_dir() / "payload" / PAYLOAD_ZIP_NAME


def _create_shortcut(target_path: Path, shortcut_path: Path) -> None:
    shortcut_path.parent.mkdir(parents=True, exist_ok=True)
    ps_script = (
        "$ws = New-Object -ComObject WScript.Shell;"
        f'$shortcut = $ws.CreateShortcut("{str(shortcut_path).replace("\\", "\\\\")}");'
        f'$shortcut.TargetPath = "{str(target_path).replace("\\", "\\\\")}";'
        f'$shortcut.WorkingDirectory = "{str(target_path.parent).replace("\\", "\\\\")}";'
        f'$shortcut.IconLocation = "{str(target_path).replace("\\", "\\\\")},0";'
        "$shortcut.Save()"
    )
    startupinfo = None
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    if hasattr(subprocess, "STARTUPINFO"):
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= getattr(subprocess, "STARTF_USESHOWWINDOW", 0)
        startupinfo.wShowWindow = 0
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-Command", ps_script],
        check=True,
        capture_output=True,
        text=True,
        startupinfo=startupinfo,
        creationflags=creationflags,
    )


class InstallerApp:
    def __init__(self) -> None:
        self.root = Tk()
        self.root.title(f"{APP_NAME} 安装程序")
        self.root.geometry("920x560")
        self.root.minsize(920, 560)
        self.root.resizable(False, False)
        self.root.configure(bg="#f0f4fa")

        self.install_dir_var = StringVar(value=str(DEFAULT_INSTALL_DIR))
        self.desktop_shortcut_var = BooleanVar(value=True)
        self.start_menu_shortcut_var = BooleanVar(value=True)
        self.launch_after_install_var = BooleanVar(value=False)
        self.status_var = StringVar(value="准备安装")
        self.detail_var = StringVar(value="选择安装位置后点击开始安装。整个安装过程会在当前窗口中完成。")
        self.step_var = StringVar(value="步骤 1/3 · 欢迎")
        self._installing = False
        self._install_finished = False
        self._installed_target_exe: Path | None = None
        self._current_page = "welcome"
        self._wizard_pages: dict[str, ttk.Frame] = {}

        self._configure_styles()
        self._build_ui()

    def _configure_styles(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Shell.TFrame", background="#f0f4fa")
        style.configure("Hero.TFrame", background="#0f2b44")
        style.configure("Panel.TFrame", background="#ffffff")
        style.configure("Card.TFrame", background="#f6f9fd", relief="flat")
        style.configure("HeroTitle.TLabel", background="#0f2b44", foreground="#ffffff", font=("Microsoft YaHei UI", 22, "bold"))
        style.configure("HeroVersion.TLabel", background="#0f2b44", foreground="#60a5fa", font=("Microsoft YaHei UI", 11, "bold"))
        style.configure("HeroBody.TLabel", background="#0f2b44", foreground="#b8d4ee", font=("Microsoft YaHei UI", 10))
        style.configure("PanelTitle.TLabel", background="#ffffff", foreground="#0f2740", font=("Microsoft YaHei UI", 18, "bold"))
        style.configure("Body.TLabel", background="#ffffff", foreground="#456179", font=("Microsoft YaHei UI", 10))
        style.configure("CardTitle.TLabel", background="#f6f9fd", foreground="#16324a", font=("Microsoft YaHei UI", 11, "bold"))
        style.configure("CardBody.TLabel", background="#f6f9fd", foreground="#5c7287", font=("Microsoft YaHei UI", 9))
        style.configure("StepInactive.TLabel", background="#0f2b44", foreground="#6b97b8", font=("Microsoft YaHei UI", 10), padding=(14, 10))
        style.configure("StepActive.TLabel", background="#1a4971", foreground="#ffffff", font=("Microsoft YaHei UI", 10, "bold"), padding=(14, 10))
        style.configure("StepDone.TLabel", background="#0f2b44", foreground="#34d399", font=("Microsoft YaHei UI", 10), padding=(14, 10))
        style.configure("Accent.TButton", background="#2563eb", foreground="#ffffff", borderwidth=0, font=("Microsoft YaHei UI", 10, "bold"), padding=(20, 12))
        style.map("Accent.TButton", background=[("active", "#1d4ed8"), ("pressed", "#1e40af")], foreground=[("disabled", "#93c5fd")])
        style.configure("Soft.TButton", background="#f0f4fa", foreground="#1e3a5f", bordercolor="#c5d3e3", lightcolor="#f0f4fa", darkcolor="#f0f4fa", font=("Microsoft YaHei UI", 10), padding=(16, 11))
        style.map("Soft.TButton", background=[("active", "#e2ecf7")])
        style.configure("TCheckbutton", background="#f6f9fd", foreground="#314a60", font=("Microsoft YaHei UI", 9))
        style.configure("TEntry", fieldbackground="#ffffff", bordercolor="#c5d3e3", padding=8, font=("Microsoft YaHei UI", 10))
        style.configure("Modern.Horizontal.TProgressbar", troughcolor="#e2ecf7", background="#2563eb", bordercolor="#e2ecf7", lightcolor="#3b82f6", darkcolor="#1d4ed8")

    def _build_ui(self) -> None:
        shell = ttk.Frame(self.root, padding=18, style="Shell.TFrame")
        shell.pack(fill="both", expand=True)

        hero = ttk.Frame(shell, width=280, padding=(28, 34), style="Hero.TFrame")
        hero.pack(side="left", fill="y")
        hero.pack_propagate(False)

        ttk.Label(hero, text=APP_NAME, style="HeroTitle.TLabel", wraplength=210).pack(anchor="w")
        ttk.Label(hero, text=f"v{APP_VERSION}", style="HeroVersion.TLabel").pack(anchor="w", pady=(4, 0))
        ttk.Label(
            hero,
            text="完整安装包，包含主程序、KPI、派生量、模板和接口映射等运行资源。",
            style="HeroBody.TLabel",
            wraplength=210,
            justify="left",
        ).pack(anchor="w", pady=(14, 24))

        highlights = [
            "完整释放应用目录，无需手工补配置文件",
            "支持自定义安装目录",
            "可选创建桌面与开始菜单快捷方式",
        ]
        for item in highlights:
            ttk.Label(hero, text=f"• {item}", style="HeroBody.TLabel", wraplength=210, justify="left").pack(anchor="w", pady=4)

        ttk.Label(hero, textvariable=self.step_var, style="HeroBody.TLabel", wraplength=210, justify="left").pack(anchor="w", pady=(22, 10))

        self.step_labels: list[ttk.Label] = []
        step_tracker = ttk.Frame(hero, style="Hero.TFrame")
        step_tracker.pack(anchor="w", fill="x")
        for index, step_name in enumerate(WIZARD_STEPS, start=1):
            label = ttk.Label(step_tracker, text=f"{index}. {step_name}", style="StepInactive.TLabel", anchor="w")
            label.pack(fill="x", pady=4)
            self.step_labels.append(label)

        content = ttk.Frame(shell, padding=(24, 22), style="Panel.TFrame")
        content.pack(side="left", fill="both", expand=True)
        content.columnconfigure(0, weight=1)
        content.rowconfigure(0, weight=1)

        self.content_body = ttk.Frame(content, style="Panel.TFrame")
        self.content_body.grid(row=0, column=0, sticky="nsew")
        self.content_body.columnconfigure(0, weight=1)
        self.content_body.rowconfigure(0, weight=1)

        self._wizard_pages["welcome"] = self._build_welcome_page(self.content_body)
        self._wizard_pages["options"] = self._build_options_page(self.content_body)
        self._wizard_pages["progress"] = self._build_progress_page(self.content_body)
        for page in self._wizard_pages.values():
            page.grid(row=0, column=0, sticky="nsew")
        self._show_page("welcome")

        action_bar = ttk.Frame(content, padding=(0, 16, 0, 0), style="Panel.TFrame")
        action_bar.grid(row=1, column=0, sticky="ew")
        action_bar.columnconfigure(0, weight=1)

        self.action_hint = ttk.Label(action_bar, text="点击“下一步”继续。", style="Body.TLabel")
        self.action_hint.grid(row=0, column=0, sticky="w")

        button_bar = ttk.Frame(action_bar, style="Panel.TFrame")
        button_bar.grid(row=0, column=1, sticky="e")
        self.back_button = ttk.Button(button_bar, text="上一步", command=self._go_back, style="Soft.TButton")
        self.back_button.pack(side="right", padx=(0, 10))
        self.cancel_button = ttk.Button(button_bar, text="取消", command=self.root.destroy, style="Soft.TButton")
        self.cancel_button.pack(side="right")
        self.install_button = ttk.Button(button_bar, text="下一步", command=self._go_next, style="Accent.TButton")
        self.install_button.pack(side="right", padx=(0, 10))
        self.install_button.focus_set()
        self.back_button.state(["disabled"])

    def _build_welcome_page(self, parent) -> ttk.Frame:  # noqa: ANN001
        page = ttk.Frame(parent, style="Panel.TFrame")
        page.columnconfigure(0, weight=1)
        hero_card = ttk.Frame(page, padding=18, style="Card.TFrame")
        hero_card.grid(row=0, column=0, sticky="ew")
        ttk.Label(hero_card, text="欢迎使用自动化数据分析工具安装向导", style="PanelTitle.TLabel").pack(anchor="w")
        ttk.Label(
            hero_card,
            text="该向导会分步完成安装配置、目录选择与快捷方式创建。整个过程在当前窗口中展示，不会额外弹出安装确认框。",
            style="Body.TLabel",
            wraplength=540,
            justify="left",
        ).pack(anchor="w", pady=(8, 0))

        info_card = ttk.Frame(page, padding=18, style="Card.TFrame")
        info_card.grid(row=1, column=0, sticky="ew", pady=(14, 0))
        ttk.Label(info_card, text="本次安装将包含", style="CardTitle.TLabel").pack(anchor="w")
        for item in [
            "主程序与运行依赖",
            "KPI、派生量、报表模板和接口映射配置",
            "可选的桌面与开始菜单快捷方式",
        ]:
            ttk.Label(info_card, text=f"• {item}", style="CardBody.TLabel", wraplength=520, justify="left").pack(anchor="w", pady=3)
        return page

    def _build_options_page(self, parent) -> ttk.Frame:  # noqa: ANN001
        page = ttk.Frame(parent, style="Panel.TFrame")
        page.columnconfigure(0, weight=1)
        header_block = ttk.Frame(page, style="Panel.TFrame")
        header_block.grid(row=0, column=0, sticky="ew")
        ttk.Label(header_block, text="安装选项", style="PanelTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            header_block,
            text="选择安装路径与附加选项。确认后，下一步将直接进入安装过程。",
            style="Body.TLabel",
            wraplength=520,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(8, 18))

        path_card = ttk.Frame(page, padding=16, style="Card.TFrame")
        path_card.grid(row=1, column=0, sticky="ew")
        ttk.Label(path_card, text="安装位置", style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(path_card, text="建议安装到默认目录，或选择一个你有写入权限的位置。", style="CardBody.TLabel", wraplength=500).pack(anchor="w", pady=(4, 12))
        path_row = ttk.Frame(path_card, style="Card.TFrame")
        path_row.pack(fill="x")
        ttk.Entry(path_row, textvariable=self.install_dir_var).pack(side="left", fill="x", expand=True, padx=(0, 10))
        ttk.Button(path_row, text="浏览目录", command=self._browse_install_dir, style="Soft.TButton").pack(side="left")

        option_card = ttk.Frame(page, padding=16, style="Card.TFrame")
        option_card.grid(row=2, column=0, sticky="ew", pady=(14, 0))
        ttk.Label(option_card, text="附加选项", style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(option_card, text="你可以在安装完成后直接关闭向导，也可以自动启动程序。", style="CardBody.TLabel").pack(anchor="w", pady=(4, 10))
        ttk.Checkbutton(option_card, text="创建桌面快捷方式", variable=self.desktop_shortcut_var).pack(anchor="w", pady=2)
        ttk.Checkbutton(option_card, text="创建开始菜单快捷方式", variable=self.start_menu_shortcut_var).pack(anchor="w", pady=2)
        ttk.Checkbutton(option_card, text="安装完成后立即启动", variable=self.launch_after_install_var).pack(anchor="w", pady=2)
        return page

    def _build_progress_page(self, parent) -> ttk.Frame:  # noqa: ANN001
        page = ttk.Frame(parent, style="Panel.TFrame")
        page.columnconfigure(0, weight=1)
        ttk.Label(page, text="安装过程", style="PanelTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            page,
            text="安装向导会在当前页面展示文件释放、快捷方式创建和完成状态。",
            style="Body.TLabel",
            wraplength=520,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(8, 18))

        status_card = ttk.Frame(page, padding=16, style="Card.TFrame")
        status_card.grid(row=2, column=0, sticky="ew")
        ttk.Label(status_card, text="安装进度", style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(status_card, textvariable=self.status_var, style="CardBody.TLabel", wraplength=500).pack(anchor="w", pady=(4, 4))
        ttk.Label(status_card, textvariable=self.detail_var, style="CardBody.TLabel", wraplength=500, justify="left").pack(anchor="w", pady=(0, 10))
        self.progress = ttk.Progressbar(status_card, mode="determinate", maximum=100, value=0, style="Modern.Horizontal.TProgressbar")
        self.progress.pack(fill="x")
        return page

    def _show_page(self, page_name: str) -> None:
        self._current_page = page_name
        self._wizard_pages[page_name].tkraise()
        step_index = {"welcome": 0, "options": 1, "progress": 2}[page_name]
        self.step_var.set(f"步骤 {step_index + 1}/3 · {WIZARD_STEPS[step_index]}")
        self._refresh_step_indicator(step_index)
        if hasattr(self, "back_button"):
            self.back_button.state(["disabled"] if page_name == "welcome" or self._installing else ["!disabled"])
        if page_name == "welcome":
            if hasattr(self, "action_hint"):
                self.action_hint.configure(text="点击“下一步”继续。")
            if hasattr(self, "install_button"):
                self.install_button.configure(text="下一步", command=self._go_next)
        elif page_name == "options":
            if hasattr(self, "action_hint"):
                self.action_hint.configure(text="确认安装目录与选项后，点击“开始安装”。")
            if hasattr(self, "install_button"):
                self.install_button.configure(text="开始安装", command=self._go_next)
        else:
            if hasattr(self, "action_hint"):
                self.action_hint.configure(text="安装过程中请保持当前窗口打开。")
            if not self._install_finished and hasattr(self, "install_button"):
                self.install_button.configure(text="正在安装", command=self._go_next)

    def _refresh_step_indicator(self, active_index: int) -> None:
        for index, label in enumerate(getattr(self, "step_labels", [])):
            if index < active_index:
                label.configure(style="StepDone.TLabel", text=f"✓ {WIZARD_STEPS[index]}")
            elif index == active_index:
                label.configure(style="StepActive.TLabel", text=f"{index + 1}. {WIZARD_STEPS[index]}")
            else:
                label.configure(style="StepInactive.TLabel", text=f"{index + 1}. {WIZARD_STEPS[index]}")

    def _go_back(self) -> None:
        if self._installing:
            return
        if self._current_page == "options":
            self._show_page("welcome")
        elif self._current_page == "progress" and self._install_finished:
            self._show_page("options")

    def _go_next(self) -> None:
        if self._current_page == "welcome":
            self._show_page("options")
            return
        if self._current_page == "options":
            self._show_page("progress")
            self._install()
            return
        if self._current_page == "progress" and self._install_finished:
            self._finish_installation()

    def _set_status(self, title: str, detail: str, *, progress: int | None = None) -> None:
        self.status_var.set(title)
        self.detail_var.set(detail)
        if progress is not None:
            self.progress.configure(value=max(0, min(progress, 100)))
        self.root.update_idletasks()

    def _set_install_controls_enabled(self, enabled: bool) -> None:
        state = ["!disabled"] if enabled else ["disabled"]
        self.install_button.state(state)
        self.cancel_button.state(state)
        self.back_button.state(state if enabled and self._current_page != "welcome" else ["disabled"])

    def _finish_installation(self) -> None:
        if self.launch_after_install_var.get() and self._installed_target_exe is not None and self._installed_target_exe.exists():
            subprocess.Popen([str(self._installed_target_exe)], cwd=str(self._installed_target_exe.parent))
        self.root.destroy()

    def _prepare_install_completion(self, install_dir: Path, target_exe: Path) -> None:
        self._installing = False
        self._install_finished = True
        self._installed_target_exe = target_exe
        self._set_install_controls_enabled(True)
        self.cancel_button.configure(text="关闭")
        self.install_button.configure(text="完成", command=self._finish_installation)
        self.back_button.state(["disabled"])
        self._set_status(
            "安装完成",
            f"{APP_NAME} 已安装到：{install_dir}\n你可以点击“完成”关闭安装器。"
            + (" 程序将在关闭时自动启动。" if self.launch_after_install_var.get() else ""),
            progress=100,
        )

    def _extract_payload(self, payload_zip: Path, install_dir: Path) -> None:
        with zipfile.ZipFile(payload_zip, "r") as zip_file:
            members = [member for member in zip_file.infolist() if not member.is_dir()]
            total_bytes = sum(max(member.file_size, 1) for member in members) or 1
            extracted_bytes = 0
            if not members:
                self._set_status("正在准备安装文件", "安装包中未检测到需要释放的文件。", progress=25)
                return
            for index, member in enumerate(members, start=1):
                zip_file.extract(member, install_dir)
                extracted_bytes += max(member.file_size, 1)
                progress = 10 + int(extracted_bytes / total_bytes * 75)
                self._set_status(
                    "正在复制程序文件",
                    f"正在释放安装内容：{index}/{len(members)}\n当前文件：{member.filename}",
                    progress=progress,
                )

    def _create_selected_shortcuts(self, target_exe: Path) -> None:
        if self.start_menu_shortcut_var.get():
            self._set_status("正在创建快捷方式", "正在创建开始菜单快捷方式。", progress=90)
            _create_shortcut(target_exe, START_MENU_DIR / f"{APP_NAME}.lnk")
        if self.desktop_shortcut_var.get():
            desktop_dir = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"
            if desktop_dir.exists():
                self._set_status("正在创建快捷方式", "正在创建桌面快捷方式。", progress=96)
                _create_shortcut(target_exe, desktop_dir / f"{APP_NAME}.lnk")

    def _browse_install_dir(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.install_dir_var.get() or str(DEFAULT_INSTALL_DIR))
        if selected:
            self.install_dir_var.set(selected)

    def _install(self) -> None:
        if self._install_finished:
            self._finish_installation()
            return
        if self._installing:
            return
        install_dir = Path(self.install_dir_var.get().strip())
        if not str(install_dir):
            self._set_status("安装目录未填写", "请先选择安装目录，再开始安装。", progress=0)
            return

        payload_zip = _payload_zip_path()
        if not payload_zip.exists():
            self._set_status("安装失败", f"安装包内容不完整，缺少 {PAYLOAD_ZIP_NAME}。", progress=0)
            return

        self._installing = True
        self._set_install_controls_enabled(False)
        self.install_button.configure(text="正在安装")

        try:
            self._set_status("正在准备安装", f"目标目录：{install_dir}", progress=2)
            install_dir.mkdir(parents=True, exist_ok=True)
            target_exe = install_dir / APP_EXE_NAME
            if target_exe.exists():
                self._set_status("正在更新已有安装", f"检测到现有安装目录，正在覆盖更新：{install_dir}", progress=6)
            self._extract_payload(payload_zip, install_dir)
            self._create_selected_shortcuts(target_exe)
        except Exception as exc:  # noqa: BLE001
            self._installing = False
            self._set_install_controls_enabled(True)
            self._set_status("安装失败", str(exc), progress=0)
            return

        self._prepare_install_completion(install_dir, target_exe)

    def run(self) -> int:
        self.root.mainloop()
        return 0


def main() -> int:
    return InstallerApp().run()


if __name__ == "__main__":
    raise SystemExit(main())