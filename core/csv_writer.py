# asc_to_csv/core/csv_writer.py
"""
CSV写入器模块

本模块实现了将分组后的信号数据写入CSV文件的功能。支持为每个唯一组名称
创建独立的CSV文件，并提供空值填充、文件存在性检查等功能。

主要功能：
    - 为每个分组创建独立的CSV文件
    - 空值填充：使用时间区间内的有效值填充缺失数据
    - 文件存在性检查：避免重复创建已存在的文件
    - 汇总报告生成：创建Summary.csv汇总文件

使用示例：
    >>> from core.csv_writer import CSVWriter
    >>> writer = CSVWriter(output_dir='./output', overwrite=True)
    >>> result = writer.write_all_groups(
    ...     classified_signals={'BATP1': ['sig1', 'sig2'], 'Others': ['sig3']},
    ...     sorted_timestamps=[0.0, 0.1, 0.2],
    ...     aggregated_data={0.0: {'sig1': 1.0, 'sig2': 2.0, 'sig3': 3.0}},
    ...     signal_info={'sig1': {'unit': 'V'}}
    ... )
"""

import os
import re
import csv
from typing import Dict, List, Any, Optional, Set
from collections import defaultdict

from core.utils import safe_value


class CSVWriter:
    """
    CSV写入器

    为每个唯一组名称创建独立的CSV文件，支持空值填充和文件覆盖控制。

    Attributes:
        output_dir (str): 输出目录路径
        encoding (str): CSV文件编码，默认为utf-8-sig
        fill_interval (float): 空值填充时间间隔（秒），默认为0.5秒
        overwrite (bool): 是否覆盖已存在的文件
        created_files (Set[str]): 已创建的文件路径集合
        existing_files (Set[str]): 已存在的文件路径集合（跳过未覆盖）

    文件命名规则：
        - 组名称会被清理，移除文件系统不支持的特殊字符
        - 文件名格式：{组名称}.csv
        - 示例：BATP1.csv, BATPS.csv, Others.csv

    空值填充算法：
        1. 将时间轴划分为固定间隔的时间区间（默认0.5秒）
        2. 对于每个时间区间，收集该区间内所有有效信号值
        3. 使用同一区间内的有效值填充缺失值
        4. 目的：减少数据缺失，提高数据连续性
    """

    def __init__(
        self,
        output_dir: str,
        encoding: str = "utf-8-sig",
        fill_interval: float = 0.5,
        overwrite: bool = False
    ):
        """
        初始化CSV写入器

        Args:
            output_dir: 输出目录路径
            encoding: CSV文件编码
            fill_interval: 空值填充时间间隔（秒）
            overwrite: 是否覆盖已存在的文件
        """
        self.output_dir = output_dir
        self.encoding = encoding
        self.fill_interval = fill_interval
        self.overwrite = overwrite

        self.created_files: Set[str] = set()
        self.existing_files: Set[str] = set()

    def _get_time_bucket(self, timestamp: float) -> int:
        """计算时间戳所属的时间区间编号"""
        return int(timestamp // self.fill_interval)

    def _fill_missing_values(
        self,
        sorted_timestamps: List[float],
        aggregated_data: Dict[float, Dict[str, Any]],
        signals: List[str]
    ) -> Dict[float, Dict[str, Any]]:
        """填充缺失值"""
        bucket_values: Dict[int, Dict[str, Any]] = defaultdict(dict)
        bucket_timestamps: Dict[int, List[float]] = defaultdict(list)

        for timestamp in sorted_timestamps:
            bucket = self._get_time_bucket(timestamp)
            bucket_timestamps[bucket].append(timestamp)
            original_data = aggregated_data.get(timestamp, {})

            for sig_name in signals:
                if sig_name in original_data and original_data[sig_name] is not None:
                    bucket_values[bucket][sig_name] = original_data[sig_name]

        filled_data = {}
        for timestamp in sorted_timestamps:
            bucket = self._get_time_bucket(timestamp)
            original_data = aggregated_data.get(timestamp, {})
            filled_row = {}

            for sig_name in signals:
                if sig_name in original_data and original_data[sig_name] is not None:
                    filled_row[sig_name] = original_data[sig_name]
                elif sig_name in bucket_values[bucket]:
                    filled_row[sig_name] = bucket_values[bucket][sig_name]
                else:
                    filled_row[sig_name] = None

            filled_data[timestamp] = filled_row

        return filled_data

    def _sanitize_filename(self, group_name: str) -> str:
        """清理组名称，生成有效的文件名"""
        invalid_chars = r'[<>:"/\\|?*\x00-\x1f]'
        cleaned = re.sub(invalid_chars, '_', group_name)
        cleaned = cleaned.strip('. ')
        if not cleaned:
            cleaned = "Unknown"
        if len(cleaned) > 200:
            cleaned = cleaned[:200]
        return cleaned

    def _check_file_exists(self, filename: str) -> bool:
        """检查文件是否已存在"""
        file_path = os.path.join(self.output_dir, filename)
        return os.path.exists(file_path)

    def write_group_file(
        self,
        group_name: str,
        signals: List[str],
        sorted_timestamps: List[float],
        filled_data: Dict,
        signal_info: Dict
    ) -> Optional[str]:
        """写入单个分组文件"""
        safe_group_name = self._sanitize_filename(group_name)
        csv_filename = f"{safe_group_name}.csv"
        file_path = os.path.join(self.output_dir, csv_filename)

        if not self.overwrite and self._check_file_exists(csv_filename):
            print(f"  跳过已存在文件: {csv_filename}")
            self.existing_files.add(file_path)
            return None

        sorted_signals = sorted(signals)
        header = self._generate_header(sorted_signals, signal_info)

        try:
            with open(file_path, 'w', newline='', encoding=self.encoding) as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(header)

                for timestamp in sorted_timestamps:
                    data = filled_data.get(timestamp, {})
                    row = self._build_row(timestamp, sorted_signals, data)
                    writer.writerow(row)

            print(f"  创建文件: {csv_filename}")
            self.created_files.add(file_path)
            return file_path

        except Exception as e:
            print(f"  创建文件失败: {csv_filename} - {e}")
            return None

    def write_all_groups(
        self,
        classified_signals: Dict[str, List[str]],
        sorted_timestamps: List[float],
        aggregated_data: Dict[float, Dict[str, Any]],
        signal_info: Dict[str, Dict[str, str]]
    ) -> Dict[str, Any]:
        """为所有分组创建CSV文件"""
        result = {
            'created_files': [],
            'skipped_files': [],
            'total_groups': len(classified_signals),
            'created_count': 0,
            'skipped_count': 0
        }

        all_signals = []
        for signals in classified_signals.values():
            all_signals.extend(signals)
        all_signals = sorted(set(all_signals))

        filled_data = self._fill_missing_values(
            sorted_timestamps, aggregated_data, all_signals
        )

        print(f"  已完成空值填充（填充间隔: {self.fill_interval}秒）")

        for group_name in sorted(classified_signals.keys()):
            signals = classified_signals[group_name]
            file_path = self.write_group_file(
                group_name, signals, sorted_timestamps,
                filled_data, signal_info
            )

            if file_path:
                result['created_files'].append(file_path)
                result['created_count'] += 1
            else:
                result['skipped_files'].append(group_name)
                result['skipped_count'] += 1

        return result

    def write_summary_file(
        self,
        classified_signals: Dict[str, List[str]],
        sorted_timestamps: List[float],
        result_stats: Dict[str, Any]
    ) -> str:
        """写入汇总文件"""
        summary_filename = os.path.join(self.output_dir, "Summary.csv")

        with open(summary_filename, 'w', newline='', encoding=self.encoding) as csvfile:
            writer = csv.writer(csvfile)

            writer.writerow(["数据转换汇总报告"])
            writer.writerow([])
            writer.writerow(["分组模式", "动态组名称提取"])
            writer.writerow(["分组规则", "BatP+数字 或 BatP+1-2个字母"])
            writer.writerow(["空值填充间隔", f"{self.fill_interval}秒"])
            writer.writerow(["覆盖模式", "是" if self.overwrite else "否"])
            writer.writerow([])
            writer.writerow(["数据统计"])
            writer.writerow(["采样后时间点数", len(sorted_timestamps)])
            writer.writerow(["信号总数", sum(len(s) for s in classified_signals.values())])
            writer.writerow(["分组数量", len(classified_signals)])
            writer.writerow([])
            writer.writerow(["文件生成统计"])
            writer.writerow(["成功创建", result_stats.get('created_count', 0)])
            writer.writerow(["跳过已存在", result_stats.get('skipped_count', 0)])
            writer.writerow([])
            writer.writerow(["各分组详情"])
            writer.writerow(["分组名称", "信号数量", "文件名", "状态"])

            for group_name in sorted(classified_signals.keys()):
                signals = classified_signals[group_name]
                safe_group_name = self._sanitize_filename(group_name)
                csv_filename = f"{safe_group_name}.csv"

                file_path = os.path.join(self.output_dir, csv_filename)
                if file_path in self.created_files:
                    status = "已创建"
                elif file_path in self.existing_files:
                    status = "已存在（跳过）"
                else:
                    status = "未创建"

                writer.writerow([
                    group_name,
                    len(signals),
                    csv_filename,
                    status
                ])

        print(f"  创建汇总文件: {summary_filename}")
        return summary_filename

    def _generate_header(self, signals: List[str], signal_info: Dict) -> List[str]:
        """生成CSV表头"""
        header = ["Time[s]"]
        for sig_name in signals:
            unit = signal_info.get(sig_name, {}).get('unit', '')
            short_name = sig_name.split('::')[-1]
            if unit:
                header.append(f"{short_name}[{unit}]")
            else:
                header.append(short_name)
        return header

    def _build_row(
        self,
        timestamp: float,
        signals: List[str],
        data: Dict
    ) -> List[Any]:
        """构建数据行"""
        row = [round(timestamp, 1)]
        for sig_name in signals:
            if sig_name in data and data[sig_name] is not None:
                row.append(safe_value(data[sig_name]))
            else:
                row.append("")
        return row

    def get_created_files(self) -> List[str]:
        """获取所有创建的文件列表"""
        return sorted(self.created_files)

    def get_existing_files(self) -> List[str]:
        """获取已存在的文件列表"""
        return sorted(self.existing_files)

    def clear(self):
        """清空写入器状态"""
        self.created_files.clear()
        self.existing_files.clear()


EnhancedCSVWriter = CSVWriter