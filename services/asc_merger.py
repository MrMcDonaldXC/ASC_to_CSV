# asc_to_csv/services/asc_merger.py
"""
ASC文件拼接模块

本模块负责多个ASC文件的拼接功能，支持：
    - 基于文件名的排序（按时间戳数值排序）
    - 文件内容按顺序拼接
    - 时间戳连续性处理
    - 错误检测和报告

使用示例：
    >>> from services.asc_merger import ASCFileMerger
    >>> merger = ASCFileMerger()
    >>> sorted_files = merger.sort_files_by_time(['file2.asc', 'file1.asc'])
    >>> print(sorted_files)  # ['file1.asc', 'file2.asc']
    >>> merged_content = merger.merge_files(sorted_files)
"""

import os
import re
from typing import List, Tuple, Optional, Callable
from dataclasses import dataclass


@dataclass
class MergeResult:
    """
    拼接结果数据类

    Attributes:
        success: 拼接是否成功
        sorted_files: 排序后的文件列表
        total_lines: 总行数
        error_files: 出错的文件列表
        error_messages: 错误信息列表
        first_timestamp: 第一个有效时间戳
        last_timestamp: 最后一个有效时间戳
    """
    success: bool = False
    sorted_files: List[str] = None
    total_lines: int = 0
    error_files: List[str] = None
    error_messages: List[str] = None
    first_timestamp: Optional[float] = None
    last_timestamp: Optional[float] = None

    def __post_init__(self):
        if self.sorted_files is None:
            self.sorted_files = []
        if self.error_files is None:
            self.error_files = []
        if self.error_messages is None:
            self.error_messages = []


class ASCFileMerger:
    """
    ASC文件拼接器

    负责多个ASC文件的排序和拼接，保持数据的时间连续性。

    Attributes:
        time_pattern: 时间戳提取正则表达式
        ASC_PATTERN: ASC数据行正则表达式
    """

    TIME_PATTERN = re.compile(r'(\d{4}[-_]?\d{2}[-_]?\d{2}[-_]?\d{2}[-_]?\d{2}[-_]?\d{2}|\d+)')

    ASC_LINE_PATTERN = re.compile(
        r'^(\d+\.\d+)\s+(\d+)\s+([0-9A-Fa-f]+x?)\s+(Rx|Tx)\s+d\s+(\d+)\s+(([0-9A-Fa-f]{2}\s*)+)$'
    )

    HEADER_PATTERNS = [
        re.compile(r'^date\s+', re.IGNORECASE),
        re.compile(r'^base\s+', re.IGNORECASE),
        re.compile(r'^start\s+', re.IGNORECASE),
        re.compile(r'^;\s*.*$'),
    ]

    def __init__(self):
        """初始化ASC文件拼接器"""
        self.errors: List[str] = []

    def extract_time_from_filename(self, filename: str) -> Optional[float]:
        """
        从文件名中提取时间戳数值

        支持多种时间格式：
            - 2024-01-15_14-30-00.asc
            - 20240115_143000.asc
            - log_12345.asc (使用数字作为时间标识)

        Args:
            filename: 文件名或文件路径

        Returns:
            Optional[float]: 提取的时间戳数值，如果无法提取则返回None
        """
        basename = os.path.basename(filename)
        match = self.TIME_PATTERN.search(basename)

        if match:
            time_str = match.group(1).replace('-', '').replace('_', '').replace(':', '')
            try:
                if len(time_str) >= 14:
                    return float(time_str)
                elif len(time_str) >= 8:
                    return float(time_str[:8])
                else:
                    return float(time_str)
            except ValueError:
                pass

        return None

    def validate_asc_file(self, file_path: str) -> Tuple[bool, str]:
        """
        验证ASC文件格式

        Args:
            file_path: ASC文件路径

        Returns:
            Tuple[bool, str]: (是否有效, 错误信息)
        """
        if not os.path.exists(file_path):
            return False, f"文件不存在: {file_path}"

        if not os.path.isfile(file_path):
            return False, f"不是有效文件: {file_path}"

        if not file_path.lower().endswith('.asc'):
            return False, f"文件不是.asc格式: {file_path}"

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                f.read(1024)
            return True, ""
        except PermissionError:
            return False, f"无权限读取文件: {file_path}"
        except Exception as e:
            return False, f"读取文件失败: {str(e)}"

    def sort_files_by_time(self, file_paths: List[str],
                           progress_callback: Optional[Callable[[str], None]] = None) -> List[str]:
        """
        根据文件名中的时间戳对ASC文件排序

        Args:
            file_paths: ASC文件路径列表
            progress_callback: 进度回调函数

        Returns:
            List[str]: 排序后的文件路径列表

        Raises:
            ValueError: 当文件列表为空或无法提取时间戳时
        """
        if not file_paths:
            raise ValueError("文件列表为空")

        if progress_callback:
            progress_callback("正在验证ASC文件...")

        valid_files = []
        for file_path in file_paths:
            is_valid, error_msg = self.validate_asc_file(file_path)
            if is_valid:
                valid_files.append(file_path)
            else:
                if progress_callback:
                    progress_callback(f"警告: 跳过无效文件 {file_path}: {error_msg}")

        if not valid_files:
            raise ValueError("没有有效的ASC文件")

        if progress_callback:
            progress_callback("正在提取时间戳...")

        files_with_time = []
        for file_path in valid_files:
            time_value = self.extract_time_from_filename(file_path)
            files_with_time.append((file_path, time_value))

        files_with_time.sort(key=lambda x: (x[1] is None, x[1]))

        sorted_files = [f[0] for f in files_with_time]

        if progress_callback:
            for i, f in enumerate(sorted_files):
                time_val = self.extract_time_from_filename(f)
                progress_callback(f"  [{i+1}/{len(sorted_files)}] {os.path.basename(f)} -> 时间戳: {time_val}")

        return sorted_files

    def get_first_timestamp(self, file_path: str) -> Optional[float]:
        """
        获取文件中第一个有效时间戳

        Args:
            file_path: ASC文件路径

        Returns:
            Optional[float]: 第一个有效时间戳
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith(';'):
                        continue

                    match = self.ASC_LINE_PATTERN.match(line)
                    if match:
                        return float(match.group(1))
        except Exception:
            pass

        return None

    def get_last_timestamp(self, file_path: str) -> Optional[float]:
        """
        获取文件中最后一个有效时间戳

        Args:
            file_path: ASC文件路径

        Returns:
            Optional[float]: 最后一个有效时间戳
        """
        try:
            last_ts = None
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith(';'):
                        continue

                    match = self.ASC_LINE_PATTERN.match(line)
                    if match:
                        last_ts = float(match.group(1))

            return last_ts
        except Exception:
            pass

        return None

    def is_header_line(self, line: str) -> bool:
        """
        判断是否为ASC文件头行

        Args:
            line: 文件行

        Returns:
            bool: 是否为头行
        """
        line = line.strip()

        if not line:
            return True

        for pattern in self.HEADER_PATTERNS:
            if pattern.match(line):
                return True

        return False

    def merge_files(self, file_paths: List[str],
                    progress_callback: Optional[Callable[[str], None]] = None) -> MergeResult:
        """
        拼接多个ASC文件内容

        Args:
            file_paths: 排序后的ASC文件路径列表
            progress_callback: 进度回调函数

        Returns:
            MergeResult: 拼接结果
        """
        result = MergeResult()
        result.sorted_files = file_paths

        if not file_paths:
            result.success = False
            result.error_messages.append("文件列表为空")
            return result

        if len(file_paths) == 1:
            result.success = True
            result.first_timestamp = self.get_first_timestamp(file_paths[0])
            result.last_timestamp = self.get_last_timestamp(file_paths[0])
            return result

        if progress_callback:
            progress_callback("正在检查文件时间戳连续性...")

        first_ts = self.get_first_timestamp(file_paths[0])
        last_ts = self.get_last_timestamp(file_paths[-1])
        result.first_timestamp = first_ts
        result.last_timestamp = last_ts

        if first_ts is None:
            result.success = False
            result.error_messages.append(f"无法获取第一个文件的时间戳: {file_paths[0]}")
            return result

        if progress_callback:
            progress_callback(f"文件时间范围: {first_ts} -> {last_ts}")

        try:
            merged_lines = []
            global_line_count = 0

            for file_idx, file_path in enumerate(file_paths):
                if progress_callback:
                    progress_callback(f"正在处理文件 [{file_idx+1}/{len(file_paths)}]: {os.path.basename(file_path)}")

                file_line_count = 0
                header_written = False

                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        line_stripped = line.strip()

                        if self.is_header_line(line_stripped):
                            if not header_written and merged_lines:
                                merged_lines.append(line)
                            continue

                        if not self.ASC_LINE_PATTERN.match(line_stripped):
                            continue

                        merged_lines.append(line)
                        file_line_count += 1
                        global_line_count += 1

                    header_written = True

                result.total_lines = global_line_count

                if progress_callback:
                    progress_callback(f"  -> 处理了 {file_line_count} 行数据")

            result.success = True

        except PermissionError as e:
            result.success = False
            result.error_messages.append(f"权限错误: {str(e)}")
        except Exception as e:
            result.success = False
            result.error_messages.append(f"拼接失败: {type(e).__name__}: {str(e)}")

        return result

    def get_merged_content(self, file_paths: List[str]) -> Tuple[List[str], MergeResult]:
        """
        获取拼接后的文件内容

        Args:
            file_paths: 排序后的ASC文件路径列表

        Returns:
            Tuple[List[str], MergeResult]: (合并后的行列表, 合并结果)
        """
        result = self.merge_files(file_paths)

        if not result.success:
            return [], result

        merged_lines = []

        for file_path in file_paths:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if self.is_header_line(line.strip()):
                        if merged_lines:
                            merged_lines.append(line)
                        continue

                    if self.ASC_LINE_PATTERN.match(line.strip()):
                        merged_lines.append(line)

        return merged_lines, result


def sort_and_validate_asc_files(file_paths: List[str],
                                 progress_callback: Optional[Callable[[str], None]] = None) -> Tuple[List[str], List[str]]:
    """
    排序并验证ASC文件列表

    Args:
        file_paths: ASC文件路径列表
        progress_callback: 进度回调函数

    Returns:
        Tuple[List[str], List[str]]: (排序后的文件列表, 无效文件列表)
    """
    merger = ASCFileMerger()

    sorted_files = merger.sort_files_by_time(file_paths, progress_callback)

    invalid_files = [f for f in file_paths if f not in sorted_files]

    return sorted_files, invalid_files


def merge_asc_files(file_paths: List[str],
                   output_path: str = None,
                   progress_callback: Optional[Callable[[str], None]] = None) -> MergeResult:
    """
    合并多个ASC文件并可选地保存到输出文件

    Args:
        file_paths: ASC文件路径列表
        output_path: 输出文件路径，如果为None则不保存
        progress_callback: 进度回调函数

    Returns:
        MergeResult: 合并结果
    """
    if not file_paths:
        result = MergeResult()
        result.success = False
        result.error_messages.append("文件列表为空")
        return result

    merger = ASCFileMerger()

    sorted_files = merger.sort_files_by_time(file_paths, progress_callback)

    result = merger.merge_files(sorted_files, progress_callback)

    if result.success and output_path:
        if progress_callback:
            progress_callback(f"正在保存合并后的文件: {output_path}")

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                for file_path in sorted_files:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as src:
                        for line in src:
                            f.write(line)

            if progress_callback:
                progress_callback(f"文件已保存: {output_path}")

        except Exception as e:
            result.success = False
            result.error_messages.append(f"保存文件失败: {str(e)}")

    return result