from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


APP_NAME = "自动化数据分析工具"
PYTHON_PACKAGE_VERSION_FILE = Path("src") / "tcs_smart_analyzer" / "__init__.py"
MAIN_FILE = Path("src") / "tcs_smart_analyzer" / "main.py"
CONFIG_DIR = Path("src") / "tcs_smart_analyzer" / "config"
RELEASE_DIR = Path("installer_release")
TEMP_ROOT = Path(".build_installer")
APP_DIST = TEMP_ROOT / "app_dist"
APP_WORK = TEMP_ROOT / "app_work"
APP_SPEC = TEMP_ROOT / "app_spec"
INSTALLER_WORK = TEMP_ROOT / "installer_work"
INSTALLER_SPEC = TEMP_ROOT / "installer_spec"
PAYLOAD_ZIP = TEMP_ROOT / "app_payload.zip"


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read_version(project_root: Path) -> tuple[str, str]:
    version_text = (project_root / PYTHON_PACKAGE_VERSION_FILE).read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*"(?P<version>[0-9]+\.[0-9]+\.[0-9]+)"', version_text)
    if match is None:
        raise RuntimeError("Failed to parse version from src/tcs_smart_analyzer/__init__.py")
    package_version = str(match.group("version"))
    version_parts = package_version.split(".")
    display_version = f"V{version_parts[0]}.{version_parts[1]}"
    return package_version, display_version


def _zip_directory_contents(source_dir: Path, target_zip: Path) -> None:
    with zipfile.ZipFile(target_zip, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
        for path in sorted(source_dir.rglob("*")):
            if path.is_dir():
                continue
            zip_file.write(path, path.relative_to(source_dir))


def _run(command: list[str], project_root: Path) -> None:
    subprocess.run(command, cwd=project_root, check=True)


def main() -> int:
    project_root = _project_root()
    _package_version, display_version = _read_version(project_root)
    installer_name = f"{APP_NAME}安装程序 {display_version}"

    if (project_root / TEMP_ROOT).exists():
        shutil.rmtree(project_root / TEMP_ROOT)
    (project_root / TEMP_ROOT).mkdir(parents=True, exist_ok=True)
    (project_root / RELEASE_DIR).mkdir(parents=True, exist_ok=True)
    for path in (project_root / RELEASE_DIR).iterdir():
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()

    python_exe = sys.executable
    data_separator = os.pathsep
    config_data = f"{project_root / CONFIG_DIR}{data_separator}tcs_smart_analyzer/config"

    _run(
        [
            python_exe,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--windowed",
            "--onedir",
            "--name",
            APP_NAME,
            "--distpath",
            str(project_root / APP_DIST),
            "--workpath",
            str(project_root / APP_WORK),
            "--specpath",
            str(project_root / APP_SPEC),
            "--paths",
            str(project_root / "src"),
            "--collect-data",
            "tcs_smart_analyzer",
            "--add-data",
            config_data,
            str(project_root / MAIN_FILE),
        ],
        project_root,
    )

    app_bundle_dir = project_root / APP_DIST / APP_NAME
    if not app_bundle_dir.exists():
        raise RuntimeError(f"Application bundle was not created: {app_bundle_dir}")

    _zip_directory_contents(app_bundle_dir, project_root / PAYLOAD_ZIP)

    _run(
        [
            python_exe,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--windowed",
            "--onefile",
            "--name",
            installer_name,
            "--distpath",
            str(project_root / RELEASE_DIR),
            "--workpath",
            str(project_root / INSTALLER_WORK),
            "--specpath",
            str(project_root / INSTALLER_SPEC),
            "--add-data",
            f"{project_root / PAYLOAD_ZIP}{data_separator}payload",
            str(project_root / "scripts" / "packaging" / "installer_bootstrap.py"),
        ],
        project_root,
    )

    installer_exe = project_root / RELEASE_DIR / f"{installer_name}.exe"
    if not installer_exe.exists():
        raise RuntimeError(f"Installer executable was not created: {installer_exe}")

    if (project_root / TEMP_ROOT).exists():
        shutil.rmtree(project_root / TEMP_ROOT)

    print(f"Installer created: {installer_exe}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())