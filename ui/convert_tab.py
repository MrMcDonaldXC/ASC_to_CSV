# asc_to_csv/ui/convert_tab.py
"""
数据转换标签页模块
提供ASC到CSV的转换功能界面
"""

import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Optional
import json
import traceback

from .base import BaseTab, LogMixin
from config import Config
from conversion_service import ConversionService


class ConvertTab(BaseTab, LogMixin):
    """
    数据转换标签页
    
    提供ASC文件到CSV文件的转换功能
    
    Attributes:
        asc_entry: ASC文件路径输入框
        dbc_listbox: DBC文件列表框
        output_entry: 输出目录输入框
        log_text: 日志文本框
    """
    
    def __init__(self, parent: tk.Widget, app_context: dict):
        """
        初始化转换标签页
        
        Args:
            parent: 父容器
            app_context: 应用上下文
        """
        self.convert_btn: Optional[ttk.Button] = None
        self.log_text: Optional[tk.Text] = None
        self.asc_entry: Optional[ttk.Entry] = None
        self.dbc_listbox: Optional[tk.Listbox] = None
        self.output_entry: Optional[ttk.Entry] = None
        self.sample_interval_var: Optional[tk.StringVar] = None
        self.encoding_var: Optional[tk.StringVar] = None
        self.debug_var: Optional[tk.BooleanVar] = None
        
        super().__init__(parent, app_context)
    
    def _create_widgets(self):
        """创建界面组件"""
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        self._create_file_section(main_frame)
        self._create_param_section(main_frame)
        self._create_action_section(main_frame)
        self._create_log_section(main_frame)
    
    def _create_file_section(self, parent: ttk.Frame):
        """创建文件选择区域"""
        file_frame = ttk.LabelFrame(parent, text="文件设置", padding="10")
        file_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(file_frame, text="ASC文件:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.asc_entry = ttk.Entry(file_frame, width=60)
        self.asc_entry.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=2)
        ttk.Button(file_frame, text="浏览...", command=self._browse_asc).grid(row=0, column=2, pady=2)
        
        ttk.Label(file_frame, text="DBC文件:").grid(row=1, column=0, sticky=tk.W, pady=2)
        dbc_frame = ttk.Frame(file_frame)
        dbc_frame.grid(row=1, column=1, columnspan=2, sticky=tk.EW, pady=2)
        
        self.dbc_listbox = tk.Listbox(dbc_frame, height=3, selectmode=tk.EXTENDED)
        self.dbc_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        dbc_btn_frame = ttk.Frame(dbc_frame)
        dbc_btn_frame.pack(side=tk.RIGHT, padx=5)
        ttk.Button(dbc_btn_frame, text="添加", command=self._add_dbc, width=6).pack(pady=1)
        ttk.Button(dbc_btn_frame, text="删除", command=self._remove_dbc, width=6).pack(pady=1)
        
        ttk.Label(file_frame, text="输出目录:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.output_entry = ttk.Entry(file_frame, width=60)
        self.output_entry.grid(row=2, column=1, sticky=tk.EW, padx=5, pady=2)
        ttk.Button(file_frame, text="浏览...", command=self._browse_output).grid(row=2, column=2, pady=2)
        
        file_frame.columnconfigure(1, weight=1)
    
    def _create_param_section(self, parent: ttk.Frame):
        """创建参数配置区域"""
        param_frame = ttk.LabelFrame(parent, text="转换参数", padding="10")
        param_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(param_frame, text="采样间隔(秒):").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.sample_interval_var = tk.StringVar(value="0.1")
        ttk.Entry(param_frame, textvariable=self.sample_interval_var, width=15).grid(
            row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(param_frame, text="CSV编码:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.encoding_var = tk.StringVar(value="utf-8-sig")
        encoding_combo = ttk.Combobox(param_frame, textvariable=self.encoding_var, 
                                       width=12, state="readonly")
        encoding_combo["values"] = ("utf-8-sig", "utf-8", "gbk", "gb2312")
        encoding_combo.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        self.debug_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(param_frame, text="调试模式", 
                        variable=self.debug_var).grid(row=1, column=2, sticky=tk.W, padx=(20, 0), pady=2)
    
    def _create_action_section(self, parent: ttk.Frame):
        """创建操作按钮区域"""
        action_frame = ttk.Frame(parent)
        action_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(action_frame, text="保存配置", 
                   command=self._save_config, width=12).pack(side=tk.LEFT, padx=5)
        
        self.convert_btn = ttk.Button(action_frame, text="开始转换", 
                                       command=self._start_convert, width=15)
        self.convert_btn.pack(side=tk.LEFT, padx=5)
    
    def _create_log_section(self, parent: ttk.Frame):
        """创建日志输出区域"""
        log_frame = ttk.LabelFrame(parent, text="运行日志", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.log_text = tk.Text(log_frame, height=10, state=tk.DISABLED, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def _browse_asc(self):
        """浏览ASC文件"""
        filename = filedialog.askopenfilename(
            title="选择ASC文件",
            filetypes=[("ASC文件", "*.asc"), ("所有文件", "*.*")]
        )
        if filename:
            self.asc_entry.delete(0, tk.END)
            self.asc_entry.insert(0, filename)
    
    def _add_dbc(self):
        """添加DBC文件"""
        filenames = filedialog.askopenfilenames(
            title="选择DBC文件",
            filetypes=[("DBC文件", "*.dbc"), ("所有文件", "*.*")]
        )
        for filename in filenames:
            if filename not in self.dbc_listbox.get(0, tk.END):
                self.dbc_listbox.insert(tk.END, filename)
    
    def _remove_dbc(self):
        """删除选中的DBC文件"""
        selection = self.dbc_listbox.curselection()
        for index in reversed(selection):
            self.dbc_listbox.delete(index)
    
    def _browse_output(self):
        """浏览输出目录"""
        dirname = filedialog.askdirectory(title="选择输出目录")
        if dirname:
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, dirname)
    
    def _save_config(self):
        """保存配置"""
        config_data = {
            "asc_file": self.asc_entry.get(),
            "dbc_files": list(self.dbc_listbox.get(0, tk.END)),
            "output_dir": self.output_entry.get(),
            "sample_interval": float(self.sample_interval_var.get()),
            "csv_encoding": self.encoding_var.get(),
            "debug": self.debug_var.get()
        }
        
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                   "config.json")
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4, ensure_ascii=False)
            self._log(f"配置已保存到: {config_path}")
            messagebox.showinfo("成功", "配置保存成功！")
        except Exception as e:
            self._log(f"保存配置失败: {e}")
            messagebox.showerror("错误", f"保存配置失败: {e}")
    
    def _validate_inputs(self) -> bool:
        """验证输入参数"""
        asc_file = self.asc_entry.get().strip()
        if not asc_file:
            messagebox.showerror("错误", "请选择ASC文件")
            return False
        
        if not os.path.exists(asc_file):
            messagebox.showerror("错误", f"ASC文件不存在: {asc_file}")
            return False
        
        if self.dbc_listbox.size() == 0:
            messagebox.showerror("错误", "请至少添加一个DBC文件")
            return False
        
        for dbc in self.dbc_listbox.get(0, tk.END):
            if not os.path.exists(dbc):
                messagebox.showerror("错误", f"DBC文件不存在: {dbc}")
                return False
        
        output_dir = self.output_entry.get().strip()
        if not output_dir:
            messagebox.showerror("错误", "请选择输出目录")
            return False
        
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
        """开始转换"""
        if not self._validate_inputs():
            return
        
        if self.app_context.get('is_converting', False):
            messagebox.showwarning("提示", "转换正在进行中，请稍候...")
            return
        
        self.app_context['is_converting'] = True
        self.convert_btn.configure(state=tk.DISABLED)
        self._clear_log()
        
        thread = threading.Thread(target=self._do_convert, daemon=True)
        thread.start()
    
    def _do_convert(self):
        """执行转换（后台线程）"""
        try:
            config = Config(
                asc_file=self.asc_entry.get(),
                dbc_files=list(self.dbc_listbox.get(0, tk.END)),
                output_dir=self.output_entry.get(),
                sample_interval=float(self.sample_interval_var.get()),
                csv_encoding=self.encoding_var.get(),
                debug=self.debug_var.get()
            )
            
            service = ConversionService(config)
            
            def progress_callback(progress: float, line_count: int):
                self.app_context['root'].after(0, 
                    lambda: self._update_progress_display(progress, line_count))
            
            result = service.convert(
                progress_callback=progress_callback,
                log_callback=self._log
            )
            
            if result.success:
                self.app_context['output_dir'] = result.output_dir
                self.app_context['root'].after(0, 
                    lambda: self.app_context.get('refresh_callback', lambda: None)())
                self.app_context['root'].after(0, 
                    lambda: messagebox.showinfo("成功", f"转换完成！\n输出目录: {result.output_dir}"))
            else:
                self.app_context['root'].after(0, 
                    lambda: messagebox.showerror("错误", f"转换失败: {result.error_message}"))
            
        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            self._log(f"转换失败: {error_msg}")
            if self.debug_var.get():
                self._log(traceback.format_exc())
            self.app_context['root'].after(0, 
                lambda: messagebox.showerror("错误", f"转换失败: {error_msg}"))
        
        finally:
            self.app_context['is_converting'] = False
            self.app_context['root'].after(0, 
                lambda: self.convert_btn.configure(state=tk.NORMAL))
    
    def _update_progress_display(self, progress: float, line_count: int):
        """更新进度显示"""
        try:
            content = self.log_text.get("1.0", tk.END)
            lines = content.strip().split('\n')
            for i in range(len(lines) - 1, -1, -1):
                if lines[i].startswith("进度:"):
                    lines[i] = f"进度: {progress:.1f}% (已处理 {line_count:,} 行)"
                    break
            
            self.log_text.configure(state=tk.NORMAL)
            self.log_text.delete("1.0", tk.END)
            self.log_text.insert(tk.END, '\n'.join(lines) + '\n')
            self.log_text.see(tk.END)
            self.log_text.configure(state=tk.DISABLED)
            self.app_context['root'].update_idletasks()
        except tk.TclError:
            pass
    
    def load_config(self, config: Config):
        """加载配置"""
        if config:
            if config.asc_file:
                self.asc_entry.insert(0, config.asc_file)
            for dbc in config.dbc_files:
                self.dbc_listbox.insert(tk.END, dbc)
            if config.output_dir:
                self.output_entry.insert(0, config.output_dir)
            self.sample_interval_var.set(str(config.sample_interval))
            self.encoding_var.set(config.csv_encoding)
            self.debug_var.set(config.debug)
            self._log("已加载配置文件")
