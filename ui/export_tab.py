# asc_to_csv/ui/export_tab.py
"""
数据导出标签页模块

提供CSV文件列选择、数据预览和导出功能。
"""

import os
import csv
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Optional, List, Tuple

from .base import BaseTab, LogMixin
from core.csv_loader import CSVDataLoader


class ExportTab(BaseTab, LogMixin):
    """
    数据导出标签页

    提供CSV文件的列选择、数据预览和导出功能。
    """

    def __init__(self, parent: tk.Widget, app_context: dict):
        """
        初始化导出标签页

        Args:
            parent: 父容器
            app_context: 应用上下文
        """
        self.data_loader = CSVDataLoader()
        self.current_file: Optional[str] = None
        self.selected_columns: List[str] = []
        self.all_columns: List[str] = []

        self.file_combo: Optional[ttk.Combobox] = None
        self.column_listbox: Optional[tk.Listbox] = None
        self.preview_btn: Optional[ttk.Button] = None
        self.export_btn: Optional[ttk.Button] = None
        self.filename_entry: Optional[ttk.Entry] = None
        self.path_entry: Optional[ttk.Entry] = None
        self.encoding_var: Optional[tk.StringVar] = None
        self.log_text: Optional[tk.Text] = None
        self.select_count_label: Optional[ttk.Label] = None

        super().__init__(parent, app_context)

    def _create_widgets(self):
        """创建界面组件"""
        control_frame = ttk.LabelFrame(self, text="文件与列选择", padding="10")
        control_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self._create_file_section(control_frame)
        self._create_column_section(control_frame)
        self._create_export_config_section(control_frame)
        self._create_action_section(control_frame)
        self._create_log_section(control_frame)

    def _create_file_section(self, parent: ttk.Frame):
        """创建文件选择区域"""
        file_frame = ttk.Frame(parent)
        file_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(file_frame, text="CSV文件:").pack(side=tk.LEFT)
        self.file_combo = ttk.Combobox(file_frame, width=50, state="readonly")
        self.file_combo.pack(side=tk.LEFT, padx=5)
        self.file_combo.bind("<<ComboboxSelected>>", self._on_file_selected)

        ttk.Button(file_frame, text="刷新", command=self._refresh_files).pack(side=tk.LEFT, padx=5)

    def _create_column_section(self, parent: ttk.Frame):
        """创建列选择区域"""
        column_frame = ttk.LabelFrame(parent, text="选择要导出的列", padding="5")
        column_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        list_frame = ttk.Frame(column_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.column_listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED,
                                         yscrollcommand=scrollbar.set, height=12)
        self.column_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.column_listbox.bind("<<ListboxSelect>>", self._on_column_selection_changed)
        scrollbar.config(command=self.column_listbox.yview)

        btn_frame = ttk.Frame(column_frame)
        btn_frame.pack(side=tk.LEFT, padx=5)

        ttk.Button(btn_frame, text="全选", command=self._select_all_columns,
                   width=10).pack(pady=2)
        ttk.Button(btn_frame, text="取消全选", command=self._deselect_all_columns,
                   width=10).pack(pady=2)

        self.select_count_label = ttk.Label(column_frame, text="已选择: 0 列",
                                            foreground="blue")
        self.select_count_label.pack(side=tk.BOTTOM, pady=5)

    def _create_export_config_section(self, parent: ttk.Frame):
        """创建导出配置区域"""
        config_frame = ttk.LabelFrame(parent, text="导出配置", padding="10")
        config_frame.pack(fill=tk.X, pady=5)

        ttk.Label(config_frame, text="文件名:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.filename_entry = ttk.Entry(config_frame, width=40)
        self.filename_entry.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=2)
        self.filename_entry.insert(0, "export_data.csv")

        ttk.Label(config_frame, text="保存路径:").grid(row=1, column=0, sticky=tk.W, pady=2)
        path_frame = ttk.Frame(config_frame)
        path_frame.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=2)
        self.path_entry = ttk.Entry(path_frame, width=35)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(path_frame, text="浏览...", command=self._browse_path,
                   width=8).pack(side=tk.LEFT, padx=(5, 0))

        ttk.Label(config_frame, text="编码:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.encoding_var = tk.StringVar(value="utf-8-sig")
        encoding_combo = ttk.Combobox(config_frame, textvariable=self.encoding_var,
                                       width=15, state="readonly")
        encoding_combo["values"] = ("utf-8-sig", "utf-8", "gbk", "gb2312")
        encoding_combo.grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)

        config_frame.columnconfigure(1, weight=1)

    def _create_action_section(self, parent: ttk.Frame):
        """创建操作按钮区域"""
        action_frame = ttk.Frame(parent)
        action_frame.pack(fill=tk.X, pady=10)

        self.preview_btn = ttk.Button(action_frame, text="预览数据",
                                       command=self._show_preview, width=12)
        self.preview_btn.pack(side=tk.LEFT, padx=5)

        self.export_btn = ttk.Button(action_frame, text="导出数据",
                                     command=self._start_export, width=12)
        self.export_btn.pack(side=tk.LEFT, padx=5)

    def _create_log_section(self, parent: ttk.Frame):
        """创建日志区域"""
        log_frame = ttk.LabelFrame(parent, text="操作日志", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.log_text = tk.Text(log_frame, height=6, state=tk.DISABLED, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _refresh_files(self):
        """刷新CSV文件列表"""
        output_dir = self.app_context.get('output_dir', '')
        if not output_dir or not os.path.exists(output_dir):
            self._log("请先在'数据转换'中选择输出目录")
            return

        csv_files = [f for f in os.listdir(output_dir) if f.endswith('.csv')]
        self.file_combo['values'] = csv_files

        if csv_files:
            self.file_combo.set(csv_files[0])
            self._on_file_selected(None)
        else:
            self.column_listbox.delete(0, tk.END)
            self.all_columns = []
            self.selected_columns = []
            self._update_select_count()

    def _on_file_selected(self, event):
        """文件选择事件处理"""
        file_name = self.file_combo.get()
        if not file_name:
            return

        output_dir = self.app_context.get('output_dir', '')
        if not output_dir:
            return

        file_path = os.path.join(output_dir, file_name)
        self._load_csv_and_update_columns(file_path)

    def _load_csv_and_update_columns(self, file_path: str):
        """加载CSV文件并更新列列表"""
        self._log(f"正在加载: {os.path.basename(file_path)}")

        if self.data_loader.load(file_path):
            self.current_file = file_path
            self.all_columns = self.data_loader.columns
            self.selected_columns = []

            self.column_listbox.delete(0, tk.END)
            for col in self.all_columns:
                self.column_listbox.insert(tk.END, col)

            base_name = os.path.splitext(os.path.basename(file_path))[0]
            self.filename_entry.delete(0, tk.END)
            self.filename_entry.insert(0, f"{base_name}_export.csv")

            self._log(f"已加载 {len(self.all_columns)} 列数据")
            self._update_select_count()
        else:
            self._log("加载失败")

    def _on_column_selection_changed(self, event):
        """列选择变化事件处理"""
        selection = self.column_listbox.curselection()
        self.selected_columns = [self.all_columns[i] for i in selection]
        self._update_select_count()

    def _update_select_count(self):
        """更新已选择列数显示"""
        count = len(self.selected_columns)
        self.select_count_label.config(text=f"已选择: {count} 列")

    def _select_all_columns(self):
        """全选所有列"""
        self.column_listbox.select_set(0, tk.END)
        self.selected_columns = self.all_columns[:]
        self._update_select_count()

    def _deselect_all_columns(self):
        """取消全选"""
        self.column_listbox.select_clear(0, tk.END)
        self.selected_columns = []
        self._update_select_count()

    def _browse_path(self):
        """浏览保存路径"""
        initial_dir = self.path_entry.get() or self.app_context.get('output_dir', '')
        dirname = filedialog.askdirectory(title="选择保存路径", initialdir=initial_dir)
        if dirname:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, dirname)

    def _show_preview(self):
        """显示数据预览窗口"""
        if not self.selected_columns:
            messagebox.showwarning("提示", "请先选择要导出的列")
            return

        if not self.current_file:
            messagebox.showwarning("提示", "请先选择CSV文件")
            return

        preview_window = tk.Toplevel(self)
        preview_window.title("数据预览")
        preview_window.geometry("800x400")

        main_frame = ttk.Frame(preview_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        info_label = ttk.Label(main_frame,
                               text=f"预览 (前10行，已选择 {len(self.selected_columns)} 列)")
        info_label.pack(pady=5)

        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        scroll_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        scroll_x = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

        tree = ttk.Treeview(tree_frame, yscrollcommand=scroll_y.set,
                           xscrollcommand=scroll_x.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.config(command=tree.yview)
        scroll_x.config(command=tree.xview)

        tree["columns"] = self.selected_columns
        tree["show"] = "headings"

        for col in self.selected_columns:
            tree.heading(col, text=col)
            tree.column(col, width=120, anchor=tk.W)

        preview_count = min(10, self.data_loader.row_count)
        for row_idx in range(preview_count):
            row_data = []
            for col in self.selected_columns:
                value = self.data_loader.data[col][row_idx]
                row_data.append(str(value) if value is not None else "")
            tree.insert("", tk.END, values=row_data)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="关闭", command=preview_window.destroy).pack()

    def _validate_export_inputs(self) -> bool:
        """验证导出输入"""
        if not self.selected_columns:
            messagebox.showerror("错误", "请选择要导出的列")
            return False

        if not self.current_file:
            messagebox.showerror("错误", "请选择CSV文件")
            return False

        filename = self.filename_entry.get().strip()
        if not filename:
            messagebox.showerror("错误", "请输入导出文件名")
            return False

        if not filename.endswith('.csv'):
            filename += '.csv'
            self.filename_entry.delete(0, tk.END)
            self.filename_entry.insert(0, filename)

        save_path = self.path_entry.get().strip()
        if not save_path:
            save_path = self.app_context.get('output_dir', '')
            if not save_path:
                messagebox.showerror("错误", "请选择保存路径")
                return False
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, save_path)

        if not os.path.exists(save_path):
            try:
                os.makedirs(save_path)
            except Exception as e:
                messagebox.showerror("错误", f"无法创建目录: {e}")
                return False

        return True

    def _start_export(self):
        """开始导出数据"""
        if not self._validate_export_inputs():
            return

        self._log("开始导出数据...")
        self.export_btn.configure(state=tk.DISABLED)

        try:
            filename = self.filename_entry.get().strip()
            if not filename.endswith('.csv'):
                filename += '.csv'

            save_path = self.path_entry.get().strip()
            output_file = os.path.join(save_path, filename)
            encoding = self.encoding_var.get()

            self._export_columns_to_csv(output_file, encoding)

            self._log(f"导出成功: {output_file}")
            messagebox.showinfo("成功", f"数据已导出到:\n{output_file}")

        except Exception as e:
            self._log(f"导出失败: {str(e)}")
            messagebox.showerror("错误", f"导出失败:\n{str(e)}")

        finally:
            self.export_btn.configure(state=tk.NORMAL)

    def _export_columns_to_csv(self, output_file: str, encoding: str):
        """
        将选定的列导出到CSV文件

        Args:
            output_file: 输出文件路径
            encoding: 文件编码
        """
        with open(output_file, 'w', newline='', encoding=encoding) as f:
            writer = csv.writer(f)

            writer.writerow(self.selected_columns)

            for row_idx in range(self.data_loader.row_count):
                row_data = []
                for col in self.selected_columns:
                    value = self.data_loader.data[col][row_idx]
                    row_data.append(value if value is not None else "")
                writer.writerow(row_data)

    def refresh_files(self):
        """刷新文件列表（供外部调用）"""
        self._refresh_files()

    def _log(self, message: str):
        """输出日志"""
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

    @property
    def root(self):
        """获取根窗口"""
        return self.app_context.get('root')
