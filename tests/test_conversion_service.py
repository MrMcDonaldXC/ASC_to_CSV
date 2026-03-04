# tests/test_conversion_service.py
"""
转换服务单元测试
"""

import unittest
import os
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from conversion_service import ConversionService, ConversionResult


class TestConversionResult(unittest.TestCase):
    """ConversionResult 数据类测试"""
    
    def test_default_values(self):
        """测试默认值"""
        result = ConversionResult()
        self.assertFalse(result.success)
        self.assertEqual(result.original_count, 0)
        self.assertEqual(result.sampled_count, 0)
        self.assertEqual(result.signal_count, 0)
        self.assertEqual(result.created_files, [])
        self.assertEqual(result.output_dir, "")
        self.assertEqual(result.error_message, "")
        self.assertEqual(result.group_statistics, {})
    
    def test_custom_values(self):
        """测试自定义值"""
        result = ConversionResult(
            success=True,
            original_count=1000,
            sampled_count=100,
            signal_count=50,
            created_files=["file1.csv", "file2.csv"],
            output_dir="/tmp/output",
            error_message="",
            group_statistics={"BatP3": 10, "BatP4": 15}
        )
        self.assertTrue(result.success)
        self.assertEqual(result.original_count, 1000)
        self.assertEqual(result.sampled_count, 100)
        self.assertEqual(result.signal_count, 50)
        self.assertEqual(len(result.created_files), 2)
        self.assertEqual(result.group_statistics["BatP3"], 10)


class TestConversionService(unittest.TestCase):
    """ConversionService 测试"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.config = Config(
            asc_file="",
            dbc_files=[],
            output_dir=self.temp_dir,
            sample_interval=0.1,
            group_size=5,
            csv_encoding="utf-8-sig",
            debug=False
        )
    
    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_init(self):
        """测试初始化"""
        service = ConversionService(self.config)
        self.assertEqual(service.config, self.config)
        self.assertIsNone(service.dbc_loader)
        self.assertIsNone(service.asc_parser)
        self.assertIsNone(service.data_processor)
        self.assertIsNone(service.csv_writer)
    
    def test_convert_with_invalid_config(self):
        """测试无效配置的转换"""
        service = ConversionService(self.config)
        result = service.convert()
        self.assertFalse(result.success)
        self.assertIn("配置验证失败", result.error_message)
    
    @patch('conversion_service.DBCLoader')
    @patch('conversion_service.ASCParser')
    @patch('conversion_service.DataProcessor')
    @patch('conversion_service.CSVWriter')
    def test_convert_success_flow(self, mock_csv_writer, mock_data_processor, 
                                   mock_asc_parser, mock_dbc_loader):
        """测试成功转换流程"""
        self.config.asc_file = "test.asc"
        self.config.dbc_files = ["test.dbc"]
        
        with patch.object(self.config, 'validate', return_value=True):
            with patch.object(self.config, 'create_output_dir', return_value=True):
                mock_dbc_instance = Mock()
                mock_dbc_instance.load.return_value = True
                mock_dbc_instance.get_message_count.return_value = 10
                mock_dbc_instance.get_signal_count.return_value = 50
                mock_dbc_instance.message_map = {}
                mock_dbc_instance.signal_info = {}
                mock_dbc_loader.return_value = mock_dbc_instance
                
                mock_asc_instance = Mock()
                mock_asc_instance.parse.return_value = True
                mock_asc_instance.get_statistics.return_value = (1000, 100, 50)
                mock_asc_instance.sampled_data = {}
                mock_asc_instance.found_signals = set()
                mock_asc_parser.return_value = mock_asc_instance
                
                mock_dp_instance = Mock()
                mock_dp_instance.get_group_statistics.return_value = {"BatP3": 10}
                mock_dp_instance.sorted_groups = ["BatP3"]
                mock_dp_instance.aggregated_data = {}
                mock_dp_instance.classified_signals = {}
                mock_dp_instance.get_sorted_timestamps.return_value = []
                mock_data_processor.return_value = mock_dp_instance
                
                mock_csv_instance = Mock()
                mock_csv_instance.write_all.return_value = ["file1.csv"]
                mock_csv_writer.return_value = mock_csv_instance
                
                service = ConversionService(self.config)
                result = service.convert()
                
                self.assertTrue(result.success)
                self.assertEqual(result.original_count, 1000)
                self.assertEqual(result.sampled_count, 100)
                self.assertEqual(result.signal_count, 50)


class TestConversionServiceLogCallback(unittest.TestCase):
    """ConversionService 日志回调测试"""
    
    def test_log_callback(self):
        """测试日志回调"""
        config = Config()
        service = ConversionService(config)
        
        messages = []
        def log_callback(msg):
            messages.append(msg)
        
        service._log(log_callback, "测试消息")
        self.assertIn("测试消息", messages)
    
    def test_log_callback_none(self):
        """测试无日志回调"""
        config = Config()
        service = ConversionService(config)
        
        with patch('builtins.print') as mock_print:
            service._log(None, "测试消息")
            mock_print.assert_called_with("测试消息")


if __name__ == '__main__':
    unittest.main()
