# tests/test_enhanced_csv_writer.py
"""
增强型CSV写入器单元测试
验证每个唯一组创建独立CSV文件的功能
"""

import unittest
import os
import sys
import tempfile
import shutil
import csv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from enhanced_csv_writer import EnhancedCSVWriter


class TestEnhancedCSVWriterBasic(unittest.TestCase):
    """基础功能测试"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.writer = EnhancedCSVWriter(
            output_dir=self.temp_dir,
            encoding="utf-8-sig",
            fill_interval=0.5
        )
    
    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_sanitize_filename(self):
        """测试文件名清理"""
        test_cases = [
            ("BatP3", "BatP3"),
            ("BATPQ", "BATPQ"),
            ("Group<Name>", "Group_Name_"),
            ("Test/File", "Test_File"),
            ("", "Unknown"),
        ]
        
        for input_name, expected in test_cases:
            result = self.writer._sanitize_filename(input_name)
            self.assertEqual(result, expected)
    
    def test_check_file_exists(self):
        """测试文件存在检查"""
        # 创建测试文件
        test_file = os.path.join(self.temp_dir, "test.csv")
        with open(test_file, 'w') as f:
            f.write("test")
        
        self.assertTrue(self.writer._check_file_exists("test.csv"))
        self.assertFalse(self.writer._check_file_exists("nonexistent.csv"))


class TestEnhancedCSVWriterGroupFiles(unittest.TestCase):
    """分组文件创建测试"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.writer = EnhancedCSVWriter(
            output_dir=self.temp_dir,
            encoding="utf-8-sig",
            fill_interval=0.5
        )
        
        self.classified_signals = {
            "BatP3": ["test.dbc::BatP3_Msg::sig1", "test.dbc::BatP3_Msg::sig2"],
            "BatP4": ["test.dbc::BatP4_Msg::sig1"],
            "BATPQ": ["test.dbc::BATPQ_Msg::sig1"],
        }
        
        self.sorted_timestamps = [0.0, 0.1, 0.2, 0.3, 0.4]
        
        self.aggregated_data = {
            0.0: {
                "test.dbc::BatP3_Msg::sig1": 1.0,
                "test.dbc::BatP3_Msg::sig2": 2.0,
                "test.dbc::BatP4_Msg::sig1": 3.0,
                "test.dbc::BATPQ_Msg::sig1": 4.0,
            },
            0.1: {
                "test.dbc::BatP3_Msg::sig1": 1.1,
                "test.dbc::BatP3_Msg::sig2": 2.1,
                "test.dbc::BatP4_Msg::sig1": 3.1,
                "test.dbc::BATPQ_Msg::sig1": 4.1,
            },
        }
        
        self.signal_info = {
            "test.dbc::BatP3_Msg::sig1": {"unit": "V", "message": "BatP3_Msg", "dbc": "test.dbc"},
            "test.dbc::BatP3_Msg::sig2": {"unit": "A", "message": "BatP3_Msg", "dbc": "test.dbc"},
            "test.dbc::BatP4_Msg::sig1": {"unit": "V", "message": "BatP4_Msg", "dbc": "test.dbc"},
            "test.dbc::BATPQ_Msg::sig1": {"unit": "V", "message": "BATPQ_Msg", "dbc": "test.dbc"},
        }
    
    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_write_all_groups(self):
        """测试写入所有分组文件"""
        result = self.writer.write_all_groups(
            classified_signals=self.classified_signals,
            sorted_timestamps=self.sorted_timestamps,
            aggregated_data=self.aggregated_data,
            signal_info=self.signal_info
        )
        
        # 验证返回结果
        self.assertEqual(result['total_groups'], 3)
        self.assertEqual(result['created_count'], 3)
        
        # 验证文件是否创建
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, "BatP3.csv")))
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, "BatP4.csv")))
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, "BATPQ.csv")))
    
    def test_write_group_file_content(self):
        """测试分组文件内容"""
        self.writer.write_all_groups(
            classified_signals=self.classified_signals,
            sorted_timestamps=self.sorted_timestamps,
            aggregated_data=self.aggregated_data,
            signal_info=self.signal_info
        )
        
        # 读取BatP3.csv文件
        with open(os.path.join(self.temp_dir, "BatP3.csv"), 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            header = next(reader)
            
            # 验证表头
            self.assertIn("Time[s]", header)
            self.assertIn("sig1[V]", header)
            self.assertIn("sig2[A]", header)
    
    def test_skip_existing_files(self):
        """测试跳过已存在文件"""
        # 第一次写入
        result1 = self.writer.write_all_groups(
            classified_signals=self.classified_signals,
            sorted_timestamps=self.sorted_timestamps,
            aggregated_data=self.aggregated_data,
            signal_info=self.signal_info
        )
        
        self.assertEqual(result1['created_count'], 3)
        self.assertEqual(result1['skipped_count'], 0)
        
        # 第二次写入（应跳过已存在文件）
        writer2 = EnhancedCSVWriter(
            output_dir=self.temp_dir,
            encoding="utf-8-sig",
            fill_interval=0.5,
            overwrite=False
        )
        
        result2 = writer2.write_all_groups(
            classified_signals=self.classified_signals,
            sorted_timestamps=self.sorted_timestamps,
            aggregated_data=self.aggregated_data,
            signal_info=self.signal_info
        )
        
        self.assertEqual(result2['created_count'], 0)
        self.assertEqual(result2['skipped_count'], 3)
    
    def test_overwrite_existing_files(self):
        """测试覆盖已存在文件"""
        # 第一次写入
        self.writer.write_all_groups(
            classified_signals=self.classified_signals,
            sorted_timestamps=self.sorted_timestamps,
            aggregated_data=self.aggregated_data,
            signal_info=self.signal_info
        )
        
        # 第二次写入（覆盖模式）
        writer2 = EnhancedCSVWriter(
            output_dir=self.temp_dir,
            encoding="utf-8-sig",
            fill_interval=0.5,
            overwrite=True
        )
        
        result2 = writer2.write_all_groups(
            classified_signals=self.classified_signals,
            sorted_timestamps=self.sorted_timestamps,
            aggregated_data=self.aggregated_data,
            signal_info=self.signal_info
        )
        
        self.assertEqual(result2['created_count'], 3)
        self.assertEqual(result2['skipped_count'], 0)


class TestEnhancedCSVWriterSummary(unittest.TestCase):
    """汇总文件测试"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.writer = EnhancedCSVWriter(
            output_dir=self.temp_dir,
            encoding="utf-8-sig"
        )
    
    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_write_summary_file(self):
        """测试写入汇总文件"""
        classified_signals = {
            "BatP3": ["sig1", "sig2"],
            "BatP4": ["sig3"],
        }
        
        result_stats = {
            'created_count': 2,
            'skipped_count': 0
        }
        
        summary_path = self.writer.write_summary_file(
            classified_signals=classified_signals,
            sorted_timestamps=[0.0, 0.1, 0.2],
            result_stats=result_stats
        )
        
        self.assertTrue(os.path.exists(summary_path))
        
        # 验证文件内容
        with open(summary_path, 'r', encoding='utf-8-sig') as f:
            content = f.read()
            self.assertIn("数据转换汇总报告", content)
            self.assertIn("动态组名称提取", content)


class TestEnhancedCSVWriterSpecialChars(unittest.TestCase):
    """特殊字符处理测试"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.writer = EnhancedCSVWriter(
            output_dir=self.temp_dir,
            encoding="utf-8-sig"
        )
    
    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_special_chars_in_group_name(self):
        """测试组名称中的特殊字符"""
        classified_signals = {
            "Group<Test>": ["sig1"],
            "Test/File": ["sig2"],
            "Normal": ["sig3"],
        }
        
        aggregated_data = {
            0.0: {"sig1": 1.0, "sig2": 2.0, "sig3": 3.0}
        }
        
        signal_info = {
            "sig1": {"unit": "", "message": "Msg1", "dbc": "test.dbc"},
            "sig2": {"unit": "", "message": "Msg2", "dbc": "test.dbc"},
            "sig3": {"unit": "", "message": "Msg3", "dbc": "test.dbc"},
        }
        
        result = self.writer.write_all_groups(
            classified_signals=classified_signals,
            sorted_timestamps=[0.0],
            aggregated_data=aggregated_data,
            signal_info=signal_info
        )
        
        # 验证文件创建（特殊字符应被替换）
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, "Group_Test_.csv")))
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, "Test_File.csv")))
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, "Normal.csv")))


if __name__ == '__main__':
    import sys
    unittest.main()
