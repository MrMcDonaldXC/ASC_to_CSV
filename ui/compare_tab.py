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
from .multi_select_combo import MultiSelectCombo
from core.csv_loader import CSVDataLoader, MULTI_SELECT_COLUMNS
from core.chart_manager import ChartManager


class CompareTab(BaseTab):
    """
    数据对比标签页
    
    提供多文件数据对比功能
    
    Attributes:
        file_combo: 多选下拉复选框组件
        compare_column_vars: 数据列选择变量字典
        chart_manager: 图表管理器
    """
    
    MAX_FILE_SELECTION = 10
    
    def __init__(self, parent: tk.Widget, app_context: dict):
        """
        初始化对比标签页
        
        Args:
            parent: 父容器
            app_context: 应用上下文
        """
        self.file_combo: Optional[MultiSelectCombo] = None
        self.compare_column_vars: Dict[str, tk.BooleanVar] = {}
        self.chart_manager: Optional[ChartManager] = None
        
        self.compare_zoom_level: float = 1.0
        self.compare_scroll_position: float = 0.0
        
        self._compare_time_data: List = []
        
        self._compare_update_pending: bool = False
        self._last_compare_update: float = 0
        self._debounce_delay: int = 50
        
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
        
        self.file_combo = MultiSelectCombo(
            file_frame,
            max_selection=self.MAX_FILE_SELECTION,
            on_selection_change=self._on_file_selection_change,
            placeholder="请选择CSV文件...",
            width=40
        )
        self.file_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(file_frame, text="刷新文件", command=self._refresh_files).pack(side=tk.LEFT, padx=5)
    
    def _on_file_selection_change(self, selected_files: List[str]):
        """
        文件选择变化回调
        
        Args:
            selected_files: 已选择的文件列表
        """
        if selected_files:
            self.compare_status_label.config(text=f"已选择 {len(selected_files)} 个文件")
        else:
            self.compare_status_label.config(text="请选择文件和数据列进行对比")
    
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
    
    def _refresh_files(self):
        """刷新文件列表"""
        output_dir = self.app_context.get('output_dir', '')
        if not output_dir or not os.path.exists(output_dir):
            messagebox.showwarning("提示", "请先进行数据转换或设置输出目录")
            return
        
        self.file_combo.set_loading(True)
        self.app_context['root'].update()
        
        csv_files = [f for f in os.listdir(output_dir) if f.endswith('.csv')]
        csv_files.sort()
        
        self.file_combo.refresh(csv_files)
        self.file_combo.set_loading(False)
        
        self.compare_status_label.config(text=f"已加载 {len(csv_files)} 个文件")
    
    def _generate_chart(self):
        """生成对比图表"""
        selected_files = self.file_combo.get_selected()
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
        
        file_names = selected_files
        
        for file_name in file_names:
            output_dir = self.app_context.get('output_dir', '')
            file_path = os.path.join(output_dir, file_name)
            loader = CSVDataLoader()
            
            if not loader.load(file_path):
                continue
            
            time_col = loader.get_time_column()
            if not time_col:
                continue
            
            time_data = loader.data[time_col]
            self._compare_time_data = time_data
            
            total_points = len(time_data)
            visible_points = max(1, int(total_points / self.compare_zoom_level))
            
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
        
        self.chart_manager.set_labels("时间 [s]", "数值", "多文件数据对比")
        self.chart_manager.add_legend()
        self.chart_manager.add_grid()
        self.chart_manager.update()
        
        self.compare_status_label.config(
            text=f"已生成对比图 - 文件: {len(file_names)}, 数据列: {len(selected_columns)}")
    
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
    
    def refresh_files(self):
        """刷新文件列表（公共接口）"""
        self._refresh_files()
