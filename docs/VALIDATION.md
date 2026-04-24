# TCS Smart Analyzer 验证说明

## 1. 当前环境事实

- 当前验证解释器：c:/Users/Ecoking/Desktop/smart_analyzer/smart_analyzer/.venv/Scripts/python.exe
- 当前最常用安装命令：

```powershell
python -m pip install -e .
python -m pip install -e .[gui]
```

## 2. 当前应执行的验证命令

### 2.1 聚焦回归

```powershell
c:/Users/Ecoking/Desktop/smart_analyzer/smart_analyzer/.venv/Scripts/python.exe -m pytest tests/test_loaders.py tests/test_engine_pipeline.py
```

### 2.2 GUI 离屏冒烟

```powershell
c:/Users/Ecoking/Desktop/smart_analyzer/smart_analyzer/.venv/Scripts/python.exe scripts/gui_smoke_check.py
```

### 2.3 UI/核心语法检查

```powershell
c:/Users/Ecoking/Desktop/smart_analyzer/smart_analyzer/.venv/Scripts/python.exe -m py_compile src/tcs_smart_analyzer/ui/main_window.py src/tcs_smart_analyzer/core/engine.py src/tcs_smart_analyzer/data/loaders.py src/tcs_smart_analyzer/core/signal_mapping.py
```

### 2.4 完整基线（需要时再刷新）

```powershell
C:/Python312/python.exe -m unittest discover -s tests -v
```

说明：

- 该命令当前保留为历史完整基线入口，但本轮没有重新执行，不应把旧统计继续写成“当前事实”。

### 2.5 CLI 样例验证

```powershell
C:/Python312/python.exe -m tcs_smart_analyzer.cli --input .\sample_data\tcs_demo.csv --output-dir .\outputs
```

### 2.6 安装程序构建

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_installer.ps1
```

说明：
仅当用户明确要求发布安装程序时执行该命令。

## 3. 当前真实验证结果

### 3.1 聚焦回归

本轮实际执行结果：

- pytest tests/test_loaders.py tests/test_engine_pipeline.py：18 项全部通过
- scripts/gui_smoke_check.py：13 项探针全部通过
- py_compile：main_window.py、engine.py、loaders.py、signal_mapping.py 通过

当前 GUI 冒烟已覆盖并通过的重点项包括：

- chart_scope_deduped
- x_synced
- chart_plot_area_full_enough
- mapping_highlight_realtime

### 3.2 本轮未重新执行

- 本轮没有重新执行完整 unittest/pytest 全量基线。
- 本轮没有重新执行 CLI 导出冒烟。
- 本轮没有重新执行真实 BLF/MF4 样本验证。
- 本轮仅在明确发布安装程序时，才需要验证安装程序可生成并落入 installer_release/。

## 4. 当前人工检查口径

如果你在后续开发中重新跑 GUI 或 CLI，请至少核对：

- GUI 主页可正常入队、分组分析和查看运行日志。
- 接口映射页缺参时会实时标红，并阻止分析。
- 曲线页支持多面板、多选拖拽和跨面板转移。
- 分析在非曲线页完成后，切到曲线页时首个子图不应出现大面积空白区。
- KPI/派生量编辑器能高亮关键配置行和 CALIBRATION。
- HTML 与 Word 报告结构一致。
- 报告内容与结果页的分组/文件/KPI 组织一致。

## 5. 当前验证结论的使用方式

- 如果你要继续做文档或轻量代码整理，可以接受当前状态继续推进。
- 如果你要继续做功能开发，建议先把测试基线修回与当前实现一致，再做新增功能。
