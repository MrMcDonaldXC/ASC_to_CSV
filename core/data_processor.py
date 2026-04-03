# asc_to_csv/core/data_processor.py
"""
数据处理器模块

本模块负责处理从ASC文件解析出的信号数据，包括数据聚合和信号分组。
与GroupExtractor协作，将信号按照命名规则分类到不同的组。

主要功能：
    - 聚合采样数据：取每个时间间隔内的最后一个值
    - 信号分组：使用GroupExtractor进行动态分组
    - 分组排序：按特定规则对分组进行排序

数据流程：
    1. ASCParser解析ASC文件，生成采样数据
    2. DataProcessor聚合采样数据
    3. GroupExtractor对信号进行分组
    4. CSVWriter将分组数据写入CSV文件

使用示例：
    >>> from core.data_processor import DataProcessor
    >>> processor = DataProcessor()
    >>> processor.aggregate(sampled_data)
    >>> processor.classify_signals(found_signals)
    >>> print(processor.get_group_statistics())
"""

import gc
from typing import Dict, List, Set, Optional, Tuple

from core.group_extractor import GroupExtractor


class DataProcessor:
    """
    数据处理器

    负责聚合采样数据并对信号进行分组分类。作为ASC解析器和CSV写入器
    之间的数据处理层，提供数据转换和分组功能。

    Attributes:
        aggregated_data (Dict[float, Dict[str, any]]): 聚合后的数据
        classified_signals (Dict[str, List[str]]): 分类后的信号
        sorted_groups (List[str]): 排序后的组名称列表
        group_extractor (GroupExtractor): 组名称提取器实例

    数据处理流程：
        1. aggregate(): 聚合采样数据
        2. classify_signals(): 对信号进行分组
        3. get_sorted_timestamps(): 获取排序后的时间戳
        4. clear(): 清理数据释放内存
    """

    def __init__(self):
        """初始化数据处理器"""
        self.aggregated_data: Dict[float, Dict[str, any]] = {}
        self.classified_signals: Dict[str, List[str]] = {}
        self.sorted_groups: List[str] = []
        self.group_extractor = GroupExtractor()

    def aggregate(self, sampled_data: Dict) -> None:
        """
        聚合采样数据

        将ASC解析器输出的采样数据进行聚合，取每个时间间隔内的最后一个值。

        Args:
            sampled_data: 采样数据（来自ASCParser）
        """
        for sampled_time, signals in sampled_data.items():
            self.aggregated_data[sampled_time] = {}
            for signal_name, values in signals.items():
                self.aggregated_data[sampled_time][signal_name] = values[-1]

    def classify_signals(self, found_signals: Set[str]) -> None:
        """
        对信号进行分组

        Args:
            found_signals: 发现的信号集合
        """
        self.classified_signals = self.group_extractor.classify_signals(list(found_signals))
        self.sorted_groups = self._sort_groups()

    def _sort_groups(self) -> List[str]:
        """对分组进行排序"""
        groups = list(self.classified_signals.keys())

        def sort_key(name: str) -> Tuple[int, int, str]:
            if name == "Others":
                return (99, 0, name)
            elif name.startswith("BATP") and name[4:].isdigit():
                return (0, int(name[4:]), name)
            elif name.startswith("BATP"):
                return (1, 0, name)
            else:
                return (50, 0, name)

        return sorted(groups, key=sort_key)

    def get_sorted_timestamps(self) -> List[float]:
        """获取排序后的时间戳列表"""
        return sorted(self.aggregated_data.keys())

    def get_group_statistics(self) -> Dict[str, int]:
        """获取各分组的统计信息"""
        return {
            group_name: len(signals)
            for group_name, signals in self.classified_signals.items()
        }

    def get_extractor_statistics(self) -> Dict[str, any]:
        """获取组提取器统计信息"""
        return self.group_extractor.get_statistics()

    def get_group_for_signal(self, signal_name: str) -> Optional[str]:
        """获取信号所属的分组"""
        return self.group_extractor.extract_from_signal_name(signal_name)

    def clear(self):
        """清理内存中的数据"""
        self.aggregated_data.clear()
        self.classified_signals.clear()
        self.sorted_groups.clear()
        self.group_extractor.clear()
        gc.collect()

    def __del__(self):
        """析构函数，确保资源释放"""
        if hasattr(self, 'aggregated_data'):
            self.aggregated_data.clear()
        if hasattr(self, 'classified_signals'):
            self.classified_signals.clear()


EnhancedDataProcessor = DataProcessor