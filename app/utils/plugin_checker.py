"""
插件状态全局检查模块
提供统一的接口来检查各功能模块是否可用
"""

import os
from app.utils.logger import get_logger

logger = get_logger('plugin_checker')

# 全局插件状态缓存
_plugin_status_cache = {}


def check_ocr_plugin():
    """检查OCR插件是否可用"""
    if 'has_ocr_plugin' in _plugin_status_cache:
        return _plugin_status_cache['has_ocr_plugin']

    try:
        # 检查OCR配置文件是否存在
        from app.config.settings import AppSettings
        ocr_enabled = AppSettings.get_ocr_enabled()

        # 尝试导入OCR相关模块
        try:
            from app.core.main.ocr_manager_mixin import OCRManagerMixin
            has_ocr = True
        except ImportError:
            has_ocr = False

        result = has_ocr and ocr_enabled
        _plugin_status_cache['has_ocr_plugin'] = result
        logger.debug(f"OCR插件检查结果: {result}")
        return result
    except Exception as e:
        logger.error(f"检查OCR插件时出错: {e}")
        _plugin_status_cache['has_ocr_plugin'] = False
        return False


def check_storage_plugin():
    """检查存储插件是否可用"""
    if 'has_storage_plugin' in _plugin_status_cache:
        return _plugin_status_cache['has_storage_plugin']

    try:
        # 检查存储插件目录是否存在
        plugins_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                   'plugins-storage')

        if not os.path.exists(plugins_dir):
            _plugin_status_cache['has_storage_plugin'] = False
            return False

        # 检查是否有至少一个存储插件
        plugin_dirs = [d for d in os.listdir(plugins_dir)
                     if os.path.isdir(os.path.join(plugins_dir, d))]

        result = len(plugin_dirs) > 0
        _plugin_status_cache['has_storage_plugin'] = result
        logger.debug(f"存储插件检查结果: {result}, 插件数: {len(plugin_dirs)}")
        return result
    except Exception as e:
        logger.error(f"检查存储插件时出错: {e}")
        _plugin_status_cache['has_storage_plugin'] = False
        return False


def check_barcode_split_plugin():
    """检查barcode拆分插件是否可用"""
    if 'has_barcode_split_plugin' in _plugin_status_cache:
        return _plugin_status_cache['has_barcode_split_plugin']

    try:
        # 检查barcode拆分处理器是否存在
        from app.core.barcode.barcode_split_processor import BarcodeSplitProcessor
        result = True
    except ImportError:
        result = False
    except Exception as e:
        logger.error(f"检查barcode拆分插件时出错: {e}")
        result = False

    _plugin_status_cache['has_barcode_split_plugin'] = result
    logger.debug(f"Barcode拆分插件检查结果: {result}")
    return result


def clear_plugin_cache():
    """清除插件状态缓存"""
    global _plugin_status_cache
    _plugin_status_cache = {}
    logger.debug("插件状态缓存已清除")


def get_all_plugin_status():
    """获取所有插件状态"""
    return {
        'has_ocr_plugin': check_ocr_plugin(),
        'has_storage_plugin': check_storage_plugin(),
        'has_barcode_split_plugin': check_barcode_split_plugin()
    }
