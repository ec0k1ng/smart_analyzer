$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$pythonExe = "C:/Python312/python.exe"
& $pythonExe (Join-Path $projectRoot "scripts/packaging/build_installer.py")