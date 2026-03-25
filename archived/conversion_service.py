# asc_to_csv/conversion_service.py
"""
转换服务模块
提供统一的ASC到CSV转换服务，封装完整的转换流程
"""

import gc
from typing import Optional, Callable, Dict, List, Any
from dataclasses import dataclass

from config import Config
from dbc_loader import DBCLoader
from asc_parser import ASCParser
from data_processor import DataProcessor
from csv_writer import CSVWriter


@dataclass
class ConversionResult:
    """
    转换结果数据类
    
    Attributes:
        success: 是否成功
        original_count: 原始数据点数
        sampled_count: 采样后时间点数
        signal_count: 信号数
        created_files: 创建的文件列表
        output_dir: 输出目录
        error_message: 错误信息
        group_statistics: 分组统计信息
    """
    success: bool = False
    original_count: int = 0
    sampled_count: int = 0
    signal_count: int = 0
    created_files: List[str] = None
    output_dir: str = ""
    error_message: str = ""
    group_statistics: Dict[str, int] = None
    
    def __post_init__(self):
        if self.created_files is None:
            self.created_files = []
        if self.group_statistics is None:
            self.group_statistics = {}


class ConversionService:
    """
    转换服务类
    
    封装ASC到CSV的完整转换流程，提供统一的转换接口。
    支持进度回调和日志回调，可用于CLI和GUI场景。
    
    Attributes:
        config: 配置对象
        dbc_loader: DBC加载器
        asc_parser: ASC解析器
        data_processor: 数据处理器
        csv_writer: CSV写入器
    
    Example:
        >>> config = Config(asc_file="input.asc", dbc_files=["data.dbc"], output_dir="output")
        >>> service = ConversionService(config)
        >>> result = service.convert()
        >>> if result.success:
        ...     print(f"转换完成，生成 {len(result.created_files)} 个文件")
    """
    
    def __init__(self, config: Config):
        """
        初始化转换服务
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.dbc_loader: Optional[DBCLoader] = None
        self.asc_parser: Optional[ASCParser] = None
        self.data_processor: Optional[DataProcessor] = None
        self.csv_writer: Optional[CSVWriter] = None
    
    def convert(
        self,
        progress_callback: Optional[Callable[[float, int], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> ConversionResult:
        """
        执行完整的转换流程
        
        Args:
            progress_callback: 进度回调函数，参数为(进度百分比, 已处理行数)
            log_callback: 日志回调函数，参数为日志消息
            
        Returns:
            ConversionResult: 转换结果对象
        """
        result = ConversionResult()
        
        try:
            self._log(log_callback, "开始转换...")
            self._log(log_callback, f"采样间隔: {self.config.sample_interval}秒")
            self._log(log_callback, "")
            
            if not self._validate_config(log_callback):
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
            
            created_files = self._write_csv(log_callback)
            result.created_files = created_files
            result.success = True
            
            self._log(log_callback, "")
            self._log(log_callback, "=" * 60)
            self._log(log_callback, "转换完成！")
            self._log(log_callback, f"输出目录: {self.config.output_dir}")
            self._log(log_callback, f"总计生成 {len(created_files)} 个文件")
            self._log(log_callback, "=" * 60)
            
        except Exception as e:
            result.error_message = f"{type(e).__name__}: {e}"
            self._log(log_callback, f"转换失败: {result.error_message}")
            
        finally:
            self._cleanup()
        
        return result
    
    def _log(self, callback: Optional[Callable[[str], None]], message: str):
        """
        输出日志
        
        Args:
            callback: 日志回调函数
            message: 日志消息
        """
        if callback:
            callback(message)
        else:
            print(message)
    
    def _validate_config(self, log_callback: Optional[Callable[[str], None]]) -> bool:
        """
        验证配置
        
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
        
        Args:
            log_callback: 日志回调函数
            
        Returns:
            bool: 是否成功加载
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
        
        Args:
            progress_callback: 进度回调函数
            log_callback: 日志回调函数
            
        Returns:
            bool: 是否成功解析
        """
        self._log(log_callback, "正在解析ASC文件...")
        self._log(log_callback, "进度: 0%")
        
        def internal_progress_callback(progress: float, line_count: int):
            if progress_callback:
                progress_callback(progress, line_count)
            if log_callback and progress % 10 < 1:
                self._log(log_callback, f"进度: {progress:.1f}% (已处理 {line_count:,} 行)")
        
        self.asc_parser = ASCParser(
            sample_interval=self.config.sample_interval,
            debug=self.config.debug
        )
        
        if not self.asc_parser.parse(
            self.config.asc_file,
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
        
        Args:
            log_callback: 日志回调函数
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
        """
        original_count, sampled_count, signal_count = self.asc_parser.get_statistics()
        return {
            'original_count': original_count,
            'sampled_count': sampled_count,
            'signal_count': signal_count
        }
    
    def _write_csv(self, log_callback: Optional[Callable[[str], None]]) -> List[str]:
        """
        写入CSV文件
        
        Args:
            log_callback: 日志回调函数
            
        Returns:
            List[str]: 创建的文件列表
        """
        self._log(log_callback, "正在创建CSV文件...")
        
        self.csv_writer = CSVWriter(
            output_dir=self.config.output_dir,
            encoding=self.config.csv_encoding,
            group_size=self.config.group_size
        )
        
        created_files = self.csv_writer.write_all(
            sorted_groups=self.data_processor.sorted_groups,
            classified_signals=self.data_processor.classified_signals,
            sorted_timestamps=self.data_processor.get_sorted_timestamps(),
            aggregated_data=self.data_processor.aggregated_data,
            signal_info=self.dbc_loader.signal_info,
            statistics=self._get_statistics()
        )
        
        return created_files
    
    def _cleanup(self):
        """清理资源"""
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
            List[str]: 分组列表
        """
        if self.data_processor:
            return self.data_processor.sorted_groups
        return []
