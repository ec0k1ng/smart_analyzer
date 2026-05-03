# TCS Smart Analyzer 验证说明

## 1. 当前环境事实

- 当前验证解释器：c:/Users/Ecoking/Desktop/smart_analyzer/smart_analyzer/.venv/Scripts/python.exe
- 当前最常用安装命令：

```powershell
python -m pip install -e .
python -m pip install -e .[gui]
```

## 2. 当前应执行的验证命令

### 2.1 发布前聚焦回归

```powershell
c:/Users/Ecoking/Desktop/smart_analyzer/smart_analyzer/.venv/Scripts/python.exe -m pytest tests/test_signal_mapping.py tests/test_loaders.py tests/test_engine_pipeline.py tests/test_editable_configs.py tests/test_rule_settings.py tests/test_exporters.py
```

### 2.2 GUI 离屏冒烟

```powershell
$env:QT_QPA_PLATFORM='offscreen'; c:/Users/Ecoking/Desktop/smart_analyzer/smart_analyzer/.venv/Scripts/python.exe scripts/gui_smoke_check.py
```

### 2.3 UI/核心语法检查

```powershell
c:/Users/Ecoking/Desktop/smart_analyzer/smart_analyzer/.venv/Scripts/python.exe -m py_compile src/tcs_smart_analyzer/ui/main_window.py src/tcs_smart_analyzer/reporting/exporters.py src/tcs_smart_analyzer/core/engine.py src/tcs_smart_analyzer/data/loaders.py src/tcs_smart_analyzer/config/editable_configs.py
```

### 2.4 CLI 样例验证

```powershell
c:/Users/Ecoking/Desktop/smart_analyzer/smart_analyzer/.venv/Scripts/python.exe -m tcs_smart_analyzer.cli --input .\sample_data\tcs_demo.csv --output-dir .\outputs
```

### 2.5 安装程序构建

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_installer.ps1
```

说明：
仅当用户明确要求发布安装程序时执行该命令。

## 3. 当前真实验证结果

### 3.1 当前应以什么结果为准

当前应以以下验证面为准：

- 映射/加载/引擎：tests/test_signal_mapping.py、tests/test_loaders.py、tests/test_engine_pipeline.py
- 配置/规则/导出：tests/test_editable_configs.py、tests/test_rule_settings.py、tests/test_exporters.py
- GUI：scripts/gui_smoke_check.py
- 语法：main_window.py、exporters.py、engine.py、loaders.py、editable_configs.py 的 py_compile

本轮特别新增或强化的覆盖重点包括：

- DAT/MDF/MF4 的探测后按需读取
- BLF/ASC 按需 DBC 解码日志
- 模板编辑器语法校验与草稿创建
- HTML 左侧目录与曲线截图
- Word 首页目录、内部 hyperlink/bookmark、短锚点和书签顺序

本轮刚刚实际执行结果：

- pytest tests/test_signal_mapping.py tests/test_loaders.py tests/test_engine_pipeline.py tests/test_editable_configs.py tests/test_rule_settings.py tests/test_exporters.py：76 项全部通过
- scripts/gui_smoke_check.py：20 / 20 通过
- py_compile：src/tcs_smart_analyzer/ui/main_window.py、src/tcs_smart_analyzer/reporting/exporters.py、src/tcs_smart_analyzer/core/engine.py、src/tcs_smart_analyzer/data/loaders.py、src/tcs_smart_analyzer/config/editable_configs.py 全部通过

### 3.2 本轮未重新执行

- 本轮仍未引入用户真实 BLF/MF4 + DBC 样本库。
- 本轮仍未引入用户真实 INCA DAT 变体做仓库内自动化样本回归。
- 安装程序构建只在明确发布时执行，不作为每次日常回归的默认步骤。

## 4. 当前人工检查口径

如果你在后续开发中重新跑 GUI 或 CLI，请至少核对：

- GUI 主页可正常入队、分组分析和查看运行日志。
- 接口映射页缺参时会实时标红，并阻止分析。
- 曲线页支持多面板、多选拖拽和跨面板转移。
- 没有分析结果时，曲线页仍允许保留已选信号并显示占位。
- KPI/派生量编辑器能高亮关键配置行和 CALIBRATION。
- 模板编辑器能提示语法错误并保留 Ctrl+S 保存路径。
- HTML 与 Word 报告结构一致。
- 报告内容与结果页的分组/文件/KPI 组织一致。
- Word 目录中的分组和数据名称都能跳到对应正文位置。

## 5. 当前验证结论的使用方式

- 如果你要发版，按 2.1 -> 2.2 -> 2.3 -> 2.4 -> 2.5 的顺序执行即可。
- 如果你要继续开发较大功能，再补真实工程样本级回归。
