# asc_to_csv/main_app.py
"""
ASC to CSV 转换与可视化主程序
整合了数据转换和数据可视化功能
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Dict, List, Optional, Any, Tuple
import csv
import gc
import traceback

import matplotlib
matplotlib.use('TkAgg')  # 设置matplotlib使用TkAgg后端以在Tkinter中显示
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import numpy as np

# 导入项目自定义模块
from config import Config, get_config
from dbc_loader import DBCLoader
from asc_parser import ASCParser
from data_processor import DataProcessor
from csv_writer import CSVWriter


# 设置matplotlib中文字体支持，防止中文显示为方框
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False  # 正确显示负号
plt.rcParams['lines.antialiased'] = True  # 启用线条抗锯齿
plt.rcParams['patch.antialiased'] = True  # 启用补丁抗锯齿


# 多列对比模式下可选择的数据列名
MULTI_SELECT_COLUMNS = [
    'MaxCellTemp', 'MinCellTemp', 'PackSOC', 'HvBusVlt', 
    'BranchCrnt', 'PackFltLvl', 'MaxCellVlt', 'MinCellVlt',
    'PackFltCode', 'PackTotCrnt'
]


class CSVDataLoader:
    """CSV数据加载器
    
    负责加载和解析CSV文件，提供数据访问接口
    支持自动识别时间列和数值列
    """
    
    def __init__(self):
        """初始化CSV数据加载器"""
        self.data: Dict[str, List] = {}  # 存储列名到数据列表的映射
        self.columns: List[str] = []      # 存储所有列名
        self.row_count: int = 0           # 存储数据行数
    
    def load(self, file_path: str, encoding: str = 'utf-8-sig') -> bool:
        """加载CSV文件
        
        Args:
            file_path: CSV文件路径
            encoding: 文件编码，默认为utf-8-sig
            
        Returns:
            bool: 加载成功返回True，失败返回False
        """
        # 重置内部状态
        self.data = {}
        self.columns = []
        self.row_count = 0
        
        try:
            # 打开并读取CSV文件
            with open(file_path, 'r', newline='', encoding=encoding) as f:
                reader = csv.reader(f)
                # 读取列名
                self.columns = next(reader)
                
                # 为每列初始化空列表
                for col in self.columns:
                    self.data[col] = []
                
                # 逐行读取数据
                for row in reader:
                    if len(row) == 0:
                        continue
                    
                    self.row_count += 1
                    # 将每行数据分配到对应列
                    for i, col in enumerate(self.columns):
                        if i < len(row):
                            value = row[i].strip()
                            try:
                                # 尝试将值转换为浮点数
                                if value == '':
                                    self.data[col].append(None)
                                else:
                                    self.data[col].append(float(value))
                            except ValueError:
                                # 转换失败则保留原始字符串
                                self.data[col].append(value)
                        else:
                            # 行数据不足，填充None
                            self.data[col].append(None)
            
            return True
            
        except Exception as e:
            print(f"加载文件失败: {e}")
            return False
    
    def get_time_column(self) -> Optional[str]:
        """获取时间列名称
        
        优先查找包含'time'关键词的列名，若没有则返回第一列
        
        Returns:
            Optional[str]: 时间列名，若没有列则返回None
        """
        for col in self.columns:
            if 'time' in col.lower():
                return col
        if self.columns:
            return self.columns[0]
        return None
    
    def get_numeric_columns(self) -> List[str]:
        """获取数值型列名称列表
        
        排除时间列，返回所有包含数值数据的列名
        
        Returns:
            List[str]: 数值型列名列表
        """
        numeric_cols = []
        time_col = self.get_time_column()
        
        for col in self.columns:
            # 跳过时间列
            if col == time_col:
                continue
            # 获取非空值
            values = [v for v in self.data[col] if v is not None]
            # 检查所有值是否为数值类型
            if values and all(isinstance(v, (int, float)) for v in values):
                numeric_cols.append(col)
        return numeric_cols
    
    def get_multi_select_columns(self) -> List[str]:
        """获取多列显示时可选择的列
        
        从数值列中筛选出预定义的重要列，用于多列对比功能
        
        Returns:
            List[str]: 可用于多列对比的列名列表
        """
        numeric_cols = self.get_numeric_columns()
        result = []
        # 从预定义的重要列名中查找匹配项
        for target in MULTI_SELECT_COLUMNS:
            for col in numeric_cols:
                if target in col:
                    result.append(col)
                    break
        return result


class MainApplication:
    """主应用程序
    
    负责创建和管理整个GUI应用程序，包括数据转换、可视化和对比功能
    """
    
    def __init__(self, root: tk.Tk):
        """初始化主应用程序
        
        Args:
            root: Tkinter根窗口对象
        """
        self.root = root
        self.root.title("ASC to CSV 转换与可视化工具 v1.0.0")
        self.root.geometry("1400x900")
        self.root.minsize(1000, 700)
        
        # 配置相关
        self.config: Optional[Config] = None
        
        # 转换状态控制
        self._convert_lock = threading.Lock()  # 线程锁，确保转换状态安全
        self._is_converting = False            # 转换进行中标志
        
        # 数据可视化相关
        self.data_loader = CSVDataLoader()    # CSV数据加载器
        self.current_file: Optional[str] = None    # 当前加载的文件路径
        self.current_column: Optional[str] = None # 当前选择的数据列
        self.zoom_level: float = 1.0          # 缩放级别
        self.scroll_position: float = 0.0     # 水平滚动位置
        self.crosshair_enabled: bool = False   # 十字参考线启用状态
        self.output_dir: Optional[str] = None  # 输出目录
        self._all_columns: List[str] = []      # 所有可用的数据列（用于搜索筛选）
        self._search_placeholder: str = "搜索列名..."  # 搜索框占位符
        
        # 数据对比相关
        self.compare_data_loaders: Dict[str, CSVDataLoader] = {}  # 对比文件的数据加载器
        self.compare_files: List[str] = []                      # 对比文件列表
        self.compare_columns: List[str] = []                    # 对比数据列列表
        self.compare_zoom_level: float = 1.0                    # 对比图表缩放级别
        self.compare_scroll_position: float = 0.0               # 对比图表水平滚动位置
        
        # 性能优化相关
        self._chart_update_pending: bool = False                # 图表更新是否待处理
        self._compare_update_pending: bool = False              # 对比图表更新是否待处理
        self._last_chart_update: float = 0                      # 上次图表更新时间
        self._last_compare_update: float = 0                    # 上次对比图表更新时间
        self._debounce_delay: int = 50                          # 防抖延迟（毫秒）
        
        # 初始化界面
        self._setup_styles()
        self._create_widgets()
        self._load_config()
        
        # 设置窗口关闭事件处理
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    @property
    def is_converting(self) -> bool:
        """获取转换状态
        
        Returns:
            bool: 转换进行中返回True，否则返回False
        """
        with self._convert_lock:
            return self._is_converting
    
    @is_converting.setter
    def is_converting(self, value: bool):
        """设置转换状态
        
        Args:
            value: True表示转换进行中，False表示转换未进行
        """
        with self._convert_lock:
            self._is_converting = value
    
    def _setup_styles(self):
        """设置界面样式"""
        style = ttk.Style()
        style.configure("Title.TLabel", font=("Microsoft YaHei", 12, "bold"))
    
    def _create_widgets(self):
        """创建主界面控件"""
        # 创建主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建选项卡控件
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # 创建三个选项卡
        self._create_convert_tab()    # 数据转换选项卡
        self._create_visualize_tab()  # 数据可视化选项卡
        self._create_compare_tab()    # 数据对比选项卡
    
    def _create_convert_tab(self):
        """创建数据转换选项卡"""
        # 创建转换选项卡框架
        convert_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(convert_frame, text="数据转换")
        
        # 标题标签
        title_label = ttk.Label(convert_frame, text="ASC to CSV 转换工具", style="Title.TLabel")
        title_label.pack(pady=(0, 10))
        
        # 文件设置区域
        file_frame = ttk.LabelFrame(convert_frame, text="文件设置", padding="10")
        file_frame.pack(fill=tk.X, pady=5)
        
        # ASC文件选择
        ttk.Label(file_frame, text="ASC文件:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.asc_entry = ttk.Entry(file_frame, width=60)
        self.asc_entry.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=2)
        ttk.Button(file_frame, text="浏览...", command=self._browse_asc).grid(row=0, column=2, pady=2)
        
        # DBC文件选择
        ttk.Label(file_frame, text="DBC文件:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.dbc_frame = ttk.Frame(file_frame)
        self.dbc_frame.grid(row=1, column=1, columnspan=2, sticky=tk.EW, pady=2)
        
        # DBC文件列表框
        self.dbc_listbox = tk.Listbox(self.dbc_frame, height=3, selectmode=tk.EXTENDED)
        self.dbc_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # DBC文件操作按钮
        dbc_btn_frame = ttk.Frame(self.dbc_frame)
        dbc_btn_frame.pack(side=tk.RIGHT, padx=5)
        ttk.Button(dbc_btn_frame, text="添加", command=self._add_dbc, width=6).pack(pady=1)
        ttk.Button(dbc_btn_frame, text="删除", command=self._remove_dbc, width=6).pack(pady=1)
        
        # 输出目录选择
        ttk.Label(file_frame, text="输出目录:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.output_entry = ttk.Entry(file_frame, width=60)
        self.output_entry.grid(row=2, column=1, sticky=tk.EW, padx=5, pady=2)
        ttk.Button(file_frame, text="浏览...", command=self._browse_output).grid(row=2, column=2, pady=2)
        
        # 设置列权重，使输入框能够自适应宽度
        file_frame.columnconfigure(1, weight=1)
        
        # 转换参数区域
        param_frame = ttk.LabelFrame(convert_frame, text="转换参数", padding="10")
        param_frame.pack(fill=tk.X, pady=5)
        
        # 采样间隔设置
        ttk.Label(param_frame, text="采样间隔(秒):").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.sample_interval_var = tk.StringVar(value="0.1")
        ttk.Entry(param_frame, textvariable=self.sample_interval_var, width=15).grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        # CSV编码设置
        ttk.Label(param_frame, text="CSV编码:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.encoding_var = tk.StringVar(value="utf-8-sig")
        encoding_combo = ttk.Combobox(param_frame, textvariable=self.encoding_var, width=12, state="readonly")
        encoding_combo["values"] = ("utf-8-sig", "utf-8", "gbk", "gb2312")
        encoding_combo.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        # 调试模式选项
        self.debug_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(param_frame, text="调试模式", variable=self.debug_var).grid(row=1, column=2, sticky=tk.W, padx=(20, 0), pady=2)
        
        # 操作按钮区域
        action_frame = ttk.Frame(convert_frame)
        action_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(action_frame, text="保存配置", command=self._save_config, width=12).pack(side=tk.LEFT, padx=5)
        self.convert_btn = ttk.Button(action_frame, text="开始转换", command=self._start_convert, width=15)
        self.convert_btn.pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="退出", command=self._on_closing, width=12).pack(side=tk.RIGHT, padx=5)
        
        # 运行日志区域
        log_frame = ttk.LabelFrame(convert_frame, text="运行日志", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 日志文本框和滚动条
        self.log_text = tk.Text(log_frame, height=10, state=tk.DISABLED, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def _create_visualize_tab(self):
        """创建数据可视化选项卡"""
        # 创建可视化选项卡框架
        viz_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(viz_frame, text="数据可视化")
        
        # 控制面板区域
        control_frame = ttk.LabelFrame(viz_frame, text="控制面板", padding="10")
        control_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 文件选择区域
        file_frame = ttk.Frame(control_frame)
        file_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(file_frame, text="CSV文件:").pack(side=tk.LEFT)
        self.file_combo = ttk.Combobox(file_frame, width=50, state="readonly")
        self.file_combo.pack(side=tk.LEFT, padx=5)
        self.file_combo.bind("<<ComboboxSelected>>", self._on_file_selected)
        
        ttk.Button(file_frame, text="刷新目录", command=self._refresh_csv_files).pack(side=tk.LEFT, padx=5)
        
        # 数据列选择区域
        column_frame = ttk.Frame(control_frame)
        column_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(column_frame, text="数据列:").pack(side=tk.LEFT)
        
        # 搜索输入框
        self.column_search_var = tk.StringVar()
        self.column_search_var.trace_add("write", self._on_column_search_changed)
        self.column_search_entry = ttk.Entry(column_frame, textvariable=self.column_search_var, width=20)
        self.column_search_entry.pack(side=tk.LEFT, padx=5)
        self.column_search_entry.insert(0, "搜索列名...")
        self.column_search_entry.bind("<FocusIn>", self._on_search_focus_in)
        self.column_search_entry.bind("<FocusOut>", self._on_search_focus_out)
        
        # 数据列下拉框
        self.column_combo = ttk.Combobox(column_frame, width=50, state="readonly")
        self.column_combo.pack(side=tk.LEFT, padx=5)
        self.column_combo.bind("<<ComboboxSelected>>", self._on_column_selected)
        
        # 搜索状态标签
        self.column_search_status = ttk.Label(column_frame, text="", width=20)
        self.column_search_status.pack(side=tk.LEFT, padx=5)
        
        # 缩放和滚动控制区域
        zoom_frame = ttk.Frame(control_frame)
        zoom_frame.pack(fill=tk.X, pady=5)
        
        # 缩放控制
        ttk.Label(zoom_frame, text="缩放:").pack(side=tk.LEFT)
        self.zoom_scale = ttk.Scale(zoom_frame, from_=0.1, to=5.0, value=1.0, 
                                    orient=tk.HORIZONTAL, length=150,
                                    command=self._on_zoom_changed)
        self.zoom_scale.pack(side=tk.LEFT, padx=5)
        self.zoom_label = ttk.Label(zoom_frame, text="100%", width=6)
        self.zoom_label.pack(side=tk.LEFT)
        
        ttk.Button(zoom_frame, text="重置", command=self._reset_zoom).pack(side=tk.LEFT, padx=10)
        
        # 水平滚动控制
        ttk.Label(zoom_frame, text="水平滚动:").pack(side=tk.LEFT, padx=(20, 0))
        self.scroll_scale = ttk.Scale(zoom_frame, from_=0, to=100, value=0,
                                      orient=tk.HORIZONTAL, length=150,
                                      command=self._on_scroll_changed)
        self.scroll_scale.pack(side=tk.LEFT, padx=5)
        
        # 十字参考线选项
        self.crosshair_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(zoom_frame, text="显示十字参考线", variable=self.crosshair_var,
                        command=self._toggle_crosshair).pack(side=tk.LEFT, padx=20)
        
        # 数据图表区域
        chart_frame = ttk.LabelFrame(viz_frame, text="数据图表", padding="5")
        chart_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建matplotlib图表
        self.figure = Figure(figsize=(12, 6), dpi=100)
        self.ax = self.figure.add_subplot(111)
        
        # 将matplotlib图表嵌入到Tkinter界面
        self.canvas = FigureCanvasTkAgg(self.figure, master=chart_frame)
        self.canvas.draw()
        
        canvas_widget = self.canvas.get_tk_widget()
        canvas_widget.pack(fill=tk.BOTH, expand=True)
        
        # 添加matplotlib工具栏
        toolbar_frame = ttk.Frame(chart_frame)
        toolbar_frame.pack(fill=tk.X)
        self.toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        self.toolbar.update()
        
        # 绑定鼠标事件
        self.canvas.mpl_connect('scroll_event', self._on_mouse_scroll)      # 鼠标滚轮事件
        self.canvas.mpl_connect('motion_notify_event', self._on_mouse_move)  # 鼠标移动事件
        
        # 初始化十字参考线相关变量
        self.crosshair_vline = None      # 垂直参考线
        self.crosshair_hline = None      # 水平参考线
        self.coord_annotation = None     # 坐标标注
        
        # 状态栏
        status_frame = ttk.Frame(viz_frame)
        status_frame.pack(fill=tk.X, pady=(5, 0))
        self.status_label = ttk.Label(status_frame, text="就绪")
        self.status_label.pack(side=tk.LEFT)
        self.coord_label = ttk.Label(status_frame, text="")
        self.coord_label.pack(side=tk.RIGHT)
    
    def _create_compare_tab(self):
        """创建数据对比选项卡"""
        # 创建对比选项卡框架
        compare_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(compare_frame, text="数据对比")
        
        # 对比设置区域
        control_frame = ttk.LabelFrame(compare_frame, text="对比设置", padding="10")
        control_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 文件选择区域
        file_frame = ttk.Frame(control_frame)
        file_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(file_frame, text="选择文件:").pack(side=tk.LEFT)
        
        # 文件列表框，支持多选
        self.compare_file_listbox = tk.Listbox(file_frame, height=4, selectmode=tk.MULTIPLE, width=40)
        self.compare_file_listbox.pack(side=tk.LEFT, padx=5)
        
        # 绑定鼠标滚轮事件，实现每次只滚动一行
        self.compare_file_listbox.bind('<MouseWheel>', self._on_file_list_scroll)
        
        ttk.Button(file_frame, text="刷新文件", command=self._refresh_compare_files).pack(side=tk.LEFT, padx=5)
        
        # 数据列选择区域
        column_frame = ttk.Frame(control_frame)
        column_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(column_frame, text="选择数据列:").pack(side=tk.LEFT)
        
        # 数据列复选框
        self.compare_column_vars: Dict[str, tk.BooleanVar] = {}
        self.compare_column_frame = ttk.Frame(column_frame)
        self.compare_column_frame.pack(side=tk.LEFT, padx=5)
        
        # 为预定义的重要列创建复选框
        for i, col_name in enumerate(MULTI_SELECT_COLUMNS):
            var = tk.BooleanVar(value=False)
            self.compare_column_vars[col_name] = var
            cb = ttk.Checkbutton(self.compare_column_frame, text=col_name, variable=var)
            cb.grid(row=0, column=i, padx=5)
        
        # 操作按钮区域
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(btn_frame, text="生成对比图", command=self._generate_compare_chart).pack(side=tk.LEFT, padx=5)
        
        # 缩放控制
        ttk.Label(btn_frame, text="缩放:").pack(side=tk.LEFT, padx=(20, 0))
        self.compare_zoom_scale = ttk.Scale(btn_frame, from_=0.1, to=5.0, value=1.0,
                                            orient=tk.HORIZONTAL, length=100,
                                            command=self._on_compare_zoom_changed)
        self.compare_zoom_scale.pack(side=tk.LEFT, padx=5)
        self.compare_zoom_label = ttk.Label(btn_frame, text="100%", width=6)
        self.compare_zoom_label.pack(side=tk.LEFT)
        
        ttk.Button(btn_frame, text="重置缩放", command=self._reset_compare_zoom).pack(side=tk.LEFT, padx=10)
        
        # 水平滚动控制（与缩放控制同一行）
        ttk.Label(btn_frame, text="水平滚动:").pack(side=tk.LEFT, padx=(20, 0))
        self.compare_scroll_scale = ttk.Scale(btn_frame, from_=0, to=100, value=0,
                                               orient=tk.HORIZONTAL, length=150,
                                               command=self._on_compare_scroll_changed)
        self.compare_scroll_scale.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text="重置滚动", command=self._reset_compare_scroll).pack(side=tk.LEFT, padx=10)
        
        # 对比图表区域
        chart_frame = ttk.LabelFrame(compare_frame, text="对比图表", padding="5")
        chart_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建matplotlib对比图表
        self.compare_figure = Figure(figsize=(12, 6), dpi=100)
        self.compare_ax = self.compare_figure.add_subplot(111)
        
        # 将matplotlib图表嵌入到Tkinter界面
        self.compare_canvas = FigureCanvasTkAgg(self.compare_figure, master=chart_frame)
        self.compare_canvas.draw()
        
        # 绑定鼠标滚轮事件
        self.compare_canvas.mpl_connect('scroll_event', self._on_compare_mouse_scroll)
        
        compare_canvas_widget = self.compare_canvas.get_tk_widget()
        compare_canvas_widget.pack(fill=tk.BOTH, expand=True)
        
        # 添加matplotlib工具栏
        compare_toolbar_frame = ttk.Frame(chart_frame)
        compare_toolbar_frame.pack(fill=tk.X)
        self.compare_toolbar = NavigationToolbar2Tk(self.compare_canvas, compare_toolbar_frame)
        self.compare_toolbar.update()
        
        # 状态栏
        compare_status_frame = ttk.Frame(compare_frame)
        compare_status_frame.pack(fill=tk.X, pady=(5, 0))
        self.compare_status_label = ttk.Label(compare_status_frame, text="请选择文件和数据列进行对比")
        self.compare_status_label.pack(side=tk.LEFT)
    
    def _log(self, message: str):
        """向日志文本框添加消息
        
        Args:
            message: 要添加的日志消息
        """
        try:
            # 临时启用文本框编辑状态
            self.log_text.configure(state=tk.NORMAL)
            # 在末尾添加消息
            self.log_text.insert(tk.END, message + "\n")
            # 自动滚动到最新消息
            self.log_text.see(tk.END)
            # 恢复只读状态
            self.log_text.configure(state=tk.DISABLED)
            # 更新界面
            self.root.update_idletasks()
        except tk.TclError:
            # 如果界面已销毁，忽略错误
            pass
    
    def _clear_log(self):
        """清空日志文本框"""
        try:
            # 临时启用文本框编辑状态
            self.log_text.configure(state=tk.NORMAL)
            # 清空所有内容
            self.log_text.delete(1.0, tk.END)
            # 恢复只读状态
            self.log_text.configure(state=tk.DISABLED)
        except tk.TclError:
            # 如果界面已销毁，忽略错误
            pass
    
    def _update_progress(self, progress: float, line_count: int):
        """更新解析进度
        
        Args:
            progress: 进度百分比(0-100)
            line_count: 已处理的行数
        """
        try:
            # 获取当前日志内容
            content = self.log_text.get("1.0", tk.END)
            lines = content.strip().split('\n')
            
            # 查找并更新进度行
            for i in range(len(lines) - 1, -1, -1):
                if lines[i].startswith("进度:"):
                    lines[i] = f"进度: {progress:.1f}% (已处理 {line_count:,} 行)"
                    break
            
            # 重新写入更新后的内容
            self.log_text.configure(state=tk.NORMAL)
            self.log_text.delete("1.0", tk.END)
            self.log_text.insert(tk.END, '\n'.join(lines) + '\n')
            self.log_text.see(tk.END)
            self.log_text.configure(state=tk.DISABLED)
            self.root.update_idletasks()
        except tk.TclError:
            # 如果界面已销毁，忽略错误
            pass
    
    def _on_file_list_scroll(self, event):
        """文件列表鼠标滚轮事件处理，实现每次只滚动一行
        
        Args:
            event: 鼠标事件对象
        """
        # 获取当前可见的第一个项目索引
        first_visible = self.compare_file_listbox.nearest(0)
        
        # 根据滚轮方向调整滚动位置
        if event.delta > 0:
            # 向上滚动，每次只滚动一行
            self.compare_file_listbox.see(max(0, first_visible - 1))
        else:
            # 向下滚动，每次只滚动一行
            self.compare_file_listbox.see(first_visible + 1)
        
        # 返回 "break" 以阻止默认的滚动行为
        return "break"
    
    def _browse_asc(self):
        """浏览并选择ASC文件"""
        filename = filedialog.askopenfilename(
            title="选择ASC文件", 
            filetypes=[("ASC文件", "*.asc"), ("所有文件", "*.*")]
        )
        if filename:
            # 更新ASC文件路径输入框
            self.asc_entry.delete(0, tk.END)
            self.asc_entry.insert(0, filename)
    
    def _add_dbc(self):
        """浏览并添加DBC文件到列表"""
        filenames = filedialog.askopenfilenames(
            title="选择DBC文件", 
            filetypes=[("DBC文件", "*.dbc"), ("所有文件", "*.*")]
        )
        # 添加选中的文件到列表，避免重复
        for filename in filenames:
            if filename not in self.dbc_listbox.get(0, tk.END):
                self.dbc_listbox.insert(tk.END, filename)
    
    def _remove_dbc(self):
        """从列表中移除选中的DBC文件"""
        selection = self.dbc_listbox.curselection()
        # 从后往前删除，避免索引变化问题
        for index in reversed(selection):
            self.dbc_listbox.delete(index)
    
    def _browse_output(self):
        """浏览并选择输出目录"""
        dirname = filedialog.askdirectory(title="选择输出目录")
        if dirname:
            # 更新输出目录路径输入框
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, dirname)
    
    def _load_config(self):
        """加载配置文件"""
        try:
            # 获取配置对象
            self.config = get_config()
            # 如果配置存在，更新界面控件
            if self.config and self.config.asc_file:
                self.asc_entry.insert(0, self.config.asc_file)
                # 添加所有DBC文件到列表
                for dbc in self.config.dbc_files:
                    self.dbc_listbox.insert(tk.END, dbc)
                self.output_entry.insert(0, self.config.output_dir)
                self.sample_interval_var.set(str(self.config.sample_interval))
                self.encoding_var.set(self.config.csv_encoding)
                self.debug_var.set(self.config.debug)
                self._log("已加载配置文件")
        except FileNotFoundError:
            self._log("未找到配置文件，将使用默认设置")
        except Exception as e:
            self._log(f"加载配置失败: {type(e).__name__}: {e}")
    
    def _save_config(self):
        """保存当前配置到文件"""
        import json
        # 收集当前界面配置
        config_data = {
            "asc_file": self.asc_entry.get(),
            "dbc_files": list(self.dbc_listbox.get(0, tk.END)),
            "output_dir": self.output_entry.get(),
            "sample_interval": float(self.sample_interval_var.get()),
            "csv_encoding": self.encoding_var.get(),
            "debug": self.debug_var.get()
        }
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        try:
            # 写入配置文件
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4, ensure_ascii=False)
            self._log(f"配置已保存到: {config_path}")
            messagebox.showinfo("成功", "配置保存成功！")
        except Exception as e:
            self._log(f"保存配置失败: {type(e).__name__}: {e}")
            messagebox.showerror("错误", f"保存配置失败: {e}")
    
    def _validate_inputs(self) -> bool:
        """验证用户输入的有效性
        
        Returns:
            bool: 输入有效返回True，否则返回False
        """
        # 验证ASC文件
        asc_file = self.asc_entry.get().strip()
        if not asc_file:
            messagebox.showerror("错误", "请选择ASC文件")
            return False
        if not os.path.exists(asc_file):
            messagebox.showerror("错误", f"ASC文件不存在: {asc_file}")
            return False
        
        # 验证DBC文件
        if self.dbc_listbox.size() == 0:
            messagebox.showerror("错误", "请至少添加一个DBC文件")
            return False
        for dbc in self.dbc_listbox.get(0, tk.END):
            if not os.path.exists(dbc):
                messagebox.showerror("错误", f"DBC文件不存在: {dbc}")
                return False
        
        # 验证输出目录
        output_dir = self.output_entry.get().strip()
        if not output_dir:
            messagebox.showerror("错误", "请选择输出目录")
            return False
        
        # 验证采样间隔
        try:
            sample_interval = float(self.sample_interval_var.get())
            if sample_interval <= 0:
                messagebox.showerror("错误", "采样间隔必须大于0")
                return False
        except ValueError:
            messagebox.showerror("错误", "采样间隔必须是有效的数字")
            return False
        
        return True
    
    def _start_convert(self):
        """开始转换过程
        
        验证输入，检查转换状态，然后启动转换线程
        """
        # 验证输入
        if not self._validate_inputs():
            return
        
        # 检查是否已有转换在进行
        if self.is_converting:
            messagebox.showwarning("提示", "转换正在进行中，请稍候...")
            return
        
        # 设置转换状态
        self.is_converting = True
        self.convert_btn.configure(state=tk.DISABLED)
        self._clear_log()
        
        # 启动转换线程，避免阻塞UI
        thread = threading.Thread(target=self._do_convert, daemon=True)
        thread.start()
    
    def _do_convert(self):
        """执行实际的转换过程
        
        在后台线程中运行，执行ASC到CSV的完整转换流程
        """
        dbc_loader = None
        asc_parser = None
        data_processor = None
        
        try:
            # 创建配置对象
            config = Config(
                asc_file=self.asc_entry.get(),
                dbc_files=list(self.dbc_listbox.get(0, tk.END)),
                output_dir=self.output_entry.get(),
                sample_interval=float(self.sample_interval_var.get()),
                csv_encoding=self.encoding_var.get(),
                debug=self.debug_var.get()
            )
            
            self._log("开始转换...")
            self._log(f"采样间隔: {config.sample_interval}秒")
            self._log("")
            
            # 加载DBC文件
            self._log("正在加载DBC文件...")
            dbc_loader = DBCLoader()
            if not dbc_loader.load(config.dbc_files):
                self._log("DBC文件加载失败")
                return
            
            self._log(f"总消息定义数: {dbc_loader.get_message_count()}")
            self._log(f"总信号定义数: {dbc_loader.get_signal_count()}")
            self._log("")
            
            # 解析ASC文件
            self._log("正在解析ASC文件...")
            self._log("进度: 0%")
            
            # 定义进度回调函数
            def progress_callback(progress: float, line_count: int):
                self.root.after(0, lambda: self._update_progress(progress, line_count))
            
            # 创建ASC解析器并解析文件
            asc_parser = ASCParser(sample_interval=config.sample_interval, debug=config.debug)
            if not asc_parser.parse(config.asc_file, dbc_loader.message_map, progress_callback):
                self._log("ASC文件解析失败")
                return
            
            # 获取解析统计信息
            original_count, sampled_count, signal_count = asc_parser.get_statistics()
            self._log(f"解析完成：原始数据点数: {original_count}, 采样后时间点数: {sampled_count}, 实际信号数: {signal_count}")
            self._log("")
            
            # 处理数据
            self._log("正在处理数据...")
            data_processor = DataProcessor()
            data_processor.aggregate(asc_parser.sampled_data)
            
            signal_count = len(asc_parser.found_signals)
            self._log(f"  聚合完成，共 {signal_count} 个信号")
            
            data_processor.classify_signals(asc_parser.found_signals)
            self._log(f"  分类完成，共 {len(data_processor.sorted_groups)} 个分组")
            self._log("")
            
            # 创建CSV文件
            self._log("正在创建CSV文件...")
            config.create_output_dir()
            csv_writer = CSVWriter(output_dir=config.output_dir, encoding=config.csv_encoding)
            
            # 写入所有CSV文件
            created_files = csv_writer.write_all(
                sorted_groups=data_processor.sorted_groups,
                classified_signals=data_processor.classified_signals,
                sorted_timestamps=data_processor.get_sorted_timestamps(),
                aggregated_data=data_processor.aggregated_data,
                signal_info=dbc_loader.signal_info,
                statistics={'original_count': original_count, 'sampled_count': sampled_count, 'signal_count': signal_count}
            )
            
            # 输出转换结果
            self._log("")
            self._log("=" * 60)
            self._log("转换完成！")
            self._log(f"输出目录: {config.output_dir}")
            self._log("")
            self._log("生成的文件列表：")
            self._log("-" * 60)
            
            # 统计每个文件的信号数
            for file_path in created_files:
                file_name = os.path.basename(file_path)
                signal_count = 0
                try:
                    with open(file_path, 'r', encoding=config.csv_encoding) as f:
                        reader = csv.reader(f)
                        header = next(reader)
                        signal_count = len(header) - 1  # 减去时间列
                except:
                    pass
                self._log(f"  {file_name}: {signal_count} 个信号")
            
            self._log("-" * 60)
            self._log(f"总计生成 {len(created_files)} 个文件")
            self._log("=" * 60)
            
            # 更新输出目录并刷新文件列表
            self.output_dir = config.output_dir
            self.root.after(0, lambda: self._refresh_csv_files())
            self.root.after(0, lambda: self._refresh_compare_files())
            self.root.after(0, lambda: messagebox.showinfo("成功", f"转换完成！\n输出目录: {config.output_dir}"))
            
        except Exception as e:
            # 处理转换过程中的异常
            error_msg = f"{type(e).__name__}: {e}"
            self._log(f"转换失败: {error_msg}")
            if self.debug_var.get():
                self._log(traceback.format_exc())
            self.root.after(0, lambda: messagebox.showerror("错误", f"转换失败: {error_msg}"))
        
        finally:
            # 清理资源
            if asc_parser:
                asc_parser.clear()
            if data_processor:
                data_processor.clear()
            gc.collect()
            
            # 重置转换状态
            self.is_converting = False
            self.root.after(0, lambda: self.convert_btn.configure(state=tk.NORMAL))
    
    def _refresh_csv_files(self):
        """刷新可视化选项卡的CSV文件列表"""
        if self.output_dir and os.path.exists(self.output_dir):
            # 获取所有CSV文件
            csv_files = [f for f in os.listdir(self.output_dir) if f.endswith('.csv')]
            self.file_combo['values'] = csv_files
            # 如果有文件，选择第一个并加载
            if csv_files:
                self.file_combo.set(csv_files[0])
                self._on_file_selected(None)
    
    def _refresh_compare_files(self):
        """刷新对比选项卡的CSV文件列表"""
        if self.output_dir and os.path.exists(self.output_dir):
            # 获取所有CSV文件
            csv_files = [f for f in os.listdir(self.output_dir) if f.endswith('.csv')]
            # 清空并重新填充列表框
            self.compare_file_listbox.delete(0, tk.END)
            for f in csv_files:
                self.compare_file_listbox.insert(tk.END, f)
    
    def _on_file_selected(self, event):
        """文件选择事件处理
        
        Args:
            event: 事件对象（未使用）
        """
        selected = self.file_combo.get()
        if self.output_dir and selected:
            file_path = os.path.join(self.output_dir, selected)
            if os.path.exists(file_path):
                self._load_csv_file(file_path)
    
    def _load_csv_file(self, file_path: str):
        """加载CSV文件并更新界面
        
        Args:
            file_path: CSV文件路径
        """
        # 更新状态标签
        self.status_label.config(text=f"正在加载: {os.path.basename(file_path)}...")
        self.root.update()
        
        # 加载文件
        if self.data_loader.load(file_path):
            self.current_file = file_path
            
            # 获取数值列
            numeric_cols = self.data_loader.get_numeric_columns()
            
            # 保存所有列用于搜索筛选
            self._all_columns = numeric_cols
            
            # 更新列选择下拉框
            self.column_combo['values'] = numeric_cols
            if numeric_cols:
                self.column_combo.set(numeric_cols[0])
                self.current_column = numeric_cols[0]
            
            # 更新搜索状态
            self.column_search_status.config(text=f"共 {len(numeric_cols)} 列")
            
            # 清空搜索框
            self.column_search_var.set(self._search_placeholder)
            
            # 更新图表
            self._update_chart()
            self.status_label.config(text=f"已加载: {os.path.basename(file_path)}")
        else:
            self.status_label.config(text="加载失败")
    
    def _on_column_search_changed(self, *args):
        """列搜索内容变化事件处理，实时筛选数据列"""
        search_text = self.column_search_var.get().lower()
        
        # 如果是占位符文本，不进行搜索
        if search_text == self._search_placeholder.lower():
            return
        
        # 如果搜索框为空，显示所有列
        if not search_text:
            self.column_combo['values'] = self._all_columns
            self.column_search_status.config(text=f"共 {len(self._all_columns)} 列")
            return
        
        # 筛选包含搜索文本的列（不区分大小写）
        filtered_columns = [col for col in self._all_columns if search_text in col.lower()]
        
        # 更新下拉框选项
        self.column_combo['values'] = filtered_columns
        
        # 更新搜索状态
        if filtered_columns:
            self.column_search_status.config(text=f"找到 {len(filtered_columns)} 列")
            # 如果只有一个匹配项，自动选中
            if len(filtered_columns) == 1:
                self.column_combo.set(filtered_columns[0])
                self.current_column = filtered_columns[0]
                self._update_chart()
        else:
            self.column_search_status.config(text="无匹配结果")
    
    def _on_search_focus_in(self, event):
        """搜索框获得焦点时清除占位符"""
        if self.column_search_var.get() == self._search_placeholder:
            self.column_search_var.set("")
    
    def _on_search_focus_out(self, event):
        """搜索框失去焦点时恢复占位符"""
        if not self.column_search_var.get():
            self.column_search_var.set(self._search_placeholder)
    
    def _on_column_selected(self, event):
        """列选择事件处理
        
        Args:
            event: 事件对象（未使用）
        """
        self.current_column = self.column_combo.get()
        self._update_chart()
    
    def _on_zoom_changed(self, value):
        """缩放变化事件处理
        
        Args:
            value: 缩放值
        """
        self.zoom_level = float(value)
        self.zoom_label.config(text=f"{int(self.zoom_level * 100)}%")
        self._debounce_chart_update()
    
    def _on_scroll_changed(self, value):
        """滚动位置变化事件处理
        
        Args:
            value: 滚动位置值(0-100)
        """
        self.scroll_position = float(value) / 100.0
        self._debounce_chart_update()
    
    def _debounce_chart_update(self):
        """防抖更新数据可视化图表"""
        import time
        current_time = time.time() * 1000
        
        if current_time - self._last_chart_update < self._debounce_delay:
            if not self._chart_update_pending:
                self._chart_update_pending = True
                self.root.after(self._debounce_delay, self._do_chart_update)
        else:
            self._do_chart_update()
    
    def _do_chart_update(self):
        """执行图表更新"""
        import time
        self._chart_update_pending = False
        self._last_chart_update = time.time() * 1000
        self._update_chart()
    
    def _debounce_compare_update(self):
        """防抖更新数据对比图表"""
        import time
        current_time = time.time() * 1000
        
        if current_time - self._last_compare_update < self._debounce_delay:
            if not self._compare_update_pending:
                self._compare_update_pending = True
                self.root.after(self._debounce_delay, self._do_compare_update)
        else:
            self._do_compare_update()
    
    def _do_compare_update(self):
        """执行对比图表更新"""
        import time
        self._compare_update_pending = False
        self._last_compare_update = time.time() * 1000
        self._generate_compare_chart()
    
    def _on_mouse_scroll(self, event):
        """鼠标滚轮事件处理，以鼠标位置为中心进行缩放
        
        Args:
            event: 鼠标事件对象
        """
        if event.inaxes:
            # 获取当前鼠标位置
            x_mouse = event.xdata
            
            # 保存当前的缩放级别
            old_zoom = self.zoom_level
            
            # 根据滚轮方向调整缩放级别
            if event.button == 'up':
                new_zoom = min(5.0, self.zoom_level * 1.1)
            else:
                new_zoom = max(0.1, self.zoom_level / 1.1)
            
            # 如果缩放级别没有变化，直接返回
            if abs(new_zoom - old_zoom) < 0.001:
                return
            
            self.zoom_level = new_zoom
            
            # 计算以鼠标位置为中心的新滚动位置
            if x_mouse is not None and self.data_loader.data:
                time_col = self.data_loader.get_time_column()
                if time_col:
                    time_data = self.data_loader.data[time_col]
                    total_points = len(time_data)
                    
                    if total_points > 0:
                        # 计算鼠标位置对应的数据索引
                        mouse_idx = 0
                        for i, t in enumerate(time_data):
                            if t is not None and t >= x_mouse:
                                mouse_idx = i
                                break
                        
                        # 计算新的可见范围
                        visible_points = max(1, int(total_points / self.zoom_level))
                        
                        # 计算新的滚动位置，使鼠标位置保持在相对相同的位置
                        new_start = max(0, min(mouse_idx - visible_points // 2, total_points - visible_points))
                        self.scroll_position = new_start / max(1, total_points - visible_points)
                        self.scroll_scale.set(self.scroll_position * 100)
            
            # 更新界面
            self.zoom_scale.set(self.zoom_level)
            self.zoom_label.config(text=f"{int(self.zoom_level * 100)}%")
            self._update_chart()
    
    def _reset_zoom(self):
        """重置缩放和滚动位置到默认值"""
        self.zoom_level = 1.0
        self.scroll_position = 0.0
        self.zoom_scale.set(1.0)
        self.scroll_scale.set(0)
        self.zoom_label.config(text="100%")
        self._update_chart()
    
    def _toggle_crosshair(self):
        """切换十字参考线显示状态"""
        self.crosshair_enabled = self.crosshair_var.get()
        # 如果禁用十字参考线，清除所有相关元素
        if not self.crosshair_enabled:
            if self.crosshair_vline:
                self.crosshair_vline.remove()
                self.crosshair_vline = None
            if self.crosshair_hline:
                self.crosshair_hline.remove()
                self.crosshair_hline = None
            if self.coord_annotation:
                self.coord_annotation.remove()
                self.coord_annotation = None
            self.coord_label.config(text="")
            self.canvas.draw()
    
    def _on_mouse_move(self, event):
        """鼠标移动事件处理，用于更新十字参考线和坐标显示
        
        Args:
            event: 鼠标事件对象
        """
        # 如果十字参考线未启用或鼠标不在图表内，清除参考线
        if not self.crosshair_enabled or not event.inaxes:
            if self.crosshair_vline:
                self.crosshair_vline.remove()
                self.crosshair_vline = None
            if self.crosshair_hline:
                self.crosshair_hline.remove()
                self.crosshair_hline = None
            if self.coord_annotation:
                self.coord_annotation.remove()
                self.coord_annotation = None
            self.coord_label.config(text="")
            self.canvas.draw()
            return
        
        # 获取鼠标坐标
        x_mouse, y_mouse = event.xdata, event.ydata
        if x_mouse is None or y_mouse is None:
            return
        
        # 更新或创建垂直参考线
        if self.crosshair_vline:
            self.crosshair_vline.set_xdata([x_mouse, x_mouse])
        else:
            self.crosshair_vline = self.ax.axvline(x=x_mouse, color='gray', linestyle='--', linewidth=1, alpha=0.7)
        
        # 获取鼠标x坐标处的曲线y值
        y_curve = self._get_curve_y_at_x(x_mouse)
        if y_curve is not None:
            # 如果找到曲线上的点，使用曲线y值
            y_display = y_curve
            if self.crosshair_hline:
                self.crosshair_hline.set_ydata([y_curve, y_curve])
            else:
                self.crosshair_hline = self.ax.axhline(y=y_curve, color='gray', linestyle='--', linewidth=1, alpha=0.7)
        else:
            # 否则使用鼠标y坐标
            y_display = y_mouse
            if self.crosshair_hline:
                self.crosshair_hline.set_ydata([y_mouse, y_mouse])
            else:
                self.crosshair_hline = self.ax.axhline(y=y_mouse, color='gray', linestyle='--', linewidth=1, alpha=0.7)
        
        # 计算坐标标注的位置
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        x_range = xlim[1] - xlim[0]
        y_range = ylim[1] - ylim[0]
        
        offset_x = x_range * 0.02
        offset_y = y_range * 0.02
        
        annot_x = x_mouse + offset_x
        annot_y = y_display - offset_y
        
        # 确保标注不会超出图表边界
        if annot_x > xlim[1] - x_range * 0.15:
            annot_x = x_mouse - x_range * 0.15
        if annot_y < ylim[0] + y_range * 0.1:
            annot_y = y_display + y_range * 0.1
        
        # 更新或创建坐标标注
        if self.coord_annotation:
            self.coord_annotation.xy = (x_mouse, y_display)
            self.coord_annotation.set_position((annot_x, annot_y))
            self.coord_annotation.set_text(f"X: {x_mouse:.3f}\nY: {y_display:.3f}")
        else:
            self.coord_annotation = self.ax.annotate(
                f"X: {x_mouse:.3f}\nY: {y_display:.3f}",
                xy=(x_mouse, y_display),
                xytext=(annot_x, annot_y),
                fontsize=9,
                bbox=dict(boxstyle='round,pad=0.3', facecolor='lightyellow', edgecolor='gray', alpha=0.9),
                horizontalalignment='left',
                verticalalignment='top'
            )
        
        # 更新坐标标签
        self.coord_label.config(text=f"坐标: X={x_mouse:.4f}, Y={y_display:.4f}")
        self.canvas.draw_idle()
    
    def _get_curve_y_at_x(self, x_target: float) -> Optional[float]:
        """获取当前图表中曲线在指定x坐标处的y值
        
        Args:
            x_target: 目标x坐标
            
        Returns:
            Optional[float]: 对应的y值，如果没有找到则返回None
        """
        if not self.current_column or not self.data_loader.data:
            return None
        
        time_col = self.data_loader.get_time_column()
        if not time_col:
            return None
        
        time_data = self.data_loader.data[time_col]
        
        selected_columns = [self.current_column]
        
        # 遍历所有选中的列，查找匹配的x坐标
        for col in selected_columns:
            if col in self.data_loader.data:
                y_data = self.data_loader.data[col]
                
                # 查找与目标x坐标最接近的点
                for i, t in enumerate(time_data):
                    if t is not None and abs(t - x_target) < 0.001:
                        if y_data[i] is not None:
                            return y_data[i]
        
        return None
    
    def _update_chart(self):
        """更新数据可视化图表"""
        # 检查是否有有效的数据
        if not self.current_column or not self.data_loader.data:
            return
        
        # 清除当前图表
        self.ax.clear()
        
        # 获取时间列
        time_col = self.data_loader.get_time_column()
        if not time_col:
            return
        
        time_data = self.data_loader.data[time_col]
        
        # 获取要显示的列
        selected_columns = [self.current_column]
        
        # 计算可见数据点数量
        total_points = len(time_data)
        visible_points = max(1, int(total_points / self.zoom_level))
        
        # 计算数据切片范围
        start_idx = int(self.scroll_position * (total_points - visible_points))
        start_idx = max(0, min(start_idx, total_points - visible_points))
        end_idx = min(start_idx + visible_points, total_points)
        
        # 绘制数据
        for col in selected_columns:
            if col in self.data_loader.data:
                # 获取数据切片
                y_data = self.data_loader.data[col][start_idx:end_idx]
                x_data = time_data[start_idx:end_idx]
                
                # 实现数据存在性检测：分段绘制连续的有效数据
                # 找出所有有效数据点的索引
                valid_indices = [i for i, v in enumerate(y_data) if v is not None]
                
                if valid_indices:
                    # 处理标签名称，去除多余信息
                    label = col.split('[')[0] if '[' in col else col
                    label = label.split('::')[-1] if '::' in label else label
                    
                    # 分段绘制：将连续的有效数据段分开绘制
                    segments = []
                    current_segment = []
                    
                    for i, idx in enumerate(valid_indices):
                        if not current_segment:
                            current_segment.append(idx)
                        else:
                            # 检查是否连续（允许间隔1个点，因为可能有小的数据缺失）
                            if idx - valid_indices[i-1] <= 2:
                                current_segment.append(idx)
                            else:
                                # 不连续，保存当前段并开始新段
                                segments.append(current_segment)
                                current_segment = [idx]
                    
                    if current_segment:
                        segments.append(current_segment)
                    
                    # 绘制每个连续的数据段
                    for segment in segments:
                        if len(segment) > 0:
                            x_segment = [x_data[i] for i in segment]
                            y_segment = [y_data[i] for i in segment]
                            
                            # 只为第一个段添加标签，避免图例重复
                            seg_label = label if segment == segments[0] else None
                            self.ax.plot(x_segment, y_segment, label=seg_label, 
                                        linewidth=1.5, antialiased=True)
        
        # 设置图表标签
        self.ax.set_xlabel(time_col, fontsize=10)
        self.ax.set_ylabel("数值", fontsize=10)
        
        # 设置图表标题
        if self.current_file:
            self.ax.set_title(os.path.basename(self.current_file), fontsize=12)
        
        # 添加网格
        self.ax.grid(True, linestyle='--', alpha=0.7)
        
        # 重置十字参考线
        self.crosshair_vline = None
        self.crosshair_hline = None
        self.coord_annotation = None
        
        # 更新图表
        self.figure.tight_layout()
        self.canvas.draw()
    
    def _generate_compare_chart(self):
        """生成数据对比图表"""
        # 获取选中的文件
        selected_files = self.compare_file_listbox.curselection()
        if not selected_files:
            messagebox.showwarning("提示", "请至少选择一个文件")
            return
        
        # 获取选中的数据列
        selected_columns = [col for col, var in self.compare_column_vars.items() if var.get()]
        if not selected_columns:
            messagebox.showwarning("提示", "请至少选择一个数据列")
            return
        
        # 清除当前对比图表
        self.compare_ax.clear()
        
        # 获取颜色方案
        colors = plt.cm.tab10.colors
        color_idx = 0
        
        # 获取选中的文件名
        file_names = [self.compare_file_listbox.get(i) for i in selected_files]
        
        # 处理每个选中的文件
        for file_name in file_names:
            file_path = os.path.join(self.output_dir, file_name)
            loader = CSVDataLoader()
            
            # 加载文件
            if not loader.load(file_path):
                continue
            
            # 获取时间列
            time_col = loader.get_time_column()
            if not time_col:
                continue
            
            time_data = loader.data[time_col]
            
            # 保存时间数据用于鼠标滚轮缩放
            self._compare_time_data = time_data
            
            # 计算可见数据点数量
            total_points = len(time_data)
            visible_points = max(1, int(total_points / self.compare_zoom_level))
            
            # 使用水平滚动位置计算数据切片范围
            start_idx = int(self.compare_scroll_position * (total_points - visible_points))
            start_idx = max(0, min(start_idx, total_points - visible_points))
            end_idx = min(start_idx + visible_points, total_points)
            
            # 处理每个选中的数据列
            for target_col in selected_columns:
                # 查找匹配的列名
                matching_col = None
                for col in loader.columns:
                    if target_col in col:
                        matching_col = col
                        break
                
                if not matching_col:
                    continue
                
                # 获取数据
                y_data = loader.data[matching_col][start_idx:end_idx]
                x_data = time_data[start_idx:end_idx]
                
                # 实现数据存在性检测：分段绘制连续的有效数据
                valid_indices = [i for i, v in enumerate(y_data) if v is not None]
                
                if valid_indices:
                    # 创建标签
                    label = f"{file_name.replace('.csv', '')} - {target_col}"
                    
                    # 分段绘制：将连续的有效数据段分开绘制
                    segments = []
                    current_segment = []
                    
                    for i, idx in enumerate(valid_indices):
                        if not current_segment:
                            current_segment.append(idx)
                        else:
                            # 检查是否连续（允许间隔1个点）
                            if idx - valid_indices[i-1] <= 2:
                                current_segment.append(idx)
                            else:
                                segments.append(current_segment)
                                current_segment = [idx]
                    
                    if current_segment:
                        segments.append(current_segment)
                    
                    # 绘制每个连续的数据段
                    for segment in segments:
                        if len(segment) > 0:
                            x_segment = [x_data[i] for i in segment]
                            y_segment = [y_data[i] for i in segment]
                            
                            seg_label = label if segment == segments[0] else None
                            self.compare_ax.plot(x_segment, y_segment, label=seg_label, 
                                                linewidth=1.5, color=colors[color_idx % len(colors)],
                                                antialiased=True)
                    color_idx += 1
        
        # 设置图表标签和标题
        self.compare_ax.set_xlabel("时间 [s]", fontsize=10)
        self.compare_ax.set_ylabel("数值", fontsize=10)
        self.compare_ax.set_title("多文件数据对比", fontsize=12)
        self.compare_ax.legend(loc='upper right', fontsize=8)
        self.compare_ax.grid(True, linestyle='--', alpha=0.7)
        
        # 更新图表
        self.compare_figure.tight_layout()
        self.compare_canvas.draw()
        
        # 更新状态标签
        self.compare_status_label.config(text=f"已生成对比图 - 文件: {len(file_names)}, 数据列: {len(selected_columns)}")
    
    def _on_compare_zoom_changed(self, value):
        """对比图表缩放变化事件处理
        
        Args:
            value: 缩放值
        """
        self.compare_zoom_level = float(value)
        self.compare_zoom_label.config(text=f"{int(self.compare_zoom_level * 100)}%")
        # 使用防抖机制重新生成图表
        self._debounce_compare_update()
    
    def _on_compare_scroll_changed(self, value):
        """对比图表水平滚动变化事件处理
        
        Args:
            value: 滚动位置值（0-100）
        """
        self.compare_scroll_position = float(value) / 100.0
        # 使用防抖机制重新生成图表
        self._debounce_compare_update()
    
    def _on_compare_mouse_scroll(self, event):
        """对比图表鼠标滚轮事件处理，以鼠标位置为中心进行缩放
        
        Args:
            event: 鼠标事件对象
        """
        if event.inaxes:
            # 获取当前鼠标位置
            x_mouse = event.xdata
            
            # 保存当前的滚动比例（相对于总数据量）
            old_zoom = self.compare_zoom_level
            
            # 根据滚轮方向调整缩放级别
            if event.button == 'up':
                new_zoom = min(5.0, self.compare_zoom_level * 1.1)
            else:
                new_zoom = max(0.1, self.compare_zoom_level / 1.1)
            
            # 如果缩放级别没有变化，直接返回
            if abs(new_zoom - old_zoom) < 0.001:
                return
            
            self.compare_zoom_level = new_zoom
            
            # 计算以鼠标位置为中心的新滚动位置
            if x_mouse is not None:
                # 获取当前显示的数据范围
                total_points = len(self._compare_time_data) if hasattr(self, '_compare_time_data') else 0
                if total_points > 0:
                    # 计算鼠标位置对应的数据索引
                    mouse_idx = 0
                    for i, t in enumerate(self._compare_time_data):
                        if t is not None and t >= x_mouse:
                            mouse_idx = i
                            break
                    
                    # 计算新的可见范围
                    visible_points = max(1, int(total_points / self.compare_zoom_level))
                    
                    # 计算新的滚动位置，使鼠标位置保持在相对相同的位置
                    new_start = max(0, min(mouse_idx - visible_points // 2, total_points - visible_points))
                    self.compare_scroll_position = new_start / max(1, total_points - visible_points)
                    self.compare_scroll_scale.set(self.compare_scroll_position * 100)
            
            # 更新界面
            self.compare_zoom_scale.set(self.compare_zoom_level)
            self.compare_zoom_label.config(text=f"{int(self.compare_zoom_level * 100)}%")
            self._generate_compare_chart()
    
    def _reset_compare_zoom(self):
        """重置对比图表缩放级别到默认值"""
        self.compare_zoom_level = 1.0
        self.compare_zoom_scale.set(1.0)
        self.compare_zoom_label.config(text="100%")
        self._generate_compare_chart()
    
    def _reset_compare_scroll(self):
        """重置对比图表水平滚动位置到默认值"""
        self.compare_scroll_position = 0.0
        self.compare_scroll_scale.set(0)
        self._generate_compare_chart()
    
    def _on_closing(self):
        """窗口关闭事件处理"""
        if self.is_converting:
            # 如果转换正在进行，询问用户是否确认退出
            if messagebox.askyesno("确认", "转换正在进行中，确定要退出吗？"):
                self.root.quit()
        else:
            self.root.quit()


def main():
    """程序入口函数
    
    创建Tkinter根窗口和主应用程序实例，并启动事件循环
    """
    # 创建Tkinter根窗口
    root = tk.Tk()
    # 创建主应用程序实例
    app = MainApplication(root)
    # 启动Tkinter事件循环
    root.mainloop()


if __name__ == "__main__":
    # 当脚本作为主程序运行时，调用main函数
    main()