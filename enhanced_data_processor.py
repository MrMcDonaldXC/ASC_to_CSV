# asc_to_csv/enhanced_data_processor.py
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
    2. EnhancedDataProcessor聚合采样数据
    3. GroupExtractor对信号进行分组
    4. EnhancedCSVWriter将分组数据写入CSV文件

使用示例：
    >>> from enhanced_data_processor import EnhancedDataProcessor
    >>> processor = EnhancedDataProcessor()
    >>> processor.aggregate(sampled_data)
    >>> processor.classify_signals(found_signals)
    >>> print(processor.get_group_statistics())
"""

import gc
from typing import Dict, List, Set, Optional, Tuple

from group_extractor import GroupExtractor


class EnhancedDataProcessor:
    """
    数据处理器
    
    负责聚合采样数据并对信号进行分组分类。作为ASC解析器和CSV写入器
    之间的数据处理层，提供数据转换和分组功能。
    
    Attributes:
        aggregated_data (Dict[float, Dict[str, any]]): 聚合后的数据
            - 键：采样时间戳
            - 值：{信号名称: 信号值} 字典
        classified_signals (Dict[str, List[str]]): 分类后的信号
            - 键：组名称（如 'BATP1', 'BATPS', 'Others'）
            - 值：属于该组的信号名称列表
        sorted_groups (List[str]): 排序后的组名称列表
        group_extractor (GroupExtractor): 组名称提取器实例
    
    数据处理流程：
        1. aggregate(): 聚合采样数据
        2. classify_signals(): 对信号进行分组
        3. get_sorted_timestamps(): 获取排序后的时间戳
        4. clear(): 清理数据释放内存
    """
    
    def __init__(self):
        """
        初始化数据处理器
        
        创建空的聚合数据字典、分类信号字典和组提取器实例。
        """
        self.aggregated_data: Dict[float, Dict[str, any]] = {}
        self.classified_signals: Dict[str, List[str]] = {}
        self.sorted_groups: List[str] = []
        self.group_extractor = GroupExtractor()
    
    def aggregate(self, sampled_data: Dict) -> None:
        """
        聚合采样数据
        
        将ASC解析器输出的采样数据进行聚合，取每个时间间隔内的最后一个值。
        这是因为CAN信号在同一采样间隔内可能有多个更新，我们只需要最新的值。
        
        Args:
            sampled_data: 采样数据（来自ASCParser）
                - 键：采样时间戳
                - 值：{信号名称: [值列表]} 字典
                - 每个信号在同一个采样间隔内可能有多个值
        
        Side Effects:
            更新 self.aggregated_data
        
        Examples:
            >>> processor = EnhancedDataProcessor()
            >>> sampled_data = {
            ...     0.0: {'signal1': [1.0, 1.5, 2.0]},
            ...     0.1: {'signal1': [2.5, 3.0]}
            ... }
            >>> processor.aggregate(sampled_data)
            >>> print(processor.aggregated_data)
            {0.0: {'signal1': 2.0}, 0.1: {'signal1': 3.0}}
        
        Note:
            - 使用 values[-1] 获取最后一个值
            - 如果值列表为空，该信号不会被添加到聚合数据中
        """
        for sampled_time, signals in sampled_data.items():
            self.aggregated_data[sampled_time] = {}
            for signal_name, values in signals.items():
                self.aggregated_data[sampled_time][signal_name] = values[-1]
    
    def classify_signals(self, found_signals: Set[str]) -> None:
        """
        对信号进行分组
        
        使用GroupExtractor对发现的所有信号进行分组分类。
        分组规则：
            - BatP + 数字：BATP1, BATP10, BATP28 等
            - BatP + 1-2个字母：BATPS, BATPQ, BATPL, BATPR 等
            - 不符合规则的归入 Others
        
        Args:
            found_signals: 发现的信号集合
                - 通常来自 ASCParser.found_signals
                - 包含所有在ASC文件中出现的信号名称
        
        Side Effects:
            - 更新 self.classified_signals
            - 更新 self.sorted_groups
        
        Examples:
            >>> processor = EnhancedDataProcessor()
            >>> signals = {'test.dbc::BatP1_Msg::sig1', 'test.dbc::FMC_Msg::sig2'}
            >>> processor.classify_signals(signals)
            >>> print(processor.classified_signals)
            {'BATP1': ['test.dbc::BatP1_Msg::sig1'], 'Others': ['test.dbc::FMC_Msg::sig2']}
        """
        self.classified_signals = self.group_extractor.classify_signals(list(found_signals))
        self.sorted_groups = self._sort_groups()
    
    def _sort_groups(self) -> List[str]:
        """
        对分组进行排序
        
        排序规则：
            1. BATP数字组：按数字升序排列
               - BATP1, BATP2, BATP10, BATP28, ...
            2. BATP字母组：按字母顺序排列
               - BATPE, BATPL, BATPQ, BATPR, BATPS, ...
            3. 其他组：按名称排序
            4. Others：排在最后
        
        Returns:
            List[str]: 排序后的组名称列表
        
        Note:
            - 数字组按数值大小排序，不是按字符串排序
            - 例如 BATP2 排在 BATP10 之前
        """
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
        """
        获取排序后的时间戳列表
        
        Returns:
            List[float]: 按升序排列的时间戳列表
        
        Examples:
            >>> processor = EnhancedDataProcessor()
            >>> processor.aggregated_data = {0.3: {}, 0.1: {}, 0.2: {}}
            >>> processor.get_sorted_timestamps()
            [0.1, 0.2, 0.3]
        """
        return sorted(self.aggregated_data.keys())
    
    def get_group_statistics(self) -> Dict[str, int]:
        """
        获取各分组的统计信息
        
        Returns:
            Dict[str, int]: 分组名称到信号数量的映射
        
        Examples:
            >>> processor = EnhancedDataProcessor()
            >>> processor.classified_signals = {'BATP1': ['sig1', 'sig2'], 'Others': ['sig3']}
            >>> processor.get_group_statistics()
            {'BATP1': 2, 'Others': 1}
        """
        return {
            group_name: len(signals) 
            for group_name, signals in self.classified_signals.items()
        }
    
    def get_extractor_statistics(self) -> Dict[str, any]:
        """
        获取组提取器统计信息
        
        Returns:
            Dict[str, any]: 包含以下字段的统计信息：
                - discovered_groups_count: 已发现的组数量
                - mapped_signals_count: 已映射的信号数量
                - groups: 排序后的组名称列表
        """
        return self.group_extractor.get_statistics()
    
    def get_group_for_signal(self, signal_name: str) -> Optional[str]:
        """
        获取信号所属的分组
        
        Args:
            signal_name: 完整的信号名称
        
        Returns:
            Optional[str]: 
                - 组名称（如 'BATP1', 'BATPS'）
                - None（表示应归入 Others 组）
        
        Examples:
            >>> processor = EnhancedDataProcessor()
            >>> processor.get_group_for_signal('test.dbc::BatP3_Msg::signal')
            'BATP3'
            >>> processor.get_group_for_signal('test.dbc::FMC_Msg::signal')
            None
        """
        return self.group_extractor.extract_from_signal_name(signal_name)
    
    def clear(self):
        """
        清理内存中的数据
        
        释放所有存储的数据，包括：
            - 聚合数据
            - 分类信号
            - 排序后的组列表
            - 组提取器缓存
        
        调用Python垃圾回收器释放内存。
        通常在处理完一个数据集后、开始处理下一个数据集前调用。
        """
        self.aggregated_data.clear()
        self.classified_signals.clear()
        self.sorted_groups.clear()
        self.group_extractor.clear()
        gc.collect()
    
    def __del__(self):
        """
        析构函数，确保资源释放
        
        在对象被销毁时清理数据，防止内存泄漏。
        """
        if hasattr(self, 'aggregated_data'):
            self.aggregated_data.clear()
        if hasattr(self, 'classified_signals'):
            self.classified_signals.clear()
