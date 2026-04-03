# asc_to_csv/main_enhanced.py
"""
增强版程序入口点
使用动态组名称提取，为每个唯一组创建独立CSV文件
"""

import argparse
from config import Config, get_default_config
from services.conversion_service import ConversionService as EnhancedConversionService, ConversionResult as EnhancedConversionResult
from core.group_extractor import ExtractionStrategy


class EnhancedASCToCSVConverter:
    """
    增强版ASC到CSV转换器
    
    使用动态组名称提取，为每个唯一组创建独立CSV文件
    """
    
    STRATEGY_MAP = {
        'auto': ExtractionStrategy.AUTO_DISCOVER,
        'message': ExtractionStrategy.MESSAGE_PREFIX,
        'signal': ExtractionStrategy.SIGNAL_PREFIX,
        'batp': ExtractionStrategy.BATP_PATTERN,
        'custom': ExtractionStrategy.CUSTOM_PATTERN,
    }
    
    def __init__(self, config: Config = None, strategy: str = 'auto'):
        """
        初始化转换器
        
        Args:
            config: 配置对象
            strategy: 分组策略名称
        """
        self.config = config or get_default_config()
        self.strategy = self.STRATEGY_MAP.get(strategy, ExtractionStrategy.AUTO_DISCOVER)
        self.service = EnhancedConversionService(self.config, self.strategy)
    
    def run(self, overwrite: bool = False) -> bool:
        """
        运行转换流程
        
        Args:
            overwrite: 是否覆盖已存在的文件
            
        Returns:
            bool: 是否成功完成转换
        """
        self._print_config()
        
        result = self.service.convert(
            log_callback=self._log,
            overwrite=overwrite
        )
        
        if result.success:
            self._print_summary(result)
            return True
        else:
            print(f"\n❌ 转换失败！{result.error_message}")
            return False
    
    def _log(self, message: str):
        """日志输出"""
        print(message)
    
    def _print_config(self) -> None:
        """打印配置信息"""
        print("=" * 60)
        print("增强型分组模式配置:")
        print(f"  分组策略: {self.strategy.value}")
        print(f"  采样间隔: {self.config.sample_interval}秒")
        print(f"  输出格式: 每个组独立CSV文件")
        print(f"  文件编码: {self.config.csv_encoding}")
        print("=" * 60)
    
    def _print_summary(self, result: EnhancedConversionResult) -> None:
        """打印转换摘要"""
        print("\n" + "=" * 60)
        print("转换摘要:")
        print(f"  输出目录: {result.output_dir}")
        print(f"  发现分组: {len(result.discovered_groups)}个")
        print(f"  创建文件: {len(result.created_files)}个")
        
        if result.skipped_files:
            print(f"  跳过文件: {len(result.skipped_files)}个（已存在）")
        
        print("\n分组详情:")
        for group_name in result.discovered_groups:
            signal_count = result.group_statistics.get(group_name, 0)
            print(f"  {group_name}: {signal_count}个信号")
        
        print("=" * 60)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='ASC到CSV转换工具（增强型分组模式）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
分组策略说明:
  auto    - 自动发现模式（默认）: 综合使用多种策略
  message - 消息前缀模式: 从消息名称前缀提取
  signal  - 信号前缀模式: 从信号名称前缀提取
  batp    - BATP模式: 匹配BATP系列模式

示例:
  python main_enhanced.py
  python main_enhanced.py --strategy auto
  python main_enhanced.py --overwrite
        """
    )
    
    parser.add_argument(
        '--strategy', '-s',
        choices=['auto', 'message', 'signal', 'batp', 'custom'],
        default='auto',
        help='分组策略 (默认: auto)'
    )
    
    parser.add_argument(
        '--overwrite', '-o',
        action='store_true',
        help='覆盖已存在的文件'
    )
    
    args = parser.parse_args()
    
    config = get_default_config()
    
    converter = EnhancedASCToCSVConverter(
        config=config,
        strategy=args.strategy
    )
    
    success = converter.run(overwrite=args.overwrite)
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
