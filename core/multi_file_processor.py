# asc_to_csv/core/multi_file_processor.py
"""
多文件处理器模块

负责处理多文件模式的ASC到CSV转换，包括多个ASC文件的排序、解析和拼接。

职责：
    - 多文件模式下的ASC文件排序
    - 循环处理多个ASC文件
    - 按分组拼接临时CSV
    - 清理临时资源
"""

import os
import gc
from typing import Optional, Callable, Dict, List, Any
from dataclasses import dataclass, field

from config import Config
from dbc_loader import DBCLoader
from asc_parser import ASCParser
from asc_file_merger import ASCFileMerger
from enhanced_data_processor import EnhancedDataProcessor
from enhanced_csv_writer import EnhancedCSVWriter
from csv_merger import CSVFileMerger
from multi_asc_converter import MultiASCConverter, MultiASCResult


class MultiFileProcessor:
    """
    多文件模式处理器

    处理多个ASC文件的完整转换流程，采用"分别转换+CSV拼接"的架构。

    Attributes:
        config: 配置对象
        dbc_loader: DBC文件加载器
    """

    def __init__(self, config: Config):
        """
        初始化多文件处理器

        Args:
            config: 配置对象
        """
        self.config = config
        self.dbc_loader: Optional[DBCLoader] = None

    def process(
        self,
        progress_callback: Optional[Callable[[float, int], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> MultiASCResult:
        """
        处理多文件转换

        Args:
            progress_callback: 进度回调函数
            log_callback: 日志回调函数

        Returns:
            MultiASCResult: 多文件转换结果
        """
        multi_converter = MultiASCConverter(self.config)
        return multi_converter.convert(progress_callback, log_callback)

    def _log(self, callback: Optional[Callable[[str], None]], message: str):
        """输出日志消息"""
        if callback:
            callback(message)
        else:
            print(message)

    def cleanup(self):
        """清理资源"""
        gc.collect()
