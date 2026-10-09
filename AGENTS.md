# AGENTS.md

本文件指导 AI 编码助手在本仓库工作。以用户最新明确要求为准。

## 项目与功能基准

Keysight `.xkt` 校准套件解析、解码、PyQt6 查看、Touchstone/CSV 导出工具。
Python >= 3.10；PyQt6、matplotlib、numpy；依赖统一由 uv 管理。
功能以用户提供的模型字段、XML 结构和解码/经典近似公式为基准。

## 目录与依赖方向

- `src/calkit_viewer/models.py`：Connector、Standard、CalKitData。改动前阅读字段注释。
- `decoding.py`：Base64 与 AgilentData 解码，无 GUI 依赖。
- `parser.py`：XML/ZIP、namespace、频率/端口映射/不确定度组装。
- `model_response.py`：原始经典标准件近似模型，GUI 不包含算法公式。
- `export.py`：Touchstone 与 CSV 文件输出。
- `gui/`：app、window、pages、plot、helpers、theme，仅负责交互与展示。
- 根目录 `xkt_parser.py`、`calkit_model.py`、`calkits_model.py`、`utils.py` 为兼容转发层，不复制算法。
- 依赖方向：GUI → parser/models/model_response/export；parser → decoding/models；export → models/model_response/parser。
- 核心模块禁止 import PyQt，禁止反向依赖 GUI。

## 模型与算法约定

- 保留 `std_type`、`num_ports`、`raw_s_data`、`is_database_type` 等用户字段。
- `s_params` 为 `freq`（Hz）与复数 S 参数数组，不可用时为 None。
- XML 使用用户提供的 `FrequencyLists/Stimulus/Segments/Arbitrary`、每个 DataBasedArrays 的 ReceivePort/SourcePort，以及 AccuracyArrays/AccuracyData。
- `raw_data` 与 `agi64_raw_data` 是 Base64 文本，不是已经 Base64 解码的二进制；不得重复解码。
- Agilent 算法：每 8 字节反转，按目标字节索引 `% 33` 与 `agilent_corruption_list` XOR，再按小端 double 实虚交替组装复数。
- 不确定度使用 Vr2/Vri/Vi2/scalar；每条目的频率轴独立解析，不得静默借用不一致的轴。
- 经典计算仍为用户原近似模型：50 Ω、1000 点、原 Open/Short/Load/Thru 公式。改变算法需显式说明口径及验证影响。
- 不猜测缺失矩阵元素，不把 Offset Z0 自动当作 Touchstone 参考阻抗。
- 模型参数 SI 单位：Hz、s、Ω/s、Ω、F/Hz^n、H/Hz^n。

## GUI 规范

- 浅冷灰背景、白色卡片、细浅灰边框、适度圆角、蓝色主强调色。
- 左侧列表/属性、右侧数据/绘图、底部摘要/日志；分隔条可调。
- 白底浅网格；S11 蓝、S21 绿、S12 橙、S22 紫；相位棕色虚线；图例和单位清楚。
- 主按钮蓝色实心；次按钮白底浅边框；无数据时使用占位图并禁用无效动作。
- 文件解析放 QThread；详细 traceback 写日志；用 QSettings 保存常用状态。
- 清空或切换套件时清理旧属性与曲线，防止展示上一文件的数据。

## 常用命令

```sh
uv sync --locked
uv run --locked xkt-viewer
uv run --locked python xkt_viewer.py examples/demo.xkt
uv run --locked pytest -q
uv run --locked ruff check .
uv run --locked ruff format --check .
uv lock --check
```

无显示器 Linux GUI 测试设置 `QT_QPA_PLATFORM=offscreen`。
Windows 打包：`uv run --locked --group build pyinstaller packaging/calkits_viewer.spec`。
依赖变更使用 uv add/uv lock；提交 pyproject.toml 与 uv.lock，不提交 .venv、缓存、build/dist、真实客户测量文件。

## 验证要求

按改动范围运行相关测试，完整提交前运行测试与静态检查。
解析/解码变更核对频率、端口顺序、复数值、不确定度；导出测试核对 Touchstone S11/S21/S12/S22 顺序。
GUI 变更检查两个页面、单/双端口、空数据、加载失败与重复切换，并检查实际渲染。
合成 demo 是 schema 验证数据，不代表真实 Keysight 文件或计量精度；报告中区分已验证与未验证内容。
