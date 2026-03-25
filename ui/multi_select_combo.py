# asc_to_csv/ui/multi_select_combo.py
"""
多选下拉复选框组件

提供类似Combobox的多选功能，支持文件多选、状态记忆、单文件取消等功能。
"""

import tkinter as tk
from tkinter import ttk
from typing import List, Callable, Optional, Set


class MultiSelectCombo(ttk.Frame):
    """
    多选下拉复选框组件
    
    外观类似Combobox，点击展开后显示复选框列表，支持多选功能。
    
    Attributes:
        max_selection (int): 最大选择数量，默认为10
        selected_items (Set[str]): 已选择的项集合
        on_selection_change (Optional[Callable]): 选择变化回调函数
    """
    
    MAX_SELECTION_DEFAULT = 10
    
    def __init__(
        self,
        parent: tk.Widget,
        max_selection: int = MAX_SELECTION_DEFAULT,
        on_selection_change: Optional[Callable[[List[str]], None]] = None,
        placeholder: str = "请选择文件...",
        width: int = 40
    ):
        """
        初始化多选下拉复选框
        
        Args:
            parent: 父容器
            max_selection: 最大选择数量
            on_selection_change: 选择变化回调函数，参数为已选择的项列表
            placeholder: 占位符文本
            width: 组件宽度
        """
        super().__init__(parent)
        
        self.max_selection = max_selection
        self.on_selection_change = on_selection_change
        self.placeholder = placeholder
        self.width = width
        
        self.selected_items: Set[str] = set()
        self.all_items: List[str] = []
        self.check_vars: dict = {}
        
        self._is_dropdown_open = False
        self._loading = False
        
        self._create_widgets()
        self._bind_events()
    
    def _create_widgets(self):
        """创建组件"""
        self.main_button = ttk.Button(
            self,
            text=self.placeholder,
            width=self.width,
            command=self._toggle_dropdown
        )
        self.main_button.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.dropdown_arrow = ttk.Label(self, text="▼", width=2)
        self.dropdown_arrow.pack(side=tk.RIGHT)
        
        self._create_dropdown_window()
    
    def _create_dropdown_window(self):
        """创建下拉窗口"""
        self.dropdown_window = tk.Toplevel(self)
        self.dropdown_window.overrideredirect(True)
        self.dropdown_window.attributes('-topmost', True)
        
        self.dropdown_frame = ttk.Frame(self.dropdown_window, relief='solid', borderwidth=1)
        self.dropdown_frame.pack(fill=tk.BOTH, expand=True)
        
        self._create_header()
        self._create_list_frame()
        self._create_footer()
        
        self.dropdown_window.withdraw()
    
    def _create_header(self):
        """创建下拉框头部"""
        header_frame = ttk.Frame(self.dropdown_frame)
        header_frame.pack(fill=tk.X, padx=2, pady=2)
        
        self.select_all_var = tk.BooleanVar(value=False)
        self.select_all_cb = ttk.Checkbutton(
            header_frame,
            text="全选",
            variable=self.select_all_var,
            command=self._toggle_select_all
        )
        self.select_all_cb.pack(side=tk.LEFT)
        
        self.clear_btn = ttk.Button(
            header_frame,
            text="清空",
            width=6,
            command=self._clear_all
        )
        self.clear_btn.pack(side=tk.RIGHT)
        
        ttk.Separator(self.dropdown_frame, orient='horizontal').pack(fill=tk.X, pady=2)
    
    def _create_list_frame(self):
        """创建列表区域"""
        list_container = ttk.Frame(self.dropdown_frame)
        list_container.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        self.canvas = tk.Canvas(list_container, height=150, width=self.width * 8)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.scrollbar = ttk.Scrollbar(list_container, orient='vertical', command=self.canvas.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.list_frame = ttk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.list_frame, anchor='nw')
        
        self.canvas.bind('<Configure>', self._on_canvas_configure)
        self.list_frame.bind('<Configure>', self._on_frame_configure)
        
        self.canvas.bind('<MouseWheel>', self._on_mousewheel)
        self.list_frame.bind('<MouseWheel>', self._on_mousewheel)
    
    def _create_footer(self):
        """创建下拉框底部"""
        footer_frame = ttk.Frame(self.dropdown_frame)
        footer_frame.pack(fill=tk.X, padx=2, pady=2)
        
        self.status_label = ttk.Label(footer_frame, text="")
        self.status_label.pack(side=tk.LEFT)
        
        self.confirm_btn = ttk.Button(
            footer_frame,
            text="确定",
            width=8,
            command=self._confirm_selection
        )
        self.confirm_btn.pack(side=tk.RIGHT)
    
    def _bind_events(self):
        """绑定事件"""
        self.main_button.bind('<Button-1>', self._toggle_dropdown)
        self.dropdown_arrow.bind('<Button-1>', lambda e: self._toggle_dropdown())
        
        self.dropdown_window.bind('<FocusOut>', self._on_focus_out)
        self.dropdown_window.bind('<Escape>', lambda e: self._close_dropdown())
        
        self.bind('<Destroy>', self._on_destroy)
    
    def _on_canvas_configure(self, event):
        """画布大小变化事件"""
        self.canvas.itemconfig(self.canvas_window, width=event.width)
    
    def _on_frame_configure(self, event):
        """框架大小变化事件"""
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))
    
    def _on_mousewheel(self, event):
        """鼠标滚轮事件"""
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')
    
    def _on_focus_out(self, event):
        """失去焦点事件"""
        try:
            if event.widget == self.dropdown_window:
                x_root = getattr(event, 'x_root', None)
                y_root = getattr(event, 'y_root', None)
                if x_root is not None and y_root is not None:
                    widget = event.widget.winfo_containing(x_root, y_root)
                    if widget is None or not self._is_child_of(widget):
                        self._close_dropdown()
        except tk.TclError:
            self._close_dropdown()
    
    def _is_child_of(self, widget) -> bool:
        """检查控件是否为本组件的子控件"""
        try:
            current = widget
            while current is not None:
                if current in (self, self.dropdown_window, self.main_button):
                    return True
                current = current.master
        except tk.TclError:
            pass
        return False
    
    def _on_destroy(self, event):
        """组件销毁事件"""
        try:
            self.dropdown_window.destroy()
        except tk.TclError:
            pass
    
    def _toggle_dropdown(self, event=None):
        """切换下拉框显示状态"""
        if self._is_dropdown_open:
            self._close_dropdown()
        else:
            self._open_dropdown()
    
    def _open_dropdown(self):
        """打开下拉框"""
        if self._is_dropdown_open:
            return
        
        self._is_dropdown_open = True
        
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()
        
        self.dropdown_window.geometry(f'+{x}+{y}')
        self.dropdown_window.deiconify()
        self.dropdown_window.lift()
        self.dropdown_window.focus_force()
        
        self.dropdown_arrow.config(text="▲")
    
    def _close_dropdown(self):
        """关闭下拉框"""
        self._is_dropdown_open = False
        self.dropdown_window.withdraw()
        self.dropdown_arrow.config(text="▼")
    
    def _toggle_select_all(self):
        """切换全选状态"""
        if self.select_all_var.get():
            items_to_select = self.all_items[:self.max_selection]
            for item in items_to_select:
                self.selected_items.add(item)
                if item in self.check_vars:
                    self.check_vars[item].set(True)
        else:
            self._clear_all()
        
        self._update_status()
        self._update_button_text()
    
    def _clear_all(self):
        """清空所有选择"""
        self.selected_items.clear()
        for var in self.check_vars.values():
            var.set(False)
        self.select_all_var.set(False)
        self._update_status()
        self._update_button_text()
    
    def _on_item_toggled(self, item: str):
        """单项选择状态变化"""
        var = self.check_vars.get(item)
        if var is None:
            return
        
        if var.get():
            if len(self.selected_items) >= self.max_selection:
                var.set(False)
                self._show_max_selection_warning()
                return
            self.selected_items.add(item)
        else:
            self.selected_items.discard(item)
        
        self._update_select_all_state()
        self._update_status()
        self._update_button_text()
    
    def _show_max_selection_warning(self):
        """显示最大选择数量警告"""
        self.status_label.config(text=f"最多选择 {self.max_selection} 个文件")
        self.after(2000, lambda: self._update_status())
    
    def _update_select_all_state(self):
        """更新全选状态"""
        if len(self.selected_items) == len(self.all_items) and len(self.all_items) > 0:
            self.select_all_var.set(True)
        else:
            self.select_all_var.set(False)
    
    def _update_status(self):
        """更新状态显示"""
        count = len(self.selected_items)
        total = len(self.all_items)
        self.status_label.config(text=f"已选择 {count}/{total} 个")
    
    def _update_button_text(self):
        """更新按钮文本"""
        if not self.selected_items:
            self.main_button.config(text=self.placeholder)
        elif len(self.selected_items) == 1:
            item = list(self.selected_items)[0]
            display_text = item if len(item) <= self.width - 3 else item[:self.width - 6] + "..."
            self.main_button.config(text=display_text)
        else:
            self.main_button.config(text=f"已选择 {len(self.selected_items)} 个文件")
    
    def _confirm_selection(self):
        """确认选择"""
        self._close_dropdown()
        if self.on_selection_change:
            self.on_selection_change(list(self.selected_items))
    
    def set_items(self, items: List[str]):
        """
        设置可选项列表
        
        Args:
            items: 可选项列表
        """
        self._loading = True
        
        self.all_items = list(items)
        
        for widget in self.list_frame.winfo_children():
            widget.destroy()
        
        self.check_vars.clear()
        
        for item in self.all_items:
            var = tk.BooleanVar(value=item in self.selected_items)
            self.check_vars[item] = var
            
            cb = ttk.Checkbutton(
                self.list_frame,
                text=item,
                variable=var,
                command=lambda i=item: self._on_item_toggled(i)
            )
            cb.pack(anchor='w', padx=5, pady=1)
        
        self._update_status()
        self._loading = False
        
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))
    
    def get_selected(self) -> List[str]:
        """
        获取已选择的项列表
        
        Returns:
            List[str]: 已选择的项列表
        """
        return list(self.selected_items)
    
    def set_selected(self, items: List[str]):
        """
        设置已选择的项
        
        Args:
            items: 要选择的项列表
        """
        self.selected_items.clear()
        
        for item in items:
            if item in self.all_items:
                self.selected_items.add(item)
        
        for item, var in self.check_vars.items():
            var.set(item in self.selected_items)
        
        self._update_select_all_state()
        self._update_status()
        self._update_button_text()
    
    def clear_selection(self):
        """清空选择"""
        self._clear_all()
    
    def refresh(self, items: List[str]):
        """
        刷新可选项列表（保持已选择状态）
        
        Args:
            items: 新的可选项列表
        """
        current_selected = self.selected_items.copy()
        self.set_items(items)
        
        valid_selected = [item for item in current_selected if item in items]
        if valid_selected:
            self.set_selected(valid_selected[:self.max_selection])
    
    def set_loading(self, loading: bool):
        """
        设置加载状态
        
        Args:
            loading: 是否正在加载
        """
        self._loading = loading
        if loading:
            self.main_button.config(text="加载中...")
            self.main_button.config(state='disabled')
        else:
            self.main_button.config(state='normal')
            self._update_button_text()
    
    def set_max_selection(self, max_count: int):
        """
        设置最大选择数量
        
        Args:
            max_count: 最大选择数量
        """
        self.max_selection = max_count
        
        if len(self.selected_items) > max_count:
            items_to_remove = list(self.selected_items)[max_count:]
            for item in items_to_remove:
                self.selected_items.discard(item)
                if item in self.check_vars:
                    self.check_vars[item].set(False)
            
            self._update_status()
            self._update_button_text()
    
    def get_item_count(self) -> int:
        """
        获取可选项总数
        
        Returns:
            int: 可选项总数
        """
        return len(self.all_items)
