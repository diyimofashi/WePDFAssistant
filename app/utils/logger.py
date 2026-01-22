"""
日志配置模块
使用picologging提供高性能日志记录
"""

import picologging as logging
import os
from datetime import datetime

from app.utils.app_path import get_app_root

# 创建logs目录（如果不存在）
log_dir = os.path.join(get_app_root(), 'logs')
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# 配置日志格式
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 默认日志级别（可通过配置文件修改）
DEFAULT_LOG_LEVEL = logging.INFO

# 创建文件处理器
log_file = os.path.join(log_dir, f'pypdf_{datetime.now().strftime("%Y%m%d")}.log')
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setFormatter(formatter)
file_handler.setLevel(DEFAULT_LOG_LEVEL)

# 创建控制台处理器
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
console_handler.setLevel(DEFAULT_LOG_LEVEL)

# 配置根日志记录器
logger = logging.getLogger('PyPDF')
logger.setLevel(DEFAULT_LOG_LEVEL)
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

def set_log_level(level):
    """
    设置日志级别
    
    Args:
        level: 日志级别字符串 ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL') 或整数值
    """
    level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    
    if isinstance(level, str):
        log_level = level_map.get(level.upper(), DEFAULT_LOG_LEVEL)
    else:
        log_level = level
    
    logger.setLevel(log_level)
    file_handler.setLevel(log_level)
    console_handler.setLevel(log_level)
    
def set_log_level_from_config():
    """
    从配置文件读取并设置日志级别
    """
    try:
        config_file = os.path.join(os.path.join(get_app_root(), 'config'), 'app_settings.json')
        if os.path.exists(config_file):
            import json
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                log_level = config.get('log_level', 'INFO')
                set_log_level(log_level)
    except Exception:
        pass

# 自动从配置文件加载日志级别（在所有函数定义之后）
set_log_level_from_config()