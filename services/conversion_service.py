# asc_to_csv/services/conversion_service.py
"""
转换服务模块

本模块是ASC到CSV转换流程的核心协调层，负责组织和协调各个处理模块，
完成从ASC文件解析到CSV文件生成的完整转换流程。

主要功能：
    - 协调DBC加载、ASC解析、数据处理、CSV写入各模块
    - 提供转换进度和日志回调接口
    - 返回结构化的转换结果

转换流程：
    1. 配置验证：检查输入文件和输出目录
    2. DBC加载：加载DBC文件，建立消息和信号映射
    3. ASC解析：解析ASC文件，提取CAN帧数据
    4. 数据处理：聚合采样数据，对信号进行分组
    5. CSV写入：为每个分组创建独立的CSV文件
    6. 资源清理：释放内存，确保资源正确释放

使用示例：
    >>> from config import Config
    >>> from services.conversion_service import ConversionService
    >>>
    >>> config = Config(
    ...     asc_file='input.asc',
    ...     dbc_files=['data.dbc'],
    ...     output_dir='output'
    ... )
    >>>
    >>> service = ConversionService(config)
    >>> result = service.convert()
    >>>
    >>> if result.success:
    ...     print(f"转换成功，创建了 {len(result.created_files)} 个文件")
    ... else:
    ...     print(f"转换失败: {result.error_message}")
"""

import gc
import os
from typing import Optional, Callable, Dict, List, Any
from dataclasses import dataclass, field

from config import Config
from core.dbc_loader import DBCLoader
from core.asc_parser import ASCParser
from services.asc_merger import ASCFileMerger
from core.data_processor import DataProcessor
from core.csv_writer import CSVWriter
from services.multi_converter import MultiASCConverter


@dataclass
class ConversionResult:
    """
    转换结果数据类

    封装转换过程的完整结果信息，包括成功状态、统计数据、文件列表和错误信息。

    Attributes:
        success (bool): 转换是否成功
        original_count (int): 原始数据点数（解析前的数据点总数）
        sampled_count (int): 采样后时间点数（按采样间隔聚合后的时间点数）
        signal_count (int): 实际信号数（成功解析的信号数量）
        created_files (List[str]): 成功创建的CSV文件路径列表
        skipped_files (List[str]): 跳过的文件列表（已存在且未覆盖）
        output_dir (str): 输出目录路径
        error_message (str): 错误信息（仅在失败时有值）
        group_statistics (Dict[str, int]): 各分组的信号数量统计
        discovered_groups (List[str]): 发现的所有分组名称（排序后）

    Examples:
        >>> result = ConversionResult()
        >>> result.success = True
        >>> result.created_files = ['output/BATP1.csv', 'output/Others.csv']
        >>> print(f"创建了 {len(result.created_files)} 个文件")
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


class ConversionService:
    """
    转换服务类

    作为ASC到CSV转换流程的核心协调器，负责组织和管理各个处理模块的执行顺序，
    处理错误情况，并提供进度和日志回调接口。

    Attributes:
        config (Config): 配置对象
        dbc_loader (Optional[DBCLoader]): DBC文件加载器
        asc_parser (Optional[ASCParser]): ASC文件解析器
        data_processor (Optional[DataProcessor]): 数据处理器
        csv_writer (Optional[CSVWriter]): CSV写入器

    分组规则：
        - BatP + 数字：BATP1, BATP10, BATP28 等
        - BatP + 1-2个字母：BATPS, BATPQ, BATPL, BATPR 等
        - 不符合规则的归入 Others

    转换流程：
        1. 配置验证 → 确保输入文件存在、输出目录有效
        2. DBC加载 → 加载DBC文件，建立消息ID到消息对象的映射
        3. ASC解析 → 解析ASC文件，提取CAN帧并解码信号
        4. 数据处理 → 聚合采样数据，对信号进行分组分类
        5. CSV写入 → 为每个分组创建独立的CSV文件
        6. 资源清理 → 释放内存，确保无内存泄漏

    Examples:
        >>> from config import Config
        >>> config = Config(
        ...     asc_file='test.asc',
        ...     dbc_files=['test.dbc'],
        ...     output_dir='output',
        ...     sample_interval=0.1
        ... )
        >>>
        >>> service = ConversionService(config)
        >>>
        >>> # 使用回调函数
        >>> def log_handler(message):
        ...     print(message)
        >>>
        >>> def progress_handler(progress, line_count):
        ...     print(f"进度: {progress:.1f}%")
        >>>
        >>> result = service.convert(
        ...     progress_callback=progress_handler,
        ...     log_callback=log_handler
        ... )
    """

    def __init__(self, config: Config):
        """
        初始化转换服务

        Args:
            config: 配置对象，包含ASC文件路径、DBC文件列表、输出目录等配置
        """
        self.config = config
        self.dbc_loader: Optional[DBCLoader] = None
        self.asc_parser: Optional[ASCParser] = None
        self.data_processor: Optional[DataProcessor] = None
        self.csv_writer: Optional[CSVWriter] = None

    def convert(
        self,
        progress_callback: Optional[Callable[[float, int], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None,
        overwrite: bool = False
    ) -> ConversionResult:
        """
        执行完整的转换流程

        按照预定义的流程执行转换，包括配置验证、DBC加载、ASC解析、
        数据处理和CSV写入。每个阶段都有详细的日志输出。

        Args:
            progress_callback: 进度回调函数
                - 参数1 (float): 进度百分比 (0.0 - 100.0)
                - 参数2 (int): 已处理的行数
                - 示例: def progress(progress, lines): print(f"{progress}%")
            log_callback: 日志回调函数
                - 参数 (str): 日志消息
                - 示例: def log(msg): print(msg)
            overwrite: 是否覆盖已存在的文件
                - False (默认): 跳过已存在的文件
                - True: 覆盖已存在的文件

        Returns:
            ConversionResult: 转换结果对象
                - success: 转换是否成功
                - created_files: 创建的文件列表
                - discovered_groups: 发现的分组列表
                - group_statistics: 分组统计信息
                - error_message: 错误信息（仅在失败时）

        Raises:
            不直接抛出异常，所有异常都会被捕获并记录到 error_message

        Examples:
            >>> service = ConversionService(config)
            >>> result = service.convert()
            >>> if result.success:
            ...     print(f"成功创建 {len(result.created_files)} 个文件")
            ...     for group in result.discovered_groups:
            ...         print(f"  {group}: {result.group_statistics[group]} 个信号")
        """
        result = ConversionResult()

        try:
            self._log(log_callback, "=" * 60)
            self._log(log_callback, "开始转换...")
            self._log(log_callback, f"采样间隔: {self.config.sample_interval}秒")
            self._log(log_callback, f"文件模式: {'多文件拼接' if self.config.multi_file_mode else '单文件'}")
            self._log(log_callback, "分组规则: BatP+数字 或 BatP+1-2个字母")
            self._log(log_callback, "")

            if self.config.multi_file_mode:
                self._log(log_callback, f"ASC文件数量: {len(self.config.asc_files)} 个文件")
                for f in self.config.asc_files:
                    self._log(log_callback, f"  - {os.path.basename(f)}")
                self._log(log_callback, "")

                if not self.config.validate():
                    result.error_message = "配置验证失败"
                    return result

                self.config.create_output_dir()
                result.output_dir = self.config.output_dir

                multi_converter = MultiASCConverter(self.config)
                multi_result = multi_converter.convert(
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

                return result

            if not self.config.validate():
                result.error_message = "配置验证失败"
                return result

            self.config.create_output_dir()
            result.output_dir = self.config.output_dir

            if not self._load_dbc(log_callback):
                result.error_message = "DBC文件加载失败"
                return result

            if not self._parse_asc(progress_callback, log_callback):
                result.error_message = "ASC文件解析失败"
                return result

            self._process_data(log_callback)

            statistics = self._get_statistics()
            result.original_count = statistics['original_count']
            result.sampled_count = statistics['sampled_count']
            result.signal_count = statistics['signal_count']

            write_result = self._write_csv(log_callback, overwrite)
            result.created_files = write_result.get('created_files', [])
            result.skipped_files = write_result.get('skipped_files', [])
            result.success = True

            result.discovered_groups = self.data_processor.sorted_groups
            result.group_statistics = self.data_processor.get_group_statistics()

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

        except Exception as e:
            result.error_message = f"{type(e).__name__}: {e}"
            self._log(log_callback, f"转换失败: {result.error_message}")

        finally:
            self._cleanup()

        return result

    def _log(self, callback: Optional[Callable[[str], None]], message: str):
        """
        输出日志消息

        Args:
            callback: 日志回调函数，如果为None则输出到控制台
            message: 日志消息
        """
        if callback:
            callback(message)
        else:
            print(message)

    def _wrap_log_callback(self, log_callback: Optional[Callable[[str], None]]):
        """
        包装日志回调函数

        用于将字符串类型的日志消息传递给回调函数。

        Args:
            log_callback: 日志回调函数

        Returns:
            包装后的回调函数
        """
        def wrapper(message: str):
            if log_callback:
                log_callback(message)
            else:
                print(message)
        return wrapper

    def _validate_config(self, log_callback: Optional[Callable[[str], None]]) -> bool:
        """
        验证配置

        检查配置的有效性，包括：
        - ASC文件是否存在
        - DBC文件是否存在
        - 输出目录是否有效

        Args:
            log_callback: 日志回调函数

        Returns:
            bool: 配置是否有效
        """
        if not self.config.validate():
            self._log(log_callback, "配置验证失败")
            return False
        return True

    def _load_dbc(self, log_callback: Optional[Callable[[str], None]]) -> bool:
        """
        加载DBC文件

        加载所有配置的DBC文件，建立消息和信号的映射关系。

        Args:
            log_callback: 日志回调函数

        Returns:
            bool: 加载是否成功

        Side Effects:
            创建 self.dbc_loader 实例
        """
        self._log(log_callback, "正在加载DBC文件...")

        self.dbc_loader = DBCLoader()
        if not self.dbc_loader.load(self.config.dbc_files):
            return False

        self._log(log_callback, f"总消息定义数: {self.dbc_loader.get_message_count()}")
        self._log(log_callback, f"总信号定义数: {self.dbc_loader.get_signal_count()}")
        self._log(log_callback, "")

        return True

    def _parse_asc(
        self,
        progress_callback: Optional[Callable[[float, int], None]],
        log_callback: Optional[Callable[[str], None]]
    ) -> bool:
        """
        解析ASC文件

        支持单文件和多文件两种模式：
        - 单文件模式：直接解析单个ASC文件
        - 多文件模式：先排序再依次解析多个ASC文件

        Args:
            progress_callback: 进度回调函数
            log_callback: 日志回调函数

        Returns:
            bool: 解析是否成功

        Side Effects:
            创建 self.asc_parser 实例
        """
        self.asc_parser = ASCParser(
            sample_interval=self.config.sample_interval,
            debug=self.config.debug
        )

        if self.config.multi_file_mode:
            return self._parse_multiple_asc(progress_callback, log_callback)
        else:
            return self._parse_single_asc(progress_callback, log_callback)

    def _parse_single_asc(
        self,
        progress_callback: Optional[Callable[[float, int], None]],
        log_callback: Optional[Callable[[str], None]]
    ) -> bool:
        """
        解析单个ASC文件（单文件模式）

        Args:
            progress_callback: 进度回调函数
            log_callback: 日志回调函数

        Returns:
            bool: 解析是否成功
        """
        self._log(log_callback, "正在解析ASC文件...")
        self._log(log_callback, "进度: 0%")

        def internal_progress_callback(progress: float, line_count: int):
            if progress_callback:
                progress_callback(progress, line_count)
            if log_callback and progress % 10 < 1:
                self._log(log_callback, f"进度: {progress:.1f}% (已处理 {line_count:,} 行)")

        if not self.asc_parser.parse(
            self.config.single_asc_file,
            self.dbc_loader.message_map,
            internal_progress_callback
        ):
            return False

        original_count, sampled_count, signal_count = self.asc_parser.get_statistics()
        self._log(log_callback, f"解析完成：原始数据点数: {original_count}, 采样后时间点数: {sampled_count}, 实际信号数: {signal_count}")
        self._log(log_callback, "")

        return True

    def _parse_multiple_asc(
        self,
        progress_callback: Optional[Callable[[float, int], None]],
        log_callback: Optional[Callable[[str], None]]
    ) -> bool:
        """
        解析多个ASC文件（多文件拼接模式）

        Args:
            progress_callback: 进度回调函数
            log_callback: 日志回调函数

        Returns:
            bool: 解析是否成功
        """
        self._log(log_callback, "正在处理多ASC文件...")

        merger = ASCFileMerger()

        def sort_progress_callback(message: str):
            self._log(log_callback, message)

        sorted_files = merger.sort_files_by_time(self.config.asc_files, sort_progress_callback)

        self._log(log_callback, f"文件排序完成，共 {len(sorted_files)} 个文件")
        self._log(log_callback, "")

        self._log(log_callback, "正在解析ASC文件...")
        self._log(log_callback, "进度: 0%")

        def internal_progress_callback(progress: float, line_count: int, current_file: str = ""):
            if progress_callback:
                progress_callback(progress, line_count)
            if log_callback:
                msg = f"进度: {progress:.1f}% (已处理 {line_count:,} 行)"
                if current_file:
                    msg += f" - {current_file}"
                self._log(log_callback, msg)

        if not self.asc_parser.parse_multiple(
            sorted_files,
            self.dbc_loader.message_map,
            internal_progress_callback
        ):
            return False

        original_count, sampled_count, signal_count = self.asc_parser.get_statistics()
        self._log(log_callback, f"解析完成：原始数据点数: {original_count}, 采样后时间点数: {sampled_count}, 实际信号数: {signal_count}")
        self._log(log_callback, "")

        return True

    def _process_data(self, log_callback: Optional[Callable[[str], None]]):
        """
        处理数据

        聚合采样数据并对信号进行分组分类。

        Args:
            log_callback: 日志回调函数

        Side Effects:
            创建 self.data_processor 实例
        """
        self._log(log_callback, "正在处理数据...")

        self.data_processor = DataProcessor()
        self.data_processor.aggregate(self.asc_parser.sampled_data)
        self.data_processor.classify_signals(self.asc_parser.found_signals)

        self._log(log_callback, "分组结果：")
        for group_name, count in self.data_processor.get_group_statistics().items():
            self._log(log_callback, f"  {group_name}: {count}个信号")
        self._log(log_callback, "")

    def _get_statistics(self) -> Dict[str, int]:
        """
        获取统计信息

        Returns:
            Dict[str, int]: 统计信息字典
                - original_count: 原始数据点数
                - sampled_count: 采样后时间点数
                - signal_count: 实际信号数
        """
        original_count, sampled_count, signal_count = self.asc_parser.get_statistics()
        return {
            'original_count': original_count,
            'sampled_count': sampled_count,
            'signal_count': signal_count
        }

    def _write_csv(self, log_callback: Optional[Callable[[str], None]],
                   overwrite: bool) -> Dict[str, Any]:
        """
        写入CSV文件

        为每个分组创建独立的CSV文件，并生成汇总文件。

        Args:
            log_callback: 日志回调函数
            overwrite: 是否覆盖已存在的文件

        Returns:
            Dict[str, Any]: 写入结果
                - created_files: 创建的文件列表
                - skipped_files: 跳过的文件列表
                - total_groups: 总分组数
                - created_count: 创建文件数
                - skipped_count: 跳过文件数

        Side Effects:
            创建 self.csv_writer 实例
        """
        self._log(log_callback, "正在创建CSV文件...")

        self.csv_writer = CSVWriter(
            output_dir=self.config.output_dir,
            encoding=self.config.csv_encoding,
            overwrite=overwrite
        )

        write_result = self.csv_writer.write_all_groups(
            classified_signals=self.data_processor.classified_signals,
            sorted_timestamps=self.data_processor.get_sorted_timestamps(),
            aggregated_data=self.data_processor.aggregated_data,
            signal_info=self.dbc_loader.signal_info
        )

        self.csv_writer.write_summary_file(
            classified_signals=self.data_processor.classified_signals,
            sorted_timestamps=self.data_processor.get_sorted_timestamps(),
            result_stats=write_result
        )

        return write_result

    def _cleanup(self):
        """
        清理资源

        释放所有模块占用的内存，确保无内存泄漏。
        通常在转换完成后调用。
        """
        if self.asc_parser:
            self.asc_parser.clear()
        if self.data_processor:
            self.data_processor.clear()
        gc.collect()

    def get_group_statistics(self) -> Dict[str, int]:
        """
        获取分组统计信息

        Returns:
            Dict[str, int]: 分组名称到信号数量的映射
        """
        if self.data_processor:
            return self.data_processor.get_group_statistics()
        return {}

    def get_sorted_groups(self) -> List[str]:
        """
        获取排序后的分组列表

        Returns:
            List[str]: 排序后的组名称列表
        """
        if self.data_processor:
            return self.data_processor.sorted_groups
        return []


EnhancedConversionService = ConversionService
EnhancedConversionResult = ConversionResult