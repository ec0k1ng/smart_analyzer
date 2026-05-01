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
c:/Users/Ecoking/Desktop/smart_analyzer/smart_analyzer/.venv/Scripts/python.exe -m pytest tests/test_signal_mapping.py tests/test_editable_configs.py tests/test_engine_pipeline.py tests/test_rule_settings.py
```

### 2.2 GUI 离屏冒烟

```powershell
$env:QT_QPA_PLATFORM='offscreen'; c:/Users/Ecoking/Desktop/smart_analyzer/smart_analyzer/.venv/Scripts/python.exe scripts/gui_smoke_check.py
```

### 2.3 UI/核心语法检查

```powershell
c:/Users/Ecoking/Desktop/smart_analyzer/smart_analyzer/.venv/Scripts/python.exe -m py_compile src/tcs_smart_analyzer/ui/main_window.py src/tcs_smart_analyzer/core/signal_mapping.py src/tcs_smart_analyzer/config/editable_configs.py src/tcs_smart_analyzer/config/derived_signals/slip_ratio.py src/tcs_smart_analyzer/config/derived_signals/tcs_target_slip_ratio_global.py src/tcs_smart_analyzer/config/kpi_specs/max_slip_speed.py src/tcs_smart_analyzer/config/kpi_specs/tcs_max_control_time.py src/tcs_smart_analyzer/config/kpi_specs/mean_vehicle_speed_kph.py src/tcs_smart_analyzer/config/kpi_specs/max_yaw_rate_abs_degps.py src/tcs_smart_analyzer/config/kpi_specs/max_steering_wheel_angle_abs_deg.py src/tcs_smart_analyzer/config/kpi_specs/mean_longitudinal_accel_full_throttle_mps2.py
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

- pytest tests/test_editable_configs.py tests/test_engine_pipeline.py tests/test_rule_settings.py：32 项全部通过
- get_errors：main_window.py、editable_configs.py 无错误
- 离屏定向验证：子框信号 Ctrl+W 局部隐藏/显示、hidden_signals 持久化、接口映射真实信号列可缩减到 1 列，均通过

当前新增覆盖重点包括：

- 接口映射公式表达式，例如 time_ms*0.001
- time_s 固定第一行的接口映射同步
- 打滑量派生量、全局目标打滑量与控滑时间新算法链路
- 新增横摆角速度、方向盘转角、全油门平均纵向加速度 KPI

补充实样核对：

- tests/D档驱制动，10kph以内纯液压.xlsx 的表头存在 pandas 改写后的 time.1、time.2、time.3 等重复时间列变体。
- 当前在该样本上把 time_s 分别映射为 time1、time2、time3，都会报 SignalMappingError: 缺少关键字段，无法开始 TCS 分析: time_s。
- 当前在该样本上把 time_s 映射为 time，可正常通过 AnalysisEngine.analyze_file()。

窗口态验证边界：

- 已完成窗口状态切换与主窗口 resize 触发的曲线页重建修复，并通过语法与聚焦回归验证。
- scripts/gui_smoke_check.py 仍可作为 GUI 冒烟入口，但当前未重新刷到整套通过结论。
- 本轮未重新执行真实桌面环境下的手动 GUI 回归，因此最大化/恢复后的最终交互体验仍建议在用户机器上做一次手测确认。

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
