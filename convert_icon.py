# -*- coding: utf-8 -*-
"""
图标转换脚本
将PNG格式图片转换为ICO格式，用于exe文件图标
"""

from PIL import Image
import os

def convert_png_to_ico(png_path: str, ico_path: str, sizes: list = None):
    """
    将PNG图片转换为ICO格式
    
    Args:
        png_path: PNG文件路径
        ico_path: 输出ICO文件路径
        sizes: ICO包含的尺寸列表，默认为常见Windows图标尺寸
    """
    if sizes is None:
        sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    
    img = Image.open(png_path)
    
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    icon_images = []
    for size in sizes:
        resized = img.resize(size, Image.Resampling.LANCZOS)
        icon_images.append(resized)
    
    img.save(ico_path, format='ICO', sizes=sizes)
    print(f"成功转换: {png_path} -> {ico_path}")
    print(f"包含尺寸: {sizes}")

if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    png_path = os.path.join(script_dir, 'resource', 'icon.png')
    ico_path = os.path.join(script_dir, 'resource', 'icon.ico')
    
    if not os.path.exists(png_path):
        print(f"错误: 找不到PNG文件 - {png_path}")
        exit(1)
    
    convert_png_to_ico(png_path, ico_path)
    print(f"\nICO文件已生成: {ico_path}")
