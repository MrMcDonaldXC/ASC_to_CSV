# asc_to_csv/core/conversion_coordinator.py
"""
转换协调器模块

负责转换流程的协调和调度，包括配置验证、流程编排和结果汇总。

职责：
    - 配置验证
    - 单文件/多文件流程调度
    - 结果汇总
    - 日志格式化
"""

import gc
import os
from typing import Optional, Callable, Dict, List, Any
from dataclasses import dataclass, field

from config import Config
from .single_file_processor import SingleFileProcessor
from .multi_file_processor import MultiFileProcessor


@dataclass
class ConversionResult:
    """
    转换结果数据类

    封装转换过程的完整结果信息。

    Attributes:
        success: 转换是否成功
        original_count: 原始数据点数
        sampled_count: 采样后时间点数
        signal_count: 实际信号数
        created_files: 成功创建的CSV文件路径列表
        skipped_files: 跳过的文件列表
        output_dir: 输出目录路径
        error_message: 错误信息
        group_statistics: 各分组的信号数量统计
        discovered_groups: 发现的所有分组名称
    """
    success: bool = False
    original_count: int = 0
    sampled_count: int = 0
    signal_count: int = 0
    created_files: List[str] = field(default_factory=list)
    skipped_files: List[str] = field(default_factory=list)
    output_dir: str = ""
    error_message: str = ""
    group_statistics: Dict[str, int] = field(default_factory=dict)
    discovered_groups: List[str] = field(default_factory=list)


class ConversionCoordinator:
    """
    转换协调器

    负责协调单文件和多文件模式的转换流程。

    Attributes:
        config: 配置对象
        single_processor: 单文件处理器
        multi_processor: 多文件处理器
    """

    def __init__(self, config: Config):
        """
        初始化转换协调器

        Args:
            config: 配置对象
        """
        self.config = config
        self.single_processor = SingleFileProcessor(config)
        self.multi_processor = MultiFileProcessor(config)

    def execute(
        self,
        progress_callback: Optional[Callable[[float, int], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None,
        overwrite: bool = False
    ) -> ConversionResult:
        """
        执行转换流程

        Args:
            progress_callback: 进度回调函数
            log_callback: 日志回调函数
            overwrite: 是否覆盖已存在的文件

        Returns:
            ConversionResult: 转换结果
        """
        result = ConversionResult()

        try:
            self._log(log_callback, "=" * 60)
            self._log(log_callback, "开始转换...")
            self._log(log_callback, f"采样间隔: {self.config.sample_interval}秒")
            self._log(log_callback, f"文件模式: {'多文件拼接' if self.config.multi_file_mode else '单文件'}")
            self._log(log_callback, "分组规则: BatP+数字 或 BatP+1-2个字母")
            self._log(log_callback, "")

            if not self.config.validate():
                result.error_message = "配置验证失败"
                return result

            self.config.create_output_dir()
            result.output_dir = self.config.output_dir

            if self.config.multi_file_mode:
                self._execute_multi_file(progress_callback, log_callback, result)
            else:
                self._execute_single_file(progress_callback, log_callback, overwrite, result)

        except Exception as e:
            result.error_message = f"{type(e).__name__}: {e}"
            self._log(log_callback, f"转换失败: {result.error_message}")

        finally:
            self._cleanup()

        return result

    def _execute_single_file(
        self,
        progress_callback: Optional[Callable[[float, int], None]],
        log_callback: Optional[Callable[[str], None]],
        overwrite: bool,
        result: ConversionResult
    ):
        """执行单文件转换"""
        success, process_result = self.single_processor.process(
            progress_callback=progress_callback,
            log_callback=log_callback,
            overwrite=overwrite
        )

        result.success = success
        result.created_files = process_result.get('created_files', [])
        result.skipped_files = process_result.get('skipped_files', [])
        result.original_count = process_result.get('original_count', 0)
        result.sampled_count = process_result.get('sampled_count', 0)
        result.signal_count = process_result.get('signal_count', 0)
        result.discovered_groups = process_result.get('discovered_groups', [])
        result.group_statistics = process_result.get('group_statistics', {})
        result.error_message = process_result.get('error_message', '')

        self._log(log_callback, "")
        self._log(log_callback, "=" * 60)
        self._log(log_callback, "转换完成！")
        self._log(log_callback, f"输出目录: {self.config.output_dir}")
        self._log(log_callback, f"发现分组: {len(result.discovered_groups)}个")

        for group_name in result.discovered_groups:
            count = result.group_statistics.get(group_name, 0)
            self._log(log_callback, f"  {group_name}: {count}个信号")

        self._log(log_callback, f"创建文件: {len(result.created_files)}个")
        if result.skipped_files:
            self._log(log_callback, f"跳过文件: {len(result.skipped_files)}个（已存在）")
        self._log(log_callback, "=" * 60)

    def _execute_multi_file(
        self,
        progress_callback: Optional[Callable[[float, int], None]],
        log_callback: Optional[Callable[[str], None]],
        result: ConversionResult
    ):
        """执行多文件转换"""
        self._log(log_callback, f"ASC文件数量: {len(self.config.asc_files)} 个文件")
        for f in self.config.asc_files:
            self._log(log_callback, f"  - {os.path.basename(f)}")
        self._log(log_callback, "")

        multi_result = self.multi_processor.process(
            progress_callback=progress_callback,
            log_callback=self._wrap_log_callback(log_callback)
        )

        result.success = multi_result.success
        result.created_files = multi_result.created_files
        result.discovered_groups = multi_result.discovered_groups
        result.group_statistics = multi_result.group_statistics
        result.error_message = multi_result.error_message
        result.output_dir = multi_result.output_dir

        self._log(log_callback, "")
        self._log(log_callback, "=" * 60)
        self._log(log_callback, "转换完成!")
        self._log(log_callback, f"输出目录: {result.output_dir}")
        self._log(log_callback, f"发现分组: {len(result.discovered_groups)}个")
        self._log(log_callback, f"总数据行: {multi_result.total_rows}行")
        self._log(log_callback, "=" * 60)

    def _log(self, callback: Optional[Callable[[str], None]], message: str):
        """输出日志消息"""
        if callback:
            callback(message)
        else:
            print(message)

    def _wrap_log_callback(self, log_callback: Optional[Callable[[str], None]]):
        """包装日志回调函数"""
        def wrapper(message: str):
            if log_callback:
                log_callback(message)
            else:
                print(message)
        return wrapper

    def _cleanup(self):
        """清理资源"""
        if self.single_processor:
            self.single_processor.cleanup()
        if self.multi_processor:
            self.multi_processor.cleanup()
        gc.collect()
