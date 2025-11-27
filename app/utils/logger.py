"""
日志配置模块
使用picologging提供高性能日志记录
"""

import picologging as logging
import os
from datetime import datetime

# 创建logs目录（如果不存在）
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# 配置日志格式
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 创建文件处理器
log_file = os.path.join(log_dir, f'pypdf_{datetime.now().strftime("%Y%m%d")}.log')
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setFormatter(formatter)

# 创建控制台处理器
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

# 配置根日志记录器
logger = logging.getLogger('PyPDF')
logger.setLevel(logging.DEBUG)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

def get_logger(name):
    """
    获取指定名称的日志记录器
    
    Args:
        name (str): 日志记录器名称
        
    Returns:
        logging.Logger: 配置好的日志记录器
    """
    return logging.getLogger(f'PyPDF.{name}')