# asc_to_csv/main.py
"""
程序入口点
协调各模块完成ASC到CSV的转换
"""

from config import Config, get_default_config
from conversion_service import ConversionService, ConversionResult


class ASCToCSVConverter:
    """
    ASC到CSV转换器
    
    协调各模块完成完整的转换流程
    """
    
    def __init__(self, config: Config = None):
        """
        初始化转换器
        
        Args:
            config: 配置对象，如果为None则使用默认配置
        """
        self.config = config or get_default_config()
        self.service = ConversionService(self.config)
    
    def run(self) -> bool:
        """
        运行转换流程
        
        Returns:
            bool: 是否成功完成转换
        """
        self._print_config()
        
        result = self.service.convert(log_callback=self._log)
        
        if result.success:
            self._print_summary(result)
            return True
        else:
            print(f"\n❌ 转换失败！{result.error_message}")
            return False
    
    def _log(self, message: str):
        """
        日志输出
        
        Args:
            message: 日志消息
        """
        print(message)
    
    def _print_config(self) -> None:
        """打印配置信息"""
        print("开始转换...")
        print(f"分组规则: 按BatP+数字模式分组")
        print(f"采样间隔: {self.config.sample_interval}秒")
        print(f"分组大小: {self.config.group_size}个数据/组")
        print(f"输出格式: CSV文件")
        print(f"文件编码: {self.config.csv_encoding}")
    
    def _print_summary(self, result: ConversionResult) -> None:
        """
        打印转换摘要
        
        Args:
            result: 转换结果
        """
        print(f"\n✅ 转换完成！")
        print(f"输出目录: {result.output_dir}")
        print(f"生成文件数: {len(result.created_files)}")
        
        print(f"\n生成的文件：")
        print(f"  1. Summary.csv - 汇总报告")
        print(f"  2. All_Signals.csv - 所有信号总览")
        for i, group_name in enumerate(self.service.get_sorted_groups(), 3):
            signal_count = result.group_statistics.get(group_name, 0)
            print(f"  {i}. {group_name}.csv - {signal_count}个信号")


def main():
    """主函数"""
    config = get_default_config()
    
    converter = ASCToCSVConverter(config)
    success = converter.run()
    
    if not success:
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
