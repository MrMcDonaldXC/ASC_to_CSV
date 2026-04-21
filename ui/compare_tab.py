# asc_to_csv/ui/compare_tab.py
"""
数据对比标签页模块
提供多文件数据对比功能界面
"""

import os
import time
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, List, Dict

from .base import BaseTab
from core.csv_loader import CSVDataLoader, MULTI_SELECT_COLUMNS
from core.chart_manager import ChartManager


class CompareTab(BaseTab):
    """
    数据对比标签页
    
    提供多文件数据对比功能
    
    Attributes:
        compare_file_listbox: 文件列表框
        compare_column_vars: 数据列选择变量字典
        chart_manager: 图表管理器
    """
    
    def __init__(self, parent: tk.Widget, app_context: dict):
        """
        初始化对比标签页

        Args:
            parent: 父容器
            app_context: 应用上下文
        """
        self.compare_file_listbox: Optional[tk.Listbox] = None
        self.compare_column_vars: Dict[str, tk.BooleanVar] = {}
        self.chart_manager: Optional[ChartManager] = None

        self.compare_zoom_level: float = 1.0
        self.compare_scroll_position: float = 0.0

        self._compare_time_data: List = []
        self._loaded_files: Dict[str, CSVDataLoader] = {}

        self._compare_update_pending: bool = False
        self._last_compare_update: float = 0
        self._debounce_delay: int = 50
        self._listbox_hover: bool = False

        self._max_data_points: int = 100000

        self.compare_zoom_scale: Optional[ttk.Scale] = None
        self.compare_zoom_label: Optional[ttk.Label] = None
        self.compare_scroll_scale: Optional[ttk.Scale] = None
        self.compare_status_label: Optional[ttk.Label] = None

        super().__init__(parent, app_context)
    
    def _create_widgets(self):
        """创建界面组件"""
        control_frame = ttk.LabelFrame(self, text="对比设置", padding="10")
        control_frame.pack(fill=tk.X, pady=(0, 5))
        
        self._create_file_section(control_frame)
        self._create_column_section(control_frame)
        self._create_control_section(control_frame)
        
        chart_frame = ttk.LabelFrame(self, text="对比图表", padding="5")
        chart_frame.pack(fill=tk.BOTH, expand=True)
        
        self.chart_manager = ChartManager(chart_frame)
        self.chart_manager.get_widget().pack(fill=tk.BOTH, expand=True)
        self.chart_manager.add_toolbar(chart_frame)
        
        self.chart_manager.bind_scroll(self._on_mouse_scroll)
        
        status_frame = ttk.Frame(self)
        status_frame.pack(fill=tk.X, pady=(5, 0))
        self.compare_status_label = ttk.Label(status_frame, text="请选择文件和数据列进行对比")
        self.compare_status_label.pack(side=tk.LEFT)
    
    def _create_file_section(self, parent: ttk.Frame):
        """创建文件选择区域"""
        file_frame = ttk.Frame(parent)
        file_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(file_frame, text="选择文件:").pack(side=tk.LEFT)
        
        listbox_frame = ttk.Frame(file_frame)
        listbox_frame.pack(side=tk.LEFT, padx=5)
        
        self.compare_file_listbox = tk.Listbox(listbox_frame, height=4, selectmode=tk.MULTIPLE, width=40)
        self.compare_file_listbox.pack(side=tk.LEFT)
        
        self.compare_file_listbox.bind('<MouseWheel>', self._on_file_list_scroll)
        self.compare_file_listbox.bind('<Button-4>', self._on_file_list_scroll_linux)
        self.compare_file_listbox.bind('<Button-5>', self._on_file_list_scroll_linux)
        
        self.compare_file_listbox.bind('<Enter>', self._on_listbox_enter)
        self.compare_file_listbox.bind('<Leave>', self._on_listbox_leave)
        
        ttk.Button(file_frame, text="刷新文件", command=self._refresh_files).pack(side=tk.LEFT, padx=5)
    
    def _create_column_section(self, parent: ttk.Frame):
        """创建数据列选择区域"""
        column_frame = ttk.Frame(parent)
        column_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(column_frame, text="选择数据列:").pack(side=tk.LEFT)
        
        self.compare_column_frame = ttk.Frame(column_frame)
        self.compare_column_frame.pack(side=tk.LEFT, padx=5)
        
        for i, col_name in enumerate(MULTI_SELECT_COLUMNS):
            var = tk.BooleanVar(value=False)
            self.compare_column_vars[col_name] = var
            cb = ttk.Checkbutton(self.compare_column_frame, text=col_name, variable=var)
            cb.grid(row=0, column=i, padx=5)
    
    def _create_control_section(self, parent: ttk.Frame):
        """创建控制按钮区域"""
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(btn_frame, text="生成对比图", command=self._generate_chart).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(btn_frame, text="缩放:").pack(side=tk.LEFT, padx=(20, 0))
        self.compare_zoom_scale = ttk.Scale(btn_frame, from_=0.1, to=5.0, value=1.0,
                                             orient=tk.HORIZONTAL, length=100,
                                             command=self._on_zoom_changed)
        self.compare_zoom_scale.pack(side=tk.LEFT, padx=5)
        self.compare_zoom_label = ttk.Label(btn_frame, text="100%", width=6)
        self.compare_zoom_label.pack(side=tk.LEFT)
        
        ttk.Button(btn_frame, text="重置缩放", command=self._reset_zoom).pack(side=tk.LEFT, padx=10)
        
        ttk.Label(btn_frame, text="水平滚动:").pack(side=tk.LEFT, padx=(20, 0))
        self.compare_scroll_scale = ttk.Scale(btn_frame, from_=0, to=100, value=0,
                                               orient=tk.HORIZONTAL, length=150,
                                               command=self._on_scroll_changed)
        self.compare_scroll_scale.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text="重置滚动", command=self._reset_scroll).pack(side=tk.LEFT, padx=10)
    
    def _on_listbox_enter(self, event):
        """鼠标进入列表框时获取焦点"""
        self._listbox_hover = True
        self.compare_file_listbox.focus_set()
    
    def _on_listbox_leave(self, event):
        """鼠标离开列表框"""
        self._listbox_hover = False
    
    def _on_file_list_scroll(self, event):
        """
        文件列表滚动事件处理 (Windows/macOS)
        
        支持鼠标滚轮在文件列表中进行上下滚动操作，
        实现与方向键一致的滚动效果。
        
        Args:
            event: 鼠标滚轮事件对象
            
        Returns:
            str: "break" 阻止事件继续传播
        """
        if not self.compare_file_listbox:
            return "break"
        
        size = self.compare_file_listbox.size()
        if size == 0:
            return "break"
        
        first_visible = self.compare_file_listbox.nearest(0)
        last_visible = self.compare_file_listbox.nearest(self.compare_file_listbox.winfo_height())
        
        scroll_amount = 1
        
        if event.delta > 0:
            new_first = max(0, first_visible - scroll_amount)
            self.compare_file_listbox.see(new_first)
            self.compare_file_listbox.yview_scroll(-scroll_amount, "units")
        else:
            new_first = min(size - 1, first_visible + scroll_amount)
            self.compare_file_listbox.see(new_first)
            self.compare_file_listbox.yview_scroll(scroll_amount, "units")
        
        return "break"
    
    def _on_file_list_scroll_linux(self, event):
        """
        文件列表滚动事件处理 (Linux)
        
        Linux系统使用Button-4(向上)和Button-5(向下)事件
        来处理鼠标滚轮操作。
        
        Args:
            event: 鼠标按钮事件对象
            
        Returns:
            str: "break" 阻止事件继续传播
        """
        if not self.compare_file_listbox:
            return "break"
        
        size = self.compare_file_listbox.size()
        if size == 0:
            return "break"
        
        scroll_amount = 1
        
        if event.num == 4:
            self.compare_file_listbox.yview_scroll(-scroll_amount, "units")
        elif event.num == 5:
            self.compare_file_listbox.yview_scroll(scroll_amount, "units")
        
        return "break"
    
    def _refresh_files(self):
        """刷新文件列表"""
        output_dir = self.app_context.get('output_dir', '')
        if not output_dir or not os.path.exists(output_dir):
            messagebox.showwarning("提示", "请先进行数据转换或设置输出目录")
            return
        
        csv_files = [f for f in os.listdir(output_dir) if f.endswith('.csv')]
        
        self.compare_file_listbox.delete(0, tk.END)
        for f in csv_files:
            self.compare_file_listbox.insert(tk.END, f)
        
        self.compare_status_label.config(text=f"已加载 {len(csv_files)} 个文件")
    
    def _generate_chart(self):
        """生成对比图表"""
        selected_files = self.compare_file_listbox.curselection()
        if not selected_files:
            messagebox.showwarning("提示", "请至少选择一个文件")
            return

        selected_columns = [col for col, var in self.compare_column_vars.items() if var.get()]
        if not selected_columns:
            messagebox.showwarning("提示", "请至少选择一个数据列")
            return

        self.chart_manager.clear()

        import matplotlib.pyplot as plt
        colors = plt.cm.tab10.colors
        color_idx = 0

        file_names = [self.compare_file_listbox.get(i) for i in selected_files]
        total_files = len(file_names)
        max_points_in_any_file = 0

        for file_name in file_names:
            output_dir = self.app_context.get('output_dir', '')
            file_path = os.path.join(output_dir, file_name)
            loader = self._get_file_loader(file_path)

            if not loader:
                continue

            time_col = loader.get_time_column()
            if not time_col:
                continue

            time_data = loader.data[time_col]
            self._compare_time_data = time_data

            total_points = len(time_data)
            max_points_in_any_file = max(max_points_in_any_file, total_points)

            visible_points = max(1, int(total_points / self.compare_zoom_level))
            visible_points = min(visible_points, self._max_data_points)

            start_idx = int(self.compare_scroll_position * (total_points - visible_points))
            start_idx = max(0, min(start_idx, total_points - visible_points))
            end_idx = min(start_idx + visible_points, total_points)

            for target_col in selected_columns:
                matching_col = None
                for col in loader.columns:
                    if target_col in col:
                        matching_col = col
                        break

                if not matching_col:
                    continue

                y_data = loader.data[matching_col][start_idx:end_idx]
                x_data = time_data[start_idx:end_idx]

                valid_indices = [i for i, v in enumerate(y_data) if v is not None]

                if valid_indices:
                    label = f"{file_name.replace('.csv', '')} - {target_col}"

                    self.chart_manager.plot_segments(
                        x_data, y_data, label=label,
                        linewidth=1.5, color=colors[color_idx % len(colors)],
                        antialiased=True
                    )
                    color_idx += 1

        if max_points_in_any_file > self._max_data_points:
            self.chart_manager.set_max_render_points(self._max_data_points)
        else:
            self.chart_manager.set_max_render_points(max_points_in_any_file)

        self.chart_manager.set_labels("时间 [s]", "数值", "多文件数据对比")
        self.chart_manager.add_legend()
        self.chart_manager.add_grid()
        self.chart_manager.update()

        perf_info = f" (性能模式)" if max_points_in_any_file > self._max_data_points else ""
        self.compare_status_label.config(
            text=f"已生成对比图 - 文件: {len(file_names)}, 数据列: {len(selected_columns)}{perf_info}")
    
    def _on_zoom_changed(self, value):
        """缩放变化事件处理"""
        self.compare_zoom_level = float(value)
        self.compare_zoom_label.config(text=f"{int(self.compare_zoom_level * 100)}%")
        self._debounce_compare_update()
    
    def _on_scroll_changed(self, value):
        """滚动位置变化事件处理"""
        self.compare_scroll_position = float(value) / 100.0
        self._debounce_compare_update()
    
    def _debounce_compare_update(self):
        """防抖更新对比图表"""
        current_time = time.time() * 1000
        
        if current_time - self._last_compare_update < self._debounce_delay:
            if not self._compare_update_pending:
                self._compare_update_pending = True
                self.app_context['root'].after(self._debounce_delay, self._do_compare_update)
        else:
            self._do_compare_update()
    
    def _do_compare_update(self):
        """执行对比图表更新"""
        self._compare_update_pending = False
        self._last_compare_update = time.time() * 1000
        self._generate_chart()
    
    def _on_mouse_scroll(self, event):
        """鼠标滚轮事件处理"""
        if event.inaxes:
            x_mouse = event.xdata
            old_zoom = self.compare_zoom_level
            
            if event.button == 'up':
                new_zoom = min(5.0, self.compare_zoom_level * 1.1)
            else:
                new_zoom = max(0.1, self.compare_zoom_level / 1.1)
            
            if abs(new_zoom - old_zoom) < 0.001:
                return
            
            self.compare_zoom_level = new_zoom
            
            if x_mouse is not None and len(self._compare_time_data) > 0:
                total_points = len(self._compare_time_data)
                
                mouse_idx = 0
                for i, t in enumerate(self._compare_time_data):
                    if t is not None and t >= x_mouse:
                        mouse_idx = i
                        break
                
                visible_points = max(1, int(total_points / self.compare_zoom_level))
                new_start = max(0, min(mouse_idx - visible_points // 2, total_points - visible_points))
                self.compare_scroll_position = new_start / max(1, total_points - visible_points)
                self.compare_scroll_scale.set(self.compare_scroll_position * 100)
            
            self.compare_zoom_scale.set(self.compare_zoom_level)
            self.compare_zoom_label.config(text=f"{int(self.compare_zoom_level * 100)}%")
            self._generate_chart()
    
    def _reset_zoom(self):
        """重置缩放"""
        self.compare_zoom_level = 1.0
        self.compare_zoom_scale.set(1.0)
        self.compare_zoom_label.config(text="100%")
        self._generate_chart()
    
    def _reset_scroll(self):
        """重置滚动位置"""
        self.compare_scroll_position = 0.0
        self.compare_scroll_scale.set(0)
        self._generate_chart()

    def cleanup(self):
        """清理资源，防止内存泄漏"""
        if self.chart_manager:
            self.chart_manager.destroy()
            self.chart_manager = None

        for loader in self._loaded_files.values():
            loader.clear()
        self._loaded_files.clear()
        self._compare_time_data = []

    def refresh_files(self):
        """刷新文件列表（公共接口）"""
        self._refresh_files()

    def _get_file_loader(self, file_path: str) -> Optional[CSVDataLoader]:
        """
        获取或创建文件加载器（带缓存）

        Args:
            file_path: CSV文件路径

        Returns:
            CSVDataLoader或None
        """
        if file_path in self._loaded_files:
            return self._loaded_files[file_path]

        if len(self._loaded_files) >= 5:
            oldest_key = next(iter(self._loaded_files))
            old_loader = self._loaded_files.pop(oldest_key)
            old_loader.clear()

        loader = CSVDataLoader()
        if loader.load(file_path):
            self._loaded_files[file_path] = loader
            return loader

        return None
