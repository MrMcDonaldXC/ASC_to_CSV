# asc_to_csv/enhanced_conversion_service.py
"""
转换服务模块

本模块是ASC到CSV转换流程的核心协调层，负责组织和协调各个处理模块，
完成从ASC文件解析到CSV文件生成的完整转换流程。

.. deprecated::
    此类已重构为Facade模式，具体实现已移至 core/ 包：
    - core.conversion_coordinator.ConversionCoordinator: 转换协调器
    - core.single_file_processor.SingleFileProcessor: 单文件处理器
    - core.multi_file_processor.MultiFileProcessor: 多文件处理器

    请使用新的模块以获得更好的代码组织和维护性。
    此类保留用于向后兼容。

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
    >>> from enhanced_conversion_service import EnhancedConversionService
    >>>
    >>> config = Config(
    ...     asc_file='input.asc',
    ...     dbc_files=['data.dbc'],
    ...     output_dir='output'
    ... )
    >>>
    >>> service = EnhancedConversionService(config)
    >>> result = service.convert()
    >>>
    >>> if result.success:
    ...     print(f"转换成功，创建了 {len(result.created_files)} 个文件")
    ... else:
    ...     print(f"转换失败: {result.error_message}")
"""

import gc
from typing import Optional, Callable, Dict, List
from dataclasses import dataclass, field

from config import Config
from core.conversion_coordinator import ConversionCoordinator, ConversionResult


@dataclass
class EnhancedConversionResult:
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
        >>> result = EnhancedConversionResult()
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


class EnhancedConversionService:
    """
    转换服务类

    作为ASC到CSV转换流程的核心协调器，本类现在作为Facade模式，
    委托给 core.conversion_coordinator.ConversionCoordinator 处理。

    .. deprecated::
        此类已弃用。请直接使用 core.conversion_coordinator.ConversionCoordinator
        或保持使用此类（向后兼容）。

    Attributes:
        config (Config): 配置对象

    Examples:
        >>> from config import Config
        >>> config = Config(
        ...     asc_file='test.asc',
        ...     dbc_files=['test.dbc'],
        ...     output_dir='output',
        ...     sample_interval=0.1
        ... )
        >>>
        >>> service = EnhancedConversionService(config)
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
        self._coordinator: Optional[ConversionCoordinator] = None

    def convert(
        self,
        progress_callback: Optional[Callable[[float, int], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None,
        overwrite: bool = False
    ) -> EnhancedConversionResult:
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
            EnhancedConversionResult: 转换结果对象
                - success: 转换是否成功
                - created_files: 创建的文件列表
                - discovered_groups: 发现的分组列表
                - group_statistics: 分组统计信息
                - error_message: 错误信息（仅在失败时）

        Raises:
            不直接抛出异常，所有异常都会被捕获并记录到 error_message

        Examples:
            >>> service = EnhancedConversionService(config)
            >>> result = service.convert()
            >>> if result.success:
            ...     print(f"成功创建 {len(result.created_files)} 个文件")
            ...     for group in result.discovered_groups:
            ...         print(f"  {group}: {result.group_statistics[group]} 个信号")
        """
        self._coordinator = ConversionCoordinator(self.config)
        core_result = self._coordinator.execute(
            progress_callback=progress_callback,
            log_callback=log_callback,
            overwrite=overwrite
        )

        result = EnhancedConversionResult(
            success=core_result.success,
            original_count=core_result.original_count,
            sampled_count=core_result.sampled_count,
            signal_count=core_result.signal_count,
            created_files=core_result.created_files,
            skipped_files=core_result.skipped_files,
            output_dir=core_result.output_dir,
            error_message=core_result.error_message,
            group_statistics=core_result.group_statistics,
            discovered_groups=core_result.discovered_groups
        )

        return result

    def get_group_statistics(self) -> Dict[str, int]:
        """
        获取分组统计信息

        Returns:
            Dict[str, int]: 分组名称到信号数量的映射
        """
        if self._coordinator and self._coordinator.single_processor:
            processor = self._coordinator.single_processor
            if processor.data_processor:
                return processor.data_processor.get_group_statistics()
        return {}

    def get_sorted_groups(self) -> List[str]:
        """
        获取排序后的分组列表

        Returns:
            List[str]: 排序后的组名称列表
        """
        if self._coordinator and self._coordinator.single_processor:
            processor = self._coordinator.single_processor
            if processor.data_processor:
                return processor.data_processor.sorted_groups
        return []
