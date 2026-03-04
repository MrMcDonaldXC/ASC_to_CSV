# ASC to CSV 转换与可视化工具

将CAN总线采集的ASC格式日志文件转换为结构化的CSV文件，并提供数据可视化和对比分析功能。

## 目录

- [功能特性](#功能特性)
- [系统架构](#系统架构)
- [安装指南](#安装指南)
- [使用方法](#使用方法)
- [配置说明](#配置说明)
- [模块文档](#模块文档)
- [工作流程](#工作流程)
- [性能优化](#性能优化)
- [故障排除](#故障排除)
- [打包部署](#打包部署)

## 功能特性

### 数据转换
- 支持多DBC文件加载
- ASC文件解析和CAN帧解码
- 按BatP模式智能分组信号
- 可配置采样间隔
- 生成汇总报告和分组CSV文件
- 空值自动填充功能

### 数据可视化
- 实时数据图表显示
- 缩放和滚动浏览
- 十字参考线功能
- 列搜索筛选
- 数据分段绘制（跳过缺失数据区间）

### 数据对比
- 多文件数据对比
- 多信号叠加显示
- 缩放和滚动功能
- 图表导出

## 系统架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           应用层 (Application Layer)                     │
├─────────────────────────────────────────────────────────────────────────┤
│  main.py (CLI入口)              │  main_app.py (GUI入口)                │
│  └── ASCToCSVConverter          │  └── MainApplication                  │
│      └── ConversionService      │      └── UI Components                │
└─────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           服务层 (Service Layer)                         │
├─────────────────────────────────────────────────────────────────────────┤
│  conversion_service.py                                                   │
│  ├── ConversionService: 统一转换服务                                     │
│  └── ConversionResult: 转换结果数据类                                    │
└─────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           核心层 (Core Layer)                            │
├─────────────────────────────────────────────────────────────────────────┤
│  dbc_loader.py          │  asc_parser.py       │  data_processor.py     │
│  ├── DBCLoader          │  ├── ASCParser       │  ├── DataProcessor     │
│  │   ├── load()         │  │   ├── parse()     │  │   ├── aggregate()   │
│  │   ├── message_map    │  │   ├── _parse_line │  │   ├── classify()    │
│  │   └── signal_info    │  │   └── sampled_data│  └── sorted_groups     │
│  └──────────────────────┴──────────────────────┴───────────────────────┘
│                                                                          │
│  csv_writer.py           │  utils.py             │  config.py            │
│  ├── CSVWriter           │  ├── extract_batp_    │  ├── Config           │
│  │   ├── write_all()     │  │   group()          │  ├── validate()       │
│  │   ├── _fill_missing() │  ├── safe_value()     │  └── create_output_   │
│  │   └── _write_group()  │  └── sort_group_key() │      dir()            │
└─────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           UI层 (UI Layer)                                │
├─────────────────────────────────────────────────────────────────────────┤
│  ui/base.py              │  ui/convert_tab.py    │  ui/visualize_tab.py  │
│  ├── BaseTab             │  ├── ConvertTab       │  ├── VisualizeTab     │
│  ├── LogMixin            │  └── 文件选择/转换    │  └── 图表显示/交互    │
│  └── ProgressMixin       │                       │                       │
│                          │  ui/compare_tab.py    │                       │
│                          │  └── CompareTab       │                       │
└─────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           可视化核心 (Visualization Core)                 │
├─────────────────────────────────────────────────────────────────────────┤
│  core/csv_loader.py                    │  core/chart_manager.py          │
│  ├── CSVDataLoader                     │  ├── ChartManager               │
│  │   ├── load(): 加载CSV文件           │  │   ├── plot_segments()        │
│  │   ├── get_numeric_columns()         │  │   ├── update_crosshair()     │
│  │   └── get_time_column()             │  │   └── bind_scroll/motion()   │
└─────────────────────────────────────────────────────────────────────────┘
```

## 安装指南

### 系统要求
- Python >= 3.8 (推荐 3.11)
- 内存: 建议 4GB+
- 操作系统: Windows / Linux / macOS

### 安装步骤

```bash
# 1. 克隆或下载项目
git clone <repository-url>
cd asc_to_csv

# 2. 创建虚拟环境
python -m venv venv

# 3. 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 4. 安装依赖
pip install -r requirements.txt
```

### 依赖说明

| 包名 | 版本要求 | 用途 |
|------|----------|------|
| cantools | >=37.0.0,<42.0.0 | CAN总线DBC解析 |
| matplotlib | >=3.5.0,<4.0.0 | 数据可视化 |
| numpy | >=1.21.0,<2.0.0 | 数值计算 |
| scipy | >=1.7.0,<2.0.0 | 科学计算(可选) |
| pyinstaller | >=5.0.0,<7.0.0 | 打包工具 |

## 使用方法

### CLI命令行模式

```bash
# 1. 配置 config.json
{
    "asc_file": "data/input.asc",
    "dbc_files": ["data/dbc1.dbc", "data/dbc2.dbc"],
    "output_dir": "output",
    "sample_interval": 0.1,
    "group_size": 5,
    "csv_encoding": "utf-8-sig",
    "debug": false
}

# 2. 运行转换
python main.py
```

### GUI图形界面模式

```bash
# 运行主程序
python main_app.py
```

### 操作流程

#### 数据转换
1. 选择ASC文件
2. 添加DBC文件（可多个）
3. 选择输出目录
4. 设置采样间隔
5. 点击"开始转换"

#### 数据可视化
1. 选择CSV文件
2. 搜索或选择数据列
3. 使用缩放和滚动浏览数据
4. 启用十字参考线查看坐标

#### 数据对比
1. 选择多个CSV文件
2. 选择要对比的数据列
3. 生成对比图表
4. 使用缩放和滚动查看细节

## 配置说明

### config.json 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| asc_file | string | "" | ASC日志文件路径 |
| dbc_files | list | [] | DBC数据库文件路径列表 |
| output_dir | string | "" | CSV输出目录 |
| sample_interval | float | 0.1 | 采样间隔(秒) |
| group_size | int | 5 | 分组大小(用于空行插入) |
| csv_encoding | string | "utf-8-sig" | CSV文件编码 |
| debug | bool | false | 调试模式开关 |

### 环境变量

| 变量名 | 说明 |
|--------|------|
| ASC_TO_CSV_CONFIG | 自定义配置文件路径 |

## 模块文档

### 核心模块

#### config.py - 配置管理
```python
from config import Config, get_config

# 获取配置
config = get_config()

# 创建自定义配置
config = Config(
    asc_file="input.asc",
    dbc_files=["data.dbc"],
    output_dir="output",
    sample_interval=0.1
)

# 验证配置
if config.validate():
    config.create_output_dir()
```

#### conversion_service.py - 转换服务
```python
from conversion_service import ConversionService, ConversionResult

# 创建服务
service = ConversionService(config)

# 执行转换
result = service.convert(
    progress_callback=lambda p, n: print(f"进度: {p:.1f}%"),
    log_callback=lambda msg: print(msg)
)

# 检查结果
if result.success:
    print(f"生成 {len(result.created_files)} 个文件")
    print(f"信号数: {result.signal_count}")
```

#### dbc_loader.py - DBC加载器
```python
from dbc_loader import DBCLoader

loader = DBCLoader()
loader.load(["file1.dbc", "file2.dbc"])

# 访问消息映射
message_map = loader.message_map  # {frame_id: {message, dbc_name}}

# 访问信号信息
signal_info = loader.signal_info   # {signal_name: {unit, message, dbc}}
```

#### asc_parser.py - ASC解析器
```python
from asc_parser import ASCParser

parser = ASCParser(sample_interval=0.1, debug=False)
parser.parse("input.asc", message_map, progress_callback)

# 获取解析结果
sampled_data = parser.sampled_data    # {timestamp: {signal: [values]}}
found_signals = parser.found_signals  # Set[str]
original_count, sampled_count, signal_count = parser.get_statistics()
```

#### data_processor.py - 数据处理器
```python
from data_processor import DataProcessor

processor = DataProcessor()
processor.aggregate(sampled_data)
processor.classify_signals(found_signals)

# 获取处理结果
sorted_groups = processor.sorted_groups           # List[str]
classified_signals = processor.classified_signals # {group: [signals]}
sorted_timestamps = processor.get_sorted_timestamps()
```

#### csv_writer.py - CSV写入器
```python
from csv_writer import CSVWriter

writer = CSVWriter(
    output_dir="output",
    encoding="utf-8-sig",
    group_size=5,
    fill_interval=0.5
)

created_files = writer.write_all(
    sorted_groups=sorted_groups,
    classified_signals=classified_signals,
    sorted_timestamps=sorted_timestamps,
    aggregated_data=aggregated_data,
    signal_info=signal_info,
    statistics=statistics
)
```

### 可视化模块

#### core/csv_loader.py - CSV数据加载器
```python
from core.csv_loader import CSVDataLoader

loader = CSVDataLoader()
loader.load("data.csv")

# 获取数据
data = loader.data              # {column: [values]}
columns = loader.columns        # List[str]
numeric_cols = loader.get_numeric_columns()
time_col = loader.get_time_column()
```

#### core/chart_manager.py - 图表管理器
```python
from core.chart_manager import ChartManager

manager = ChartManager(parent_frame, figsize=(12, 6))

# 绘制数据
manager.plot_segments(x_data, y_data, label="Signal")

# 设置图表
manager.set_labels("Time[s]", "Value", "Title")
manager.add_grid()
manager.add_legend()
manager.update()

# 交互功能
manager.bind_scroll(scroll_callback)
manager.bind_motion(motion_callback)
manager.update_crosshair(x, y)
```

## 工作流程

### 转换流程序列图

```
┌─────────┐    ┌──────────────────────┐    ┌────────────┐    ┌─────────────┐
│  用户   │    │  ConversionService   │    │ DBCLoader  │    │ ASCParser   │
└────┬────┘    └──────────┬───────────┘    └─────┬──────┘    └──────┬──────┘
     │                    │                      │                  │
     │  convert(config)   │                      │                  │
     │───────────────────>│                      │                  │
     │                    │                      │                  │
     │                    │  load(dbc_files)     │                  │
     │                    │─────────────────────>│                  │
     │                    │                      │                  │
     │                    │  message_map         │                  │
     │                    │<─────────────────────│                  │
     │                    │                      │                  │
     │                    │  parse(asc_file)     │                  │
     │                    │─────────────────────────────────────────>│
     │                    │                      │                  │
     │                    │                      │  逐行解析ASC     │
     │                    │                      │  解码CAN帧       │
     │                    │                      │  采样数据        │
     │                    │                      │                  │
     │                    │  sampled_data        │                  │
     │                    │<─────────────────────────────────────────│
     │                    │                      │                  │
     │                    │  ┌─────────────────────────────────┐    │
     │                    │  │ DataProcessor.aggregate()       │    │
     │                    │  │ DataProcessor.classify_signals()│    │
     │                    │  └─────────────────────────────────┘    │
     │                    │                      │                  │
     │                    │  ┌─────────────────────────────────┐    │
     │                    │  │ CSVWriter.write_all()           │    │
     │                    │  │ - _fill_missing_values()        │    │
     │                    │  │ - _write_group_file()           │    │
     │                    │  │ - _write_summary_file()         │    │
     │                    │  └─────────────────────────────────┘    │
     │                    │                      │                  │
     │  ConversionResult  │                      │                  │
     │<───────────────────│                      │                  │
     │                    │                      │                  │
```

### ASC文件解析流程

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        ASC文件解析流程                                   │
└─────────────────────────────────────────────────────────────────────────┘

输入: ASC文件
      │
      ▼
┌─────────────────┐
│ 编码检测        │  尝试: utf-8 → gbk → gb2312 → latin-1
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 逐行读取        │  缓冲区大小: 32KB
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────────────────────────────┐
│ 正则匹配        │     │ ASC_PATTERN:                             │
│                 │     │ ^(\d+\.\d+)\s+(\d+)\s+([0-9A-Fa-f]+x?)   │
│                 │     │ \s+(Rx|Tx)\s+d\s+(\d+)\s+((...)+)$       │
└────────┬────────┘     └──────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│ 提取CAN帧信息   │
│ - timestamp     │
│ - frame_id      │
│ - data bytes    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────────────────────────────┐
│ 消息ID匹配      │────>│ frame_id in message_map?                 │
│                 │     │ Yes: 继续处理                            │
│                 │     │ No: 跳过该帧                             │
└────────┬────────┘     └──────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│ 时间采样        │  sampled_time = round(timestamp / interval) * interval
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 信号解码        │  使用cantools解码CAN帧数据
│                 │  msg.decode(data, decode_choices=False)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 数据存储        │  sampled_data[time][signal] = [values]
│                 │  found_signals.add(signal_name)
└────────┬────────┘
         │
         ▼
输出: sampled_data, found_signals, statistics
```

### 数据验证规则

| 验证项 | 规则 | 错误处理 |
|--------|------|----------|
| ASC文件路径 | 非空、存在、可读 | 返回错误信息 |
| DBC文件路径 | 非空列表、存在、可读 | 返回错误信息 |
| 输出目录 | 非空、可创建 | 返回错误信息 |
| 采样间隔 | > 0, <= 3600 | 返回错误/警告 |
| 分组大小 | > 0 | 返回错误 |
| 路径长度 | <= 4096字符 | 返回错误 |

### 错误处理机制

```python
# 文件错误
FileNotFoundError  → "错误：文件不存在"
PermissionError    → "错误：无权限访问文件"
UnicodeDecodeError → 尝试其他编码

# 内存错误
MemoryError → "错误：内存不足，请尝试增加采样间隔"

# 数据错误
ValueError  → 调试模式下输出详细信息
KeyError    → 调试模式下输出详细信息
```

## 性能优化

### 1. 防抖机制 (Debounce)
```python
# 缩放/滚动操作延迟50ms执行
_debounce_delay: int = 50

def _debounce_chart_update(self):
    current_time = time.time() * 1000
    if current_time - self._last_chart_update < self._debounce_delay:
        if not self._chart_update_pending:
            self._chart_update_pending = True
            self.root.after(self._debounce_delay, self._do_chart_update)
```

### 2. 节流处理 (Throttle)
```python
# 鼠标移动事件限制30ms间隔
_mouse_move_throttle: int = 30

def _on_mouse_move(self, event):
    current_time = time.time() * 1000
    if current_time - self._last_mouse_move_time < self._mouse_move_throttle:
        return
```

### 3. 分段绘制算法
```python
def plot_segments(self, x_data, y_data, max_gap=2):
    """
    跳过数据缺失区间，避免错误连线
    
    算法:
    1. 找出所有有效数据点索引
    2. 根据max_gap分割成多个连续段
    3. 分别绘制每个段
    """
    valid_indices = [i for i, v in enumerate(y_data) if v is not None]
    segments = []
    current_segment = [valid_indices[0]]
    
    for i in range(1, len(valid_indices)):
        if valid_indices[i] - valid_indices[i-1] <= max_gap:
            current_segment.append(valid_indices[i])
        else:
            segments.append(current_segment)
            current_segment = [valid_indices[i]]
```

### 4. 内存管理
```python
# 大文件处理时定期检查内存
MEMORY_CHECK_INTERVAL = 50000
MAX_MEMORY_SIGNALS = 10000
MAX_MEMORY_TIMESTAMPS = 100000

# 转换完成后显式释放资源
def _cleanup(self):
    if self.asc_parser:
        self.asc_parser.clear()
    if self.data_processor:
        self.data_processor.clear()
    gc.collect()
```

## 故障排除

### 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 图表无法显示 | CSV文件未正确加载 | 检查文件格式和编码 |
| 鼠标操作卡顿 | 数据量过大 | 已优化节流机制，检查系统资源 |
| 转换失败 | 文件路径错误 | 启用调试模式查看详细信息 |
| 打包后运行报错 | 缺失模块 | 在.spec的hiddenimports中添加模块 |
| 中文显示乱码 | 字体问题 | 确保系统安装SimHei或Microsoft YaHei字体 |

### 调试模式

启用调试模式可输出详细信息:
- config.json中设置: `"debug": true`
- GUI中勾选: "调试模式"

### 日志分析

```
# 正常转换日志示例
开始转换...
采样间隔: 0.1秒

正在加载DBC文件...
  已加载DBC: data/dbc1.dbc - 消息数: 50
总消息定义数: 50
总信号定义数: 200

正在解析ASC文件...
进度: 25.0% (已处理 100,000 行)
进度: 50.0% (已处理 200,000 行)
解析完成：原始数据点数: 50000, 采样后时间点数: 1000, 实际信号数: 150

正在处理数据...
分组结果：
  BatP3: 50个信号
  BatP4: 60个信号

正在创建CSV文件...
  创建文件: output/BatP3.csv
  创建文件: output/BatP4.csv

============================================================
转换完成！
输出目录: output
总计生成 5 个文件
============================================================
```

## 打包部署

### Windows打包

```bash
# 使用打包脚本
build.bat

# 或手动打包
pyinstaller main_app.spec --clean
```

输出文件: `dist\ASCtoCSV.exe`

### 部署方式

**方式一：打包文件部署**
```
将 dist\ASCtoCSV.exe 复制到目标电脑
双击运行即可
```

**方式二：源码部署**
```bash
复制整个项目目录到目标电脑
pip install -r requirements.txt
python main_app.py
```

## 输出文件说明

| 文件名 | 说明 |
|--------|------|
| Summary.csv | 转换汇总报告 |
| All_Signals.csv | 所有信号数据总览 |
| BatP3.csv, BatP4.csv... | 按分组输出的信号数据 |
| Other.csv | 未匹配分组的信号数据 |

## 版本历史

### v1.0.0 (当前版本)
- 模块化重构，代码结构清晰
- 服务层抽象，CLI/GUI共享转换逻辑
- 数据可视化功能
- 数据对比功能
- 性能优化（防抖、节流、分段绘制）
- 完善的单元测试

## 许可证

MIT License

## 作者

ASC to CSV Development Team
