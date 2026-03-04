# asc_to_csv/ui/base.py
"""
基础UI组件模块
提供所有标签页的基类和公共组件
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable


class BaseTab(ttk.Frame):
    """
    标签页基类
    
    所有功能标签页的父类，提供公共方法和接口
    """
    
    def __init__(self, parent: tk.Widget, app_context: dict):
        """
        初始化标签页
        
        Args:
            parent: 父容器
            app_context: 应用上下文（包含共享资源）
        """
        super().__init__(parent)
        self.app_context = app_context
        self._create_widgets()
    
    def _create_widgets(self):
        """创建界面组件（子类实现）"""
        pass
    
    def on_activate(self):
        """标签页激活时调用（子类实现）"""
        pass
    
    def on_deactivate(self):
        """标签页停用时调用（子类实现）"""
        pass


class LogMixin:
    """
    日志功能混入类
    
    提供日志输出功能
    """
    
    log_text: Optional[tk.Text] = None
    root: Optional[tk.Tk] = None
    
    def _log(self, message: str):
        """
        输出日志信息
        
        Args:
            message: 日志消息
        """
        if not self.log_text:
            return
        try:
            self.log_text.configure(state=tk.NORMAL)
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
            self.log_text.configure(state=tk.DISABLED)
            if self.root:
                self.root.update_idletasks()
        except tk.TclError:
            pass
    
    def _clear_log(self):
        """清空日志"""
        if not self.log_text:
            return
        try:
            self.log_text.configure(state=tk.NORMAL)
            self.log_text.delete(1.0, tk.END)
            self.log_text.configure(state=tk.DISABLED)
        except tk.TclError:
            pass


class ProgressMixin:
    """
    进度显示功能混入类
    """
    
    def _update_progress(self, progress: float, message: str = ""):
        """
        更新进度显示
        
        Args:
            progress: 进度值（0-100）
            message: 进度消息
        """
        pass
