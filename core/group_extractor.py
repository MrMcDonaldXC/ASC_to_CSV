# asc_to_csv/core/group_extractor.py
"""
信号分组提取器模块

本模块实现了基于信号命名规则的动态分组功能。通过正则表达式匹配，
从信号名称中提取组标识符，为每个唯一组创建独立的CSV文件。

分组规则：
    - BatP + 数字：BatP1, BatP10, BatP28 等
    - BatP + 1-2个字母：BatPS, BatPQ, BatPL, BatPR 等
    - 不符合以上规则的信号归入 Others 组

使用示例：
    >>> from core.group_extractor import GroupExtractor
    >>> extractor = GroupExtractor()
    >>> group = extractor.extract_from_signal_name('test.dbc::BatP3_Msg::signal')
    >>> print(group)  # 输出: BatP3

    >>> # 批量分组
    >>> signals = ['test.dbc::BatP1_Msg::sig1', 'test.dbc::FMC_Msg::sig2']
    >>> classified = extractor.classify_signals(signals)
    >>> print(classified)  # {'BatP1': ['test.dbc::BatP1_Msg::sig1'], 'Others': ['test.dbc::FMC_Msg::sig2']}
"""

import re
from typing import List, Set, Dict, Optional, Tuple


class ExtractionStrategy:
    """分组提取策略枚举"""
    AUTO_DISCOVER = "auto_discover"
    MESSAGE_PREFIX = "message_prefix"
    SIGNAL_PREFIX = "signal_prefix"
    BATP_PATTERN = "batp_pattern"
    CUSTOM_PATTERN = "custom_pattern"


class GroupExtractor:
    """
    信号分组提取器

    根据信号名称中的特定模式提取组标识符，支持大小写不敏感匹配。

    Attributes:
        discovered_groups (Set[str]): 已发现的组名称集合
        group_mapping (Dict[str, Optional[str]]): 信号名称到组名称的映射缓存

    分组规则详情：
        1. 数字组：匹配 "BatP" 后跟一个或多个数字
           - 示例：BatP1, BatP10, BatP28
           - 输出：BatP1, BatP10, BatP28

        2. 字母组：匹配 "BatP" 后跟1-2个大写字母
           - 示例：BatPS, BatPQ, BatPL, BatPR
           - 输出：BatPS, BatPQ, BatPL, BatPR

        3. Others组：不符合以上规则的信号
           - 示例：FMC_signal, HVMS_signal, BMS_signal
           - 输出：归入 Others 组

    边界条件处理：
        - 空信号名称：返回 None
        - 无效字符：替换为下划线
        - 超长名称：截断至200字符
    """

    VALID_GROUP_PATTERN = re.compile(r'(?i)(BatP\d+|BatP[A-Z]{1,2})(?=_|$|[^a-zA-Z0-9])')

    INVALID_CHARS = r'[<>:"/\\|?*\x00-\x1f]'

    def __init__(self, strategy: str = ExtractionStrategy.AUTO_DISCOVER):
        """
        初始化分组提取器

        Args:
            strategy: 分组策略
        """
        self.strategy = strategy
        self.discovered_groups: Set[str] = set()
        self.group_mapping: Dict[str, Optional[str]] = {}
        self._custom_patterns: List[re.Pattern] = []

    def add_custom_pattern(self, pattern: str):
        """添加自定义模式"""
        self._custom_patterns.append(re.compile(pattern, re.IGNORECASE))

    def extract_from_signal_name(self, signal_name: str) -> Optional[str]:
        """
        从信号名称中提取组名称

        Args:
            signal_name: 完整的信号名称
                格式通常为：{DBC文件名}::{消息名称}::{信号名称}
                示例：'800V_BMS.dbc::BatP3_BMS_CellVolt::P3_AvgCellVlt'

        Returns:
            Optional[str]: 提取的组名称（保持原始大小写）
                - 成功匹配：返回组名称，如 'BatP3', 'BatPS'
                - 匹配失败：返回 None（表示应归入 Others 组）
        """
        if not signal_name:
            return None

        if signal_name in self.group_mapping:
            return self.group_mapping[signal_name]

        match = self.VALID_GROUP_PATTERN.search(signal_name)

        if match:
            group_name = match.group(1)
            group_name = self._sanitize_group_name(group_name)
            self.group_mapping[signal_name] = group_name
            self.discovered_groups.add(group_name)
            return group_name

        self.group_mapping[signal_name] = None
        return None

    def _sanitize_group_name(self, group_name: str) -> str:
        """清理组名称"""
        cleaned = re.sub(self.INVALID_CHARS, '_', group_name)
        cleaned = cleaned.strip('. ')
        if not cleaned:
            cleaned = "Unknown"
        if len(cleaned) > 200:
            cleaned = cleaned[:200]
        return cleaned

    def classify_signals(self, signal_names: List[str]) -> Dict[str, List[str]]:
        """
        对信号列表进行批量分组

        Args:
            signal_names: 信号名称列表

        Returns:
            Dict[str, List[str]]: 分组结果字典
        """
        classified: Dict[str, List[str]] = {}

        for signal_name in signal_names:
            group_name = self.extract_from_signal_name(signal_name)

            if group_name:
                if group_name not in classified:
                    classified[group_name] = []
                classified[group_name].append(signal_name)
            else:
                if "Others" not in classified:
                    classified["Others"] = []
                classified["Others"].append(signal_name)

        return classified

    def get_discovered_groups(self) -> List[str]:
        """获取所有已发现的组名称（排序后）"""
        return sorted(self.discovered_groups, key=self._sort_key)

    def _sort_key(self, name: str) -> Tuple[int, int, str]:
        """生成组名称的排序键"""
        if name == "Others":
            return (99, 0, name)
        elif name.lower().startswith("batp") and name[4:].isdigit():
            return (0, int(name[4:]), name)
        elif name.lower().startswith("batp"):
            return (1, 0, name)
        else:
            return (50, 0, name)

    def get_group_count(self) -> int:
        """获取已发现的组数量"""
        return len(self.discovered_groups)

    def clear(self):
        """清空提取器状态"""
        self.discovered_groups.clear()
        self.group_mapping.clear()

    def get_statistics(self) -> Dict[str, any]:
        """获取提取器统计信息"""
        return {
            'discovered_groups_count': len(self.discovered_groups),
            'mapped_signals_count': len(self.group_mapping),
            'groups': sorted(self.discovered_groups, key=self._sort_key)
        }