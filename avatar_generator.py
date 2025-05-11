"""
头像生成工具模块
提供自动生成动漫风格头像的功能
"""

import os
import random
import string
from dicebear import DAvatar, DStyle, DOptions, DFormat
from flask import current_app
from werkzeug.utils import secure_filename

# 可用的动漫风格头像样式
ANIME_STYLES = [
    DStyle.pixel_art,       # 像素风格
    DStyle.avataaars,       # 卡通风格
    DStyle.big_smile,       # 大笑脸风格
    DStyle.bottts,          # 机器人风格
    DStyle.lorelei,         # 可爱风格
    DStyle.micah,           # 简约风格
    DStyle.notionists,      # 概念风格
    DStyle.open_peeps,      # 开放风格
    DStyle.personas         # 人物风格
]

def generate_random_avatar(username, save_path=None):
    """
    为用户生成随机风格的动漫头像
    
    参数:
        username: 用户名，用作种子
        save_path: 保存路径，如果为None则返回文件名和二进制数据
        
    返回:
        如果save_path为None，返回(filename, binary_data)
        如果save_path不为None，返回保存的文件路径
    """
    # 随机选择一个动漫风格
    style = random.choice(ANIME_STYLES)
    
    # 创建基本选项
    options = DOptions(
        backgroundColor="ffffff",  # 白色背景
        radius=50                  # 圆形头像
    )
    
    # 创建头像
    avatar = DAvatar(
        style=style,
        seed=username,  # 使用用户名作为种子，这样同一用户名总是生成相同的头像
        options=options
    )
    
    # 生成随机文件名
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    filename = f"{secure_filename(username)}_{random_suffix}.png"
    
    if save_path:
        # 确保目录存在
        os.makedirs(save_path, exist_ok=True)
        
        # 保存头像
        file_path = os.path.join(save_path, filename)
        avatar.save(
            location=save_path,
            file_name=os.path.splitext(filename)[0],
            file_format=DFormat.png,
            overwrite=True
        )
        return filename
    else:
        # 获取二进制数据
        binary_data = avatar.get_bytes(file_format=DFormat.png)
        return filename, binary_data

def generate_avatar_collection(count=10, save_path=None):
    """
    生成一组随机头像
    
    参数:
        count: 要生成的头像数量
        save_path: 保存路径
        
    返回:
        生成的头像文件名列表
    """
    filenames = []
    
    for i in range(count):
        # 使用随机字符串作为种子
        seed = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        filename = generate_random_avatar(f"avatar_{i}_{seed}", save_path)
        filenames.append(filename)
    
    return filenames

def get_avatar_path(filename):
    """
    获取头像的完整路径
    
    参数:
        filename: 头像文件名
        
    返回:
        头像的完整路径
    """
    return os.path.join(current_app.static_folder, 'avatars', filename)
