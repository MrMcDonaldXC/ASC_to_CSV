# tests/test_utils.py
"""
工具函数单元测试
"""

import unittest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import extract_batp_group, safe_value, sort_group_key


class TestExtractBatpGroup(unittest.TestCase):
    """extract_batp_group 函数测试"""
    
    def test_batp_with_number(self):
        """测试 BatP 数字模式"""
        self.assertEqual(
            extract_batp_group("800V_BMS_PCAN_V2.5.3.dbc::BatP3_BMS_CellVoltMaxMin::P3_AvgCellVlt"),
            "BatP3"
        )
        self.assertEqual(
            extract_batp_group("xxx::BatP4_xxx::signal"),
            "BatP4"
        )
        self.assertEqual(
            extract_batp_group("BatP10_test"),
            "BatP10"
        )
    
    def test_batpq_pattern(self):
        """测试 BATPQ 模式"""
        self.assertEqual(
            extract_batp_group("xxx::BATPQ_xxx::signal"),
            "BATPQ"
        )
        self.assertEqual(
            extract_batp_group("batpq_test"),
            "BATPQ"
        )
    
    def test_batps_pattern(self):
        """测试 BATPS 模式"""
        self.assertEqual(
            extract_batp_group("xxx::BATPS_xxx::signal"),
            "BATPS"
        )
        self.assertEqual(
            extract_batp_group("batps_test"),
            "BATPS"
        )
    
    def test_other_pattern(self):
        """测试其他模式"""
        self.assertEqual(
            extract_batp_group("xxx::Unknown_xxx::signal"),
            "Other"
        )
        self.assertEqual(
            extract_batp_group("random_signal_name"),
            "Other"
        )


class TestSafeValue(unittest.TestCase):
    """safe_value 函数测试"""
    
    def test_none_value(self):
        """测试 None 值"""
        self.assertEqual(safe_value(None), "")
    
    def test_integer_value(self):
        """测试整数值"""
        self.assertEqual(safe_value(123), 123)
        self.assertEqual(safe_value(0), 0)
        self.assertEqual(safe_value(-456), -456)
    
    def test_float_value(self):
        """测试浮点数值"""
        self.assertEqual(safe_value(123.456), 123.456)
        self.assertEqual(safe_value(0.0), 0)
        self.assertEqual(safe_value(100.0), 100)
    
    def test_float_precision(self):
        """测试浮点数精度处理"""
        result = safe_value(15.600000000000001)
        self.assertEqual(result, 15.6)
    
    def test_string_value(self):
        """测试字符串值"""
        self.assertEqual(safe_value("Standby"), "Standby")
        self.assertEqual(safe_value(""), "")


class TestSortGroupKey(unittest.TestCase):
    """sort_group_key 函数测试"""
    
    def test_batp_order(self):
        """测试 BatP 数字组排序"""
        self.assertEqual(sort_group_key("BatP3"), (0, 3))
        self.assertEqual(sort_group_key("BatP4"), (0, 4))
        self.assertEqual(sort_group_key("BatP10"), (0, 10))
    
    def test_batpq_order(self):
        """测试 BATPQ 排序"""
        self.assertEqual(sort_group_key("BATPQ"), (1, 0))
    
    def test_batps_order(self):
        """测试 BATPS 排序"""
        self.assertEqual(sort_group_key("BATPS"), (2, 0))
    
    def test_other_order(self):
        """测试 Other 排序"""
        self.assertEqual(sort_group_key("Other"), (3, "Other"))
        self.assertEqual(sort_group_key("Unknown"), (3, "Unknown"))
    
    def test_sorting_order(self):
        """测试整体排序顺序"""
        groups = ["Other", "BatP4", "BATPQ", "BatP3", "BATPS"]
        sorted_groups = sorted(groups, key=sort_group_key)
        self.assertEqual(sorted_groups, ["BatP3", "BatP4", "BATPQ", "BATPS", "Other"])


if __name__ == '__main__':
    unittest.main()
