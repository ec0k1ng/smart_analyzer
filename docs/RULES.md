# TCS Smart Analyzer 规则与判定治理说明

## 1. 当前规则模型

当前项目面向用户的“规则”本质上是 KPI 的判定层，不再是独立 rule_specs 执行链。

当前一条规则至少由以下信息构成：

- KPI 名称
- KPI 数值
- 单位
- 阈值
- 达标条件
- 判定说明
- 通过提示
- 失败提示

这些信息当前主要来自 KPI_DEFINITION。

## 2. 当前强约束

### 2.1 KPI 文件必须承担计算与判定

正式 KPI 文件必须同时提供：

- KPI_DEFINITION
- CALIBRATION
- calculate_kpi(dataframe)
- calculate_kpi_series(dataframe)

### 2.2 trend_source 约束

- KPI_DEFINITION["trend_source"] 必须与 KPI_DEFINITION["name"] 完全一致。
- 不允许再把 trend_source 写成任意临时列名。

### 2.3 阈值与判定条件必须显式化

- threshold 不能为空
- pass_condition 不能为空
- rule_description 应说明该 KPI 为什么代表对应判定
- pass_message 和 fail_message 应可直接用于结果展示和导出

## 3. 当前派生量与规则的关系

- 派生量不直接输出规则结果。
- 派生量的职责是提供共享中间序列。
- KPI 使用原始信号和派生量完成最终数值计算与判定。

## 4. 当前不允许再回退的旧做法

- 不允许把规则主体写回独立 rule_specs 作为当前主执行机制。
- 不允许把自动别名匹配写成规则前置依赖。
- 不允许省略 calculate_kpi_series。
- 不允许把算法调参量散落在文件顶部和函数内部，而不集中到 CALIBRATION。

## 5. 当前维护要求

如果新增、删除或修改 KPI 判定逻辑，必须同步更新：

1. docs/RULES.md
2. docs/PROJECT_STATUS.md
3. docs/VALIDATION.md
4. docs/CHANGELOG.md
5. 如影响接手理解，还要更新 docs/HANDOFF.md

### 5.1 版本号与安装程序强约束

- 当前发布版本基线固定从 V1.1 起步，对应 Python 包版本号 1.1.0。
- 默认开发变更不要求同步生成安装程序；只有在用户明确提出“发布安装程序”时，才执行安装程序构建与交付。
- 安装程序唯一发布目录固定为 installer_release/。
- installer_release/ 目录中只允许保留当前版本的安装程序，不允许堆放 spec、临时 dist、work、日志或其他中间产物。
- 标准构建命令固定为 scripts/build_installer.ps1；需要发布时必须复用这条脚本，不允许手工散落生成物。
- 发布名称统一为“自动化数据分析工具”；安装程序必须包含完整应用目录和当前配置文件，包括 KPI、派生量、模板、接口映射、DBC 等运行所需内容。
- 发布安装程序时，必须提供安装目录选择过程，并支持标准快捷方式创建。
- KPI 和派生量文件名必须与各自 definition 中的 name 保持一致；历史错名文件也必须自动纠偏，不允许继续保留 new_kpi 这类正式运行文件名。

## 6. 当前已知风险

- 当前完整测试基线尚未完全覆盖最新规则清单。
- 当前仓库中没有 tcs_active_avg_slip_ratio，但历史测试与旧文档仍可能引用它。
