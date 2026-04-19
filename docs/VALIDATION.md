# TCS Smart Analyzer 验证说明

## 1. 当前环境事实

- 当前验证解释器：C:/Python312/python.exe
- 当前最常用安装命令：

```powershell
python -m pip install -e .
python -m pip install -e .[gui]
```

## 2. 当前应执行的验证命令

### 2.1 完整 unittest

```powershell
C:/Python312/python.exe -m unittest discover -s tests -v
```

### 2.2 CLI 样例验证

```powershell
C:/Python312/python.exe -m tcs_smart_analyzer.cli --input .\sample_data\tcs_demo.csv --output-dir .\outputs
```

### 2.3 GUI 离屏冒烟

```powershell
$env:QT_QPA_PLATFORM="offscreen"
C:/Python312/python.exe scripts/gui_smoke_check.py
```

### 2.4 安装程序构建

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_installer.ps1
```

说明：
仅当用户明确要求发布安装程序时执行该命令。

## 3. 当前真实验证结果

### 3.1 unittest

本轮实际执行结果：

- 总计 42 项
- 失败 2 项
- 错误 8 项
- 其余通过

当前主要失败类别：

1. 测试仍引用已移除的派生量 tcs_active_avg_slip_ratio。
2. 动态 guide 清单测试仍按旧派生量集合断言。
3. 部分导出测试与当前接口映射前置条件不一致，触发关键字段缺失。

### 3.2 CLI 与 GUI

- 本轮没有重新执行 GUI 离屏冒烟。
- 本轮没有重新执行 CLI 导出冒烟。
- 本轮仅在明确发布安装程序时，才需要验证安装程序可生成并落入 installer_release/。
- 文档中不再沿用“全部验证通过”的旧表述。

## 4. 当前人工检查口径

如果你在后续开发中重新跑 GUI 或 CLI，请至少核对：

- GUI 主页可正常入队、分组分析和查看运行日志。
- 接口映射页缺参时会实时标红，并阻止分析。
- 曲线页支持多面板、多选拖拽和跨面板转移。
- KPI/派生量编辑器能高亮关键配置行和 CALIBRATION。
- HTML 与 Word 报告结构一致。
- 报告内容与结果页的分组/文件/KPI 组织一致。

## 5. 当前验证结论的使用方式

- 如果你要继续做文档或轻量代码整理，可以接受当前状态继续推进。
- 如果你要继续做功能开发，建议先把测试基线修回与当前实现一致，再做新增功能。
