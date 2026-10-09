# 验证记录

- 环境：Linux、Python 3.12、uv 管理的独立虚拟环境。
- `uv sync --locked`、`uv lock --check`：通过。
- `QT_QPA_PLATFORM=offscreen uv run --locked pytest -q`：27 passed。
- `uv run --locked ruff check .`：通过。
- `uv run --locked ruff format --check .`：通过。
- `uv build`：成功生成 Python sdist 和 wheel。
- 使用实际 parser 读取 `examples/demo.xkt`，生成并检查 Connectors / Standards 两个页面的预览。

## 数据链路

合成示例采用用户提供的 XML 布局：CalKitSave、Coaxial/SystemZ0、FrequencyLists/Stimulus/Segments/Arbitrary、DataBasedArrays/ReceivePort/SourcePort、AccuracyArrays/AccuracyData。

实际测试包含：

- 普通 Base64 与 Agilent 反转/XOR 解码，跨越 33 字节表周期。
- 接收端口/源端口组装，S11/S21/S12/S22 值与频率轴。
- Vr2/Vri/Vi2 协方差与 scalar 数组，独立频率轴及 CSV 输出。
- Touchstone RI 格式、二端口顺序、经典模型导出和不完整矩阵拒绝。
- XML namespace、UTF-16、ZIP 内额外 XML、无效输入、非法频率和解析警告。
- 原 Open 近似公式、理想 SOL、Thru 延迟。
- 核心模块独立导入而不加载 PyQt。
- GUI 使用实际解析器后台加载、实际导出函数写文件、空套件刷新、重复切换、失败后保留上一套件。
- 根目录旧 API 的兼容导入。

## 尚未验证

真实 Keysight .xkt 文件的覆盖率、与仪器计算/导出结果的一致性、Windows EXE 和所有支持的 Python/平台组合。
示例为合成测试数据，不能作为校准参考。
