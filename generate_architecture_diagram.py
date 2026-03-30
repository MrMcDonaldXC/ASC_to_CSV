# -*- coding: utf-8 -*-
"""
项目架构图生成脚本

生成高分辨率的PNG格式项目架构图，包含：
- 核心业务层
- 数据访问层
- UI层
- 外部服务集成
- 数据流方向

使用方式:
    python generate_architecture_diagram.py
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


def draw_layer(ax, x, y, width, height, label, color, text_color='white', alpha=0.9):
    """绘制矩形层"""
    box = FancyBboxPatch(
        (x, y), width, height,
        boxstyle="round,pad=0.02,rounding_size=0.05",
        facecolor=color, edgecolor='#333333',
        linewidth=2, alpha=alpha
    )
    ax.add_patch(box)
    ax.text(x + width/2, y + height/2, label,
            ha='center', va='center', fontsize=11, fontweight='bold', color=text_color)
    return (x, y, width, height)


def draw_module(ax, x, y, width, height, label, color, font_size=9):
    """绘制模块框"""
    box = FancyBboxPatch(
        (x, y), width, height,
        boxstyle="round,pad=0.02,rounding_size=0.03",
        facecolor=color, edgecolor='#555555',
        linewidth=1.5, alpha=0.95
    )
    ax.add_patch(box)
    ax.text(x + width/2, y + height/2, label,
            ha='center', va='center', fontsize=font_size, color='#222222')
    return (x, y, width, height)


def draw_arrow(ax, start, end, color='#333333', style='->'):
    """绘制箭头"""
    ax.annotate('', xy=end, xytext=start,
                arrowprops=dict(arrowstyle=style, color=color, lw=2,
                               connectionstyle="arc3,rad=0"))


def draw_bidirectional_arrow(ax, start, end, color='#333333'):
    """绘制双向箭头"""
    ax.annotate('', xy=end, xytext=start,
                arrowprops=dict(arrowstyle='<->', color=color, lw=2,
                               connectionstyle="arc3,rad=0"))


def draw_dashed_arrow(ax, start, end, color='#666666'):
    """绘制虚线箭头（数据流）"""
    ax.annotate('', xy=end, xytext=start,
                arrowprops=dict(arrowstyle='->', color=color, lw=1.5,
                               linestyle='dashed',
                               connectionstyle="arc3,rad=0"))


def generate_architecture_diagram():
    """生成项目架构图"""

    fig, ax = plt.subplots(1, 1, figsize=(20, 14), dpi=150)
    ax.set_xlim(0, 20)
    ax.set_ylim(0, 14)
    ax.set_aspect('equal')
    ax.axis('off')

    fig.patch.set_facecolor('#FAFAFA')

    ax.text(10, 13.5, 'ASC to CSV 项目架构图', ha='center', va='center',
            fontsize=20, fontweight='bold', color='#1a1a2e')
    ax.text(10, 13.0, 'Architecture Diagram', ha='center', va='center',
            fontsize=12, fontweight='normal', color='#555555', style='italic')

    colors = {
        'ui': '#4A90D9',
        'service': '#5B9A5B',
        'processor': '#E8A838',
        'parser': '#D96552',
        'core': '#8B5CF6',
        'external': '#17A2B8',
        'config': '#6C757D',
        'arrow': '#333333',
    }

    # ============ UI Layer ============
    ui_y = 11.0
    ui_height = 1.5
    draw_layer(ax, 0.5, ui_y, 19, ui_height, 'UI Layer (User Interface)', colors['ui'])

    ui_modules = [
        (1.0, 'ConvertTab\n(转换标签)', 2.5),
        (4.0, 'VisualizeTab\n(可视化标签)', 2.5),
        (7.0, 'CompareTab\n(对比标签)', 2.5),
        (10.5, 'BaseTab\n(基础组件)', 2.5),
    ]

    for x, label, w in ui_modules:
        draw_module(ax, x, ui_y + 0.2, w, ui_height - 0.4, label, '#D6E8F7', 8)

    # ============ Service Layer ============
    service_y = 8.5
    service_height = 2.0
    draw_layer(ax, 0.5, service_y, 19, service_height, 'Service Layer (Business Logic)', colors['service'])

    service_modules = [
        (1.0, 'EnhancedConversion\nService\n(转换服务)', 3.5),
        (5.0, 'MultiASC\nConverter\n(多文件转换)', 3.5),
        (9.0, 'CSVWriter\n(CSV写入)', 2.5),
        (12.0, 'DataProcessor\n(数据处理)', 2.5),
        (15.0, 'GroupExtractor\n(分组提取)', 2.5),
    ]

    for x, label, w in service_modules:
        draw_module(ax, x, service_y + 0.25, w, service_height - 0.5, label, '#C3E6C3', 8)

    # ============ Data Access Layer ============
    data_y = 5.5
    data_height = 2.5
    draw_layer(ax, 0.5, data_y, 19, data_height, 'Data Access Layer (File I/O)', colors['parser'])

    data_modules = [
        (1.0, 'ASCParser\n(ASC解析)', 3.0),
        (4.5, 'DBCLoader\n(DBC加载)', 3.0),
        (8.0, 'ASCFileMerger\n(ASC拼接)', 3.0),
        (11.5, 'CSVFileMerger\n(CSV拼接)', 3.0),
        (15.0, 'CSVLoader\n(CSV加载)', 2.5),
    ]

    for x, label, w in data_modules:
        draw_module(ax, x, data_y + 0.3, w, data_height - 0.6, label, '#F5C6C0', 8)

    # ============ Core Layer ============
    core_y = 3.0
    core_height = 2.0
    draw_layer(ax, 0.5, core_y, 19, core_height, 'Core Utilities & Configuration', colors['core'])

    core_modules = [
        (1.0, 'Config\n(配置管理)', 2.5),
        (4.0, 'Utils\n(工具函数)', 2.5),
        (7.0, 'ChartManager\n(图表管理)', 2.8),
        (10.5, 'MainApplication\n(主程序)', 2.8),
    ]

    for x, label, w in core_modules:
        draw_module(ax, x, core_y + 0.25, w, core_height - 0.5, label, '#DDD6FE', 8)

    # ============ External Services ============
    ext_y = 0.5
    ext_height = 1.8
    draw_layer(ax, 0.5, ext_y, 19, ext_height, 'External Libraries & Dependencies', colors['external'])

    ext_modules = [
        (1.0, 'cantools\n(CAN解码)', 2.5),
        (4.0, 'Tkinter\n(GUI框架)', 2.5),
        (7.0, 'matplotlib\n(图表绘制)', 2.8),
        (10.5, 'numpy\n(数值计算)', 2.5),
        (13.5, 'PyInstaller\n(打包工具)', 2.5),
    ]

    for x, label, w in ext_modules:
        draw_module(ax, x, ext_y + 0.25, w, ext_height - 0.5, label, '#B8E4E8', 8)

    # ============ Arrows / Data Flow ============
    # UI -> Service
    draw_arrow(ax, (10, ui_y), (10, service_y + service_height))
    ax.text(10.2, (ui_y + service_y + service_height)/2, 'User Input\n& Config',
            fontsize=7, color='#666666', va='center')

    # Service -> Data Access
    draw_arrow(ax, (10, service_y), (10, data_y + data_height))
    ax.text(10.2, (service_y + data_y + data_height)/2, 'Parse Request\n& Data',
            fontsize=7, color='#666666', va='center')

    # Data Access -> Core
    draw_dashed_arrow(ax, (10, data_y), (10, core_y + core_height))
    ax.text(10.2, (data_y + core_y + core_height)/2, 'Config\n& Utils',
            fontsize=7, color='#666666', va='center')

    # Internal service connections
    draw_bidirectional_arrow(ax, (4.5, service_y + 1.0), (7.5, service_y + 1.0), colors['arrow'])
    ax.text(6.0, service_y + 1.3, 'Data', fontsize=7, color='#666666', ha='center')

    draw_arrow(ax, (9.0, service_y + 1.0), (12.0, service_y + 1.0), colors['arrow'])
    ax.text(10.5, service_y + 1.3, 'Processed\nData', fontsize=7, color='#666666', ha='center')

    # Data access internal
    draw_bidirectional_arrow(ax, (4.5, data_y + 1.2), (7.5, data_y + 1.2), colors['arrow'])
    draw_bidirectional_arrow(ax, (11.5, data_y + 1.2), (14.5, data_y + 1.2), colors['arrow'])

    # ============ Legend ============
    legend_y = 0.15
    legend_items = [
        ('→', '单数据流', '#333333'),
        ('↔', '双向数据流', '#333333'),
        ('--→', '配置/工具流', '#666666'),
    ]

    ax.text(16, legend_y, 'Legend:', fontsize=9, fontweight='bold', color='#333333')
    for i, (arrow, label, color) in enumerate(legend_items):
        ax.text(17.2 + i*1.2, legend_y, f'{arrow} {label}', fontsize=7, color=color)

    # ============ Deployment Info ============
    ax.text(0.8, 0.15, 'Deployment: Windows Desktop Application (PyInstaller)',
            fontsize=8, color='#888888', style='italic')
    ax.text(13, 0.15, 'Python 3.8+ | Tkinter | matplotlib',
            fontsize=8, color='#888888', style='italic')

    plt.tight_layout()
    plt.savefig('architecture_diagram.png', dpi=150, bbox_inches='tight',
                facecolor='#FAFAFA', edgecolor='none')
    print("架构图已保存: architecture_diagram.png")


def generate_detailed_flow_diagram():
    """生成详细的数据流图"""

    fig, ax = plt.subplots(1, 1, figsize=(18, 12), dpi=150)
    ax.set_xlim(0, 18)
    ax.set_ylim(0, 12)
    ax.set_aspect('equal')
    ax.axis('off')
    fig.patch.set_facecolor('#FAFAFA')

    ax.text(9, 11.5, 'ASC to CSV 数据流图', ha='center', va='center',
            fontsize=18, fontweight='bold', color='#1a1a2e')
    ax.text(9, 11.0, 'Data Flow Diagram', ha='center', va='center',
            fontsize=11, fontweight='normal', color='#555555', style='italic')

    def draw_box(ax, x, y, w, h, label, color, subtitle=''):
        box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.05",
                            facecolor=color, edgecolor='#333333', linewidth=2, alpha=0.95)
        ax.add_patch(box)
        if subtitle:
            ax.text(x + w/2, y + h/2 + 0.15, label, ha='center', va='center',
                   fontsize=9, fontweight='bold', color='#222222')
            ax.text(x + w/2, y + h/2 - 0.15, subtitle, ha='center', va='center',
                   fontsize=7, color='#555555')
        else:
            ax.text(x + w/2, y + h/2, label, ha='center', va='center',
                   fontsize=9, fontweight='bold', color='#222222')

    def draw_arrow_simple(ax, x1, y1, x2, y2, color='#333333'):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                   arrowprops=dict(arrowstyle='->', color=color, lw=2))

    # Single File Mode Flow
    ax.text(4.5, 10.2, 'Single File Mode', ha='center', fontsize=12,
            fontweight='bold', color='#4A90D9')

    draw_box(ax, 1, 8.5, 2.5, 1, 'ASC File', '#E8A838', 'Input')
    draw_box(ax, 4.5, 8.5, 2.5, 1, 'ASCParser', '#D96552', 'cantools decode')
    draw_box(ax, 8, 8.5, 2.5, 1, 'DataProcessor', '#5B9A5B', 'aggregate & classify')
    draw_box(ax, 11.5, 8.5, 2.5, 1, 'CSVWriter', '#8B5CF6', 'write groups')
    draw_box(ax, 14.5, 8.5, 2.5, 1, 'CSV Files', '#E8A838', 'Output')

    for i, (x1, y1, x2, y2) in enumerate([
        (3.5, 9, 4.5, 9), (7, 9, 8, 9), (10.5, 9, 11.5, 9), (14, 9, 14.5, 9)
    ]):
        draw_arrow_simple(ax, x1, y1, x2, y2)

    # Multi File Mode Flow
    ax.text(13.5, 10.2, 'Multi File Mode', ha='center', fontsize=12,
            fontweight='bold', color='#5B9A5B')

    draw_box(ax, 10, 8.5, 2.5, 1, 'Multiple\nASC Files', '#E8A838', 'Input')
    draw_box(ax, 13.5, 8.5, 2.5, 1, 'FileMerger\n(Sort)', '#D96552', 'time sort')
    draw_box(ax, 10, 6.5, 6, 1.5, 'Loop: Parse + Process + Temp CSV', '#5B9A5B', '')
    draw_box(ax, 10, 4.5, 6, 1.5, 'CSVFileMerger\n(concat by group)', '#8B5CF6', '')
    draw_box(ax, 10, 2.5, 6, 1.5, 'Final CSV Files\n(cleanup temp)', '#E8A838', 'Output')

    draw_arrow_simple(ax, 12.5, 9, 13.5, 9)
    draw_arrow_simple(ax, 13.5, 8.5, 13.5, 8)
    draw_arrow_simple(ax, 13.5, 6.5, 13.5, 6)
    draw_arrow_simple(ax, 13.5, 4.5, 13.5, 4)
    draw_arrow_simple(ax, 13.5, 2.5, 13.5, 1.5)

    ax.text(16, 7.5, 'For each\nASC file', fontsize=8, color='#666666', ha='center')
    ax.text(16, 5.5, 'Merge by\ngroup name', fontsize=8, color='#666666', ha='center')

    # Note
    ax.text(9, 0.8, 'Note: Multi-file mode handles large datasets by processing each file sequentially,\n'
            'sorting by timestamp, and merging results to avoid memory issues.',
            ha='center', fontsize=8, color='#666666', style='italic',
            bbox=dict(boxstyle='round', facecolor='#F0F0F0', alpha=0.8))

    plt.tight_layout()
    plt.savefig('dataflow_diagram.png', dpi=150, bbox_inches='tight',
                facecolor='#FAFAFA', edgecolor='none')
    print("数据流图已保存: dataflow_diagram.png")


if __name__ == '__main__':
    print("正在生成项目架构图...")
    generate_architecture_diagram()
    generate_detailed_flow_diagram()
    print("完成！生成了两个PNG文件：")
    print("  1. architecture_diagram.png - 项目架构图")
    print("  2. dataflow_diagram.png - 数据流图")