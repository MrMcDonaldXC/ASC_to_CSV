# asc_to_csv/core/csv_loader.py
"""
CSV数据加载器模块
负责加载和解析CSV文件，提供数据访问接口
"""

import csv
from typing import Dict, List, Optional


MULTI_SELECT_COLUMNS = [
    'MaxCellTemp', 'MinCellTemp', 'PackSOC', 'HvBusVlt', 
    'BranchCrnt', 'PackFltLvl', 'MaxCellVlt', 'MinCellVlt',
    'PackFltCode', 'PackTotCrnt'
]


class CSVDataLoader:
    """
    CSV数据加载器
    
    负责加载CSV文件并解析数据，提供数据访问接口
    
    Attributes:
        data: 列名到数据列表的映射字典
        columns: 列名列表
        row_count: 数据行数
    """
    
    def __init__(self):
        """初始化数据加载器"""
        self.data: Dict[str, List] = {}
        self.columns: List[str] = []
        self.row_count: int = 0
    
    def load(self, file_path: str, encoding: str = 'utf-8-sig') -> bool:
        """
        加载CSV文件
        
        Args:
            file_path: CSV文件路径
            encoding: 文件编码，默认为utf-8-sig
            
        Returns:
            bool: 是否成功加载
        """
        self.data = {}
        self.columns = []
        self.row_count = 0
        
        try:
            with open(file_path, 'r', newline='', encoding=encoding) as f:
                reader = csv.reader(f)
                self.columns = next(reader)
                
                for col in self.columns:
                    self.data[col] = []
                
                for row in reader:
                    if len(row) != len(self.columns):
                        continue
                    
                    for i, value in enumerate(row):
                        col_name = self.columns[i]
                        try:
                            if value == '' or value.strip() == '':
                                self.data[col_name].append(None)
                            else:
                                self.data[col_name].append(float(value))
                        except ValueError:
                            self.data[col_name].append(value)
                    
                    self.row_count += 1
            
            return True
            
        except FileNotFoundError:
            return False
        except UnicodeDecodeError:
            try:
                with open(file_path, 'r', newline='', encoding='gbk') as f:
                    reader = csv.reader(f)
                    self.columns = next(reader)
                    
                    for col in self.columns:
                        self.data[col] = []
                    
                    for row in reader:
                        if len(row) != len(self.columns):
                            continue
                        
                        for i, value in enumerate(row):
                            col_name = self.columns[i]
                            try:
                                if value == '' or value.strip() == '':
                                    self.data[col_name].append(None)
                                else:
                                    self.data[col_name].append(float(value))
                            except ValueError:
                                self.data[col_name].append(value)
                        
                        self.row_count += 1
                
                return True
                
            except Exception:
                return False
        except Exception:
            return False
    
    def get_numeric_columns(self) -> List[str]:
        """
        获取数值类型的列名列表
        
        Returns:
            List[str]: 数值列名列表
        """
        numeric_cols = []
        for col in self.columns:
            if col == 'Time':
                continue
            values = [v for v in self.data[col] if v is not None]
            if values and all(isinstance(v, (int, float)) for v in values):
                numeric_cols.append(col)
        return numeric_cols
    
    def get_multi_select_columns(self) -> List[str]:
        """
        获取多列显示时可选择的列
        
        Returns:
            List[str]: 可用于多列对比的列名列表
        """
        numeric_cols = self.get_numeric_columns()
        result = []
        for target in MULTI_SELECT_COLUMNS:
            for col in numeric_cols:
                if target in col:
                    result.append(col)
                    break
        return result
    
    def get_time_column(self) -> Optional[str]:
        """
        获取时间列名
        
        Returns:
            Optional[str]: 时间列名，如果没有则返回None
        """
        for col in self.columns:
            col_lower = col.lower()
            if col_lower == 'time' or col_lower == 'times' or col_lower == 'time[s]':
                return col
        return None
    
    def clear(self):
        """清空加载的数据"""
        self.data.clear()
        self.columns.clear()
        self.row_count = 0
