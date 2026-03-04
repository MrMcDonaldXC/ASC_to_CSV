# ASC to CSV 转换与可视化工具

将CAN总线采集的ASC格式日志文件转换为结构化的CSV文件，并提供数据可视化和对比分析功能。

## 功能特性

### 数据转换
- 支持多DBC文件加载
- ASC文件解析和CAN帧解码
- 按BatP模式智能分组信号
- 可配置采样间隔
- 生成汇总报告和分组CSV文件

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

## 项目结构

```
asc_to_csv/
├── main_app.py              # 主入口（模块化版本）
├── main_app_legacy.py       # 旧版本备份
├── main_app.spec            # PyInstaller打包配置
│
├── core/                    # 核心功能模块
│   ├── __init__.py
│   ├── csv_loader.py        # CSV数据加载器
│   └── chart_manager.py     # 图表管理器
│
├── ui/                      # 用户界面模块
│   ├── __init__.py
│   ├── base.py              # 基础UI组件
│   ├── convert_tab.py       # 数据转换标签页
│   ├── visualize_tab.py     # 数据可视化标签页
│   └── compare_tab.py       # 数据对比标签页
│
├── config.py                # 配置管理
├── dbc_loader.py            # DBC文件加载器
├── asc_parser.py            # ASC文件解析器
├── data_processor.py        # 数据处理器
├── csv_writer.py            # CSV文件写入器
├── utils.py                 # 工具函数
│
├── requirements.txt         # 依赖清单
├── build.bat                # Windows打包脚本
└── README.md                # 项目说明
```

## 安装

### 系统要求
- Python >= 3.8 (推荐 3.11)
- 内存: 建议 4GB+

### 安装依赖

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

## 使用方法

### 图形界面模式

```bash
# 运行主程序
python main_app.py
```

或直接运行打包后的可执行文件：
```
dist\ASCtoCSV.exe
```

### 操作步骤

1. **数据转换**
   - 选择ASC文件
   - 添加DBC文件（可多个）
   - 选择输出目录
   - 设置采样间隔
   - 点击"开始转换"

2. **数据可视化**
   - 选择CSV文件
   - 搜索或选择数据列
   - 使用缩放和滚动浏览数据
   - 启用十字参考线查看坐标

3. **数据对比**
   - 选择多个CSV文件
   - 选择要对比的数据列
   - 生成对比图表
   - 使用缩放和滚动查看细节

## 配置文件

`config.json` 示例：
```json
{
    "asc_file": "data/input.asc",
    "dbc_files": ["data/dbc1.dbc", "data/dbc2.dbc"],
    "output_dir": "output",
    "sample_interval": 0.1,
    "csv_encoding": "utf-8-sig",
    "debug": false
}
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

## 输出文件

| 文件名 | 说明 |
|--------|------|
| Summary.csv | 转换汇总报告 |
| All_Signals.csv | 所有信号数据总览 |
| BatP3.csv, BatP4.csv... | 按分组输出的信号数据 |
| Other.csv | 未匹配分组的信号数据 |

## 性能优化

- 防抖机制：减少频繁重绘
- 节流处理：优化鼠标交互
- 分段绘制：跳过数据缺失区间
- 内存管理：及时释放资源

## 版本历史

### v1.0.0 (当前版本)
- 模块化重构，代码结构清晰
- 数据可视化功能
- 数据对比功能
- 性能优化
- 修复图像生成问题
- 优化鼠标交互流畅度

## 许可证

MIT License

## 作者

ASC to CSV Development Team
