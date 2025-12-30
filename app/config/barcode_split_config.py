"""条码拆分配置管理器模块"""

import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from app.utils.logger import get_logger

logger = get_logger('barcode_split_config')


@dataclass
class BarcodeFilterConfig:
    """条码过滤配置"""
    enabled_types: List[str] = None
    min_length: int = 1
    max_length: int = 1000
    include_keywords: List[str] = None
    exclude_keywords: List[str] = None
    include_regex: str = ""  # 包含正则表达式
    exclude_regex: str = ""  # 排除正则表达式
    
    def __post_init__(self):
        if self.enabled_types is None:
            self.enabled_types = ['QRCODE', 'CODE128', 'EAN13', 'CODE39', 'PDF417', 'CODE93', 'I25', 'UPCA', 'UPCE']
        if self.include_keywords is None:
            self.include_keywords = []
        if self.exclude_keywords is None:
            self.exclude_keywords = []


@dataclass
class BarcodeOutputConfig:
    """输出配置"""
    output_dir: str = ""
    use_barcode_filename: bool = True
    filename_template: str = "{barcode}_{index}"
    duplicate_handling: str = "merge"  # "merge" 或 "separate"
    multi_barcode_handling: str = "first"  # "first" 或 "duplicate_page"
    
    def get_filename(self, barcode_data: str, index: int) -> str:
        """
        根据配置生成文件名
        
        Args:
            barcode_data: 条码数据
            index: 索引（用于处理重复条码）
            
        Returns:
            生成的文件名（不含扩展名）
        """
        if self.use_barcode_filename and barcode_data:
            # 清理条码数据中的非法字符
            clean_barcode = self._clean_filename(barcode_data)
            # 格式化index为3位数字，前面补0
            formatted_index = f"{index + 1:03d}"  # 从1开始，格式化为001, 002等
            filename = self.filename_template.format(
                barcode=clean_barcode,
                index=formatted_index
            )
        else:
            # 格式化index为3位数字，前面补0
            formatted_index = f"{index + 1:03d}"  # 从1开始，格式化为001, 002等
            filename = f"split_document_{formatted_index}"
        
        return filename
    
    def _clean_filename(self, filename: str) -> str:
        """清理文件名中的非法字符"""
        # Windows文件名非法字符
        illegal_chars = '<>:"/\\|?*'
        for char in illegal_chars:
            filename = filename.replace(char, '_')
        
        # 去除前后空格和点
        filename = filename.strip('. ')
        
        # 限制长度
        if len(filename) > 50:
            filename = filename[:50]
        
        return filename


@dataclass
class BarcodeSplitConfig:
    """条码拆分完整配置"""
    filter_config: BarcodeFilterConfig = None
    output_config: BarcodeOutputConfig = None
    last_used: bool = False
    
    def __post_init__(self):
        if self.filter_config is None:
            self.filter_config = BarcodeFilterConfig()
        if self.output_config is None:
            self.output_config = BarcodeOutputConfig()



class BarcodeSplitConfigManager:
    """条码拆分配置管理器"""
    
    def __init__(self, config_dir: str = None):
        """
        初始化配置管理器
        
        Args:
            config_dir: 配置文件目录，默认为应用目录下的config
        """
        if config_dir is None:
            # 获取app目录下的config目录
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_dir = os.path.join(app_dir, 'config')
        
        self.config_dir = config_dir
        self.config_file = os.path.join(config_dir, 'barcode_split_config.json')
        
        # 确保配置目录存在
        os.makedirs(config_dir, exist_ok=True)
        
        # 默认配置
        self.default_config = BarcodeSplitConfig()
        
        logger.debug(f"配置管理器初始化，配置文件路径: {self.config_file}")
    
    def save_config(self, config: BarcodeSplitConfig, name: str = "default") -> bool:
        """
        保存配置
        
        Args:
            config: 配置对象
            name: 配置名称
            
        Returns:
            是否保存成功
        """
        try:
            # 读取现有配置
            configs = self._load_all_configs()
            
            # 转换为可序列化的字典
            config_dict = self._config_to_dict(config)
            config_dict['last_used'] = True  # 标记为最后使用
            
            # 更新其他配置的last_used状态
            for key in configs:
                if key != name:
                    configs[key]['last_used'] = False
            
            # 保存当前配置
            configs[name] = config_dict
            
            # 写入文件
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(configs, f, ensure_ascii=False, indent=2)
            
            logger.info(f"配置保存成功: {name} -> {self.config_file}")
            return True
            
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False
    
    def load_config(self, name: str = "default") -> BarcodeSplitConfig:
        """
        加载配置
        
        Args:
            name: 配置名称
            
        Returns:
            配置对象
        """
        try:
            configs = self._load_all_configs()
            
            if name in configs:
                config = self._dict_to_config(configs[name])
                logger.info(f"配置加载成功: {name}")
                return config
            else:
                logger.warning(f"配置不存在: {name}，使用默认配置")
                return self.default_config
                
        except Exception as e:
            logger.error(f"加载配置失败: {e}，使用默认配置")
            return self.default_config
    
    def load_last_used_config(self) -> BarcodeSplitConfig:
        """
        加载最后使用的配置
        
        Returns:
            最后使用的配置对象，如果没有则返回默认配置
        """
        try:
            configs = self._load_all_configs()
            
            # 查找标记为last_used的配置
            for name, config_dict in configs.items():
                if config_dict.get('last_used', False):
                    config = self._dict_to_config(config_dict)
                    logger.info(f"加载最后使用的配置: {name}")
                    return config
            
            # 如果没有找到，使用第一个配置
            if configs:
                first_name = list(configs.keys())[0]
                config = self._dict_to_config(configs[first_name])
                logger.info(f"没有找到最后使用的配置，使用第一个配置: {first_name}")
                return config
            
            logger.info("没有找到任何配置，使用默认配置")
            return self.default_config
            
        except Exception as e:
            logger.error(f"加载最后使用的配置失败: {e}，使用默认配置")
            return self.default_config
    
    def get_all_configs(self) -> Dict[str, BarcodeSplitConfig]:
        """
        获取所有配置
        
        Returns:
            配置字典 {名称: 配置对象}
        """
        try:
            configs = self._load_all_configs()
            result = {}
            
            for name, config_dict in configs.items():
                result[name] = self._dict_to_config(config_dict)
            
            return result
            
        except Exception as e:
            logger.error(f"获取所有配置失败: {e}")
            return {"default": self.default_config}
    
    def delete_config(self, name: str) -> bool:
        """
        删除配置
        
        Args:
            name: 配置名称
            
        Returns:
            是否删除成功
        """
        try:
            if name == "default":
                logger.warning("不能删除默认配置")
                return False
            
            configs = self._load_all_configs()
            
            if name in configs:
                del configs[name]
                
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(configs, f, ensure_ascii=False, indent=2)
                
                logger.info(f"配置删除成功: {name}")
                return True
            else:
                logger.warning(f"配置不存在: {name}")
                return False
                
        except Exception as e:
            logger.error(f"删除配置失败: {e}")
            return False
    
    def export_config(self, config: BarcodeSplitConfig, file_path: str) -> bool:
        """
        导出配置到文件
        
        Args:
            config: 配置对象
            file_path: 导出文件路径
            
        Returns:
            是否导出成功
        """
        try:
            config_dict = self._config_to_dict(config)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, ensure_ascii=False, indent=2)
            
            logger.info(f"配置导出成功: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出配置失败: {e}")
            return False
    
    def import_config(self, file_path: str) -> Optional[BarcodeSplitConfig]:
        """
        从文件导入配置
        
        Args:
            file_path: 导入文件路径
            
        Returns:
            导入的配置对象，失败返回None
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config_dict = json.load(f)
            
            config = self._dict_to_config(config_dict)
            logger.info(f"配置导入成功: {file_path}")
            return config
            
        except Exception as e:
            logger.error(f"导入配置失败: {e}")
            return None
    
    def _load_all_configs(self) -> Dict[str, Any]:
        """加载所有配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                logger.debug("配置文件不存在，返回空配置")
                return {}
                
        except json.JSONDecodeError as e:
            logger.error(f"配置文件JSON格式错误: {e}")
            return {}
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return {}
    
    def _config_to_dict(self, config: BarcodeSplitConfig) -> Dict[str, Any]:
        """将配置对象转换为字典"""
        return {
            'filter_config': asdict(config.filter_config),
            'output_config': asdict(config.output_config),
            'last_used': config.last_used
        }
    
    def _dict_to_config(self, config_dict: Dict[str, Any]) -> BarcodeSplitConfig:
        """将字典转换为配置对象"""
        # 处理过滤配置的类型转换
        filter_config_data = config_dict.get('filter_config', {})
        filter_config = convert_filter_config_types(filter_config_data)
        
        output_config = BarcodeOutputConfig(**config_dict.get('output_config', {}))
        
        return BarcodeSplitConfig(
            filter_config=filter_config,
            output_config=output_config,
            last_used=config_dict.get('last_used', False)
        )
    
def convert_filter_config_types(config_data: Dict[str, Any]) -> BarcodeFilterConfig:
    """转换过滤配置中的类型，确保数值类型正确"""
    # 确保数值类型的配置项是正确的类型
    converted_data = config_data.copy()
    
    # 只处理BarcodeFilterConfig中存在的字段
    # 处理 min_length
    if 'min_length' in converted_data:
        min_length = converted_data['min_length']
        if isinstance(min_length, str):
            try:
                min_length = int(min_length)
            except ValueError:
                min_length = 1
        converted_data['min_length'] = min_length
    
    # 处理 max_length
    if 'max_length' in converted_data:
        max_length = converted_data['max_length']
        if isinstance(max_length, str):
            try:
                max_length = int(max_length)
            except ValueError:
                max_length = 1000
        converted_data['max_length'] = max_length
    
    return BarcodeFilterConfig(**converted_data)


class BarcodeSplitConfigManager:
    """条码拆分配置管理器"""
    
    def __init__(self, config_dir: str = None):
        """
        初始化配置管理器
        
        Args:
            config_dir: 配置文件目录，默认为应用目录下的config
        """
        if config_dir is None:
            # 获取app目录下的config目录
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_dir = os.path.join(app_dir, 'config')
        
        self.config_dir = config_dir
        self.config_file = os.path.join(config_dir, 'barcode_split_config.json')
        
        # 确保配置目录存在
        os.makedirs(config_dir, exist_ok=True)
        
        # 默认配置
        self.default_config = BarcodeSplitConfig()
        
        logger.debug(f"配置管理器初始化，配置文件路径: {self.config_file}")
    
    def save_config(self, config: BarcodeSplitConfig, name: str = "default") -> bool:
        """
        保存配置
        
        Args:
            config: 配置对象
            name: 配置名称
            
        Returns:
            是否保存成功
        """
        try:
            # 读取现有配置
            configs = self._load_all_configs()
            
            # 转换为可序列化的字典
            config_dict = self._config_to_dict(config)
            config_dict['last_used'] = True  # 标记为最后使用
            
            # 更新其他配置的last_used状态
            for key in configs:
                if key != name:
                    configs[key]['last_used'] = False
            
            # 保存当前配置
            configs[name] = config_dict
            
            # 写入文件
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(configs, f, ensure_ascii=False, indent=2)
            
            logger.info(f"配置保存成功: {name} -> {self.config_file}")
            return True
            
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False
    
    def load_config(self, name: str = "default") -> BarcodeSplitConfig:
        """
        加载配置
        
        Args:
            name: 配置名称
            
        Returns:
            配置对象
        """
        try:
            configs = self._load_all_configs()
            
            if name in configs:
                config = self._dict_to_config(configs[name])
                logger.info(f"配置加载成功: {name}")
                return config
            else:
                logger.warning(f"配置不存在: {name}，使用默认配置")
                return self.default_config
                
        except Exception as e:
            logger.error(f"加载配置失败: {e}，使用默认配置")
            return self.default_config
    
    def load_last_used_config(self) -> BarcodeSplitConfig:
        """
        加载最后使用的配置
        
        Returns:
            最后使用的配置对象，如果没有则返回默认配置
        """
        try:
            configs = self._load_all_configs()
            
            # 查找标记为last_used的配置
            for name, config_dict in configs.items():
                if config_dict.get('last_used', False):
                    config = self._dict_to_config(config_dict)
                    logger.info(f"加载最后使用的配置: {name}")
                    return config
            
            # 如果没有找到，使用第一个配置
            if configs:
                first_name = list(configs.keys())[0]
                config = self._dict_to_config(configs[first_name])
                logger.info(f"没有找到最后使用的配置，使用第一个配置: {first_name}")
                return config
            
            logger.info("没有找到任何配置，使用默认配置")
            return self.default_config
            
        except Exception as e:
            logger.error(f"加载最后使用的配置失败: {e}，使用默认配置")
            return self.default_config
    
    def get_all_configs(self) -> Dict[str, BarcodeSplitConfig]:
        """
        获取所有配置
        
        Returns:
            配置字典 {名称: 配置对象}
        """
        try:
            configs = self._load_all_configs()
            result = {}
            
            for name, config_dict in configs.items():
                result[name] = self._dict_to_config(config_dict)
            
            return result
            
        except Exception as e:
            logger.error(f"获取所有配置失败: {e}")
            return {"default": self.default_config}
    
    def delete_config(self, name: str) -> bool:
        """
        删除配置
        
        Args:
            name: 配置名称
            
        Returns:
            是否删除成功
        """
        try:
            if name == "default":
                logger.warning("不能删除默认配置")
                return False
            
            configs = self._load_all_configs()
            
            if name in configs:
                del configs[name]
                
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(configs, f, ensure_ascii=False, indent=2)
                
                logger.info(f"配置删除成功: {name}")
                return True
            else:
                logger.warning(f"配置不存在: {name}")
                return False
                
        except Exception as e:
            logger.error(f"删除配置失败: {e}")
            return False
    
    def export_config(self, config: BarcodeSplitConfig, file_path: str) -> bool:
        """
        导出配置到文件
        
        Args:
            config: 配置对象
            file_path: 导出文件路径
            
        Returns:
            是否导出成功
        """
        try:
            config_dict = self._config_to_dict(config)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, ensure_ascii=False, indent=2)
            
            logger.info(f"配置导出成功: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出配置失败: {e}")
            return False
    
    def import_config(self, file_path: str) -> Optional[BarcodeSplitConfig]:
        """
        从文件导入配置
        
        Args:
            file_path: 导入文件路径
            
        Returns:
            导入的配置对象，失败返回None
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config_dict = json.load(f)
            
            config = self._dict_to_config(config_dict)
            logger.info(f"配置导入成功: {file_path}")
            return config
            
        except Exception as e:
            logger.error(f"导入配置失败: {e}")
            return None
    
    def _load_all_configs(self) -> Dict[str, Any]:
        """加载所有配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                logger.debug("配置文件不存在，返回空配置")
                return {}
                
        except json.JSONDecodeError as e:
            logger.error(f"配置文件JSON格式错误: {e}")
            return {}
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return {}
    
    def _config_to_dict(self, config: BarcodeSplitConfig) -> Dict[str, Any]:
        """将配置对象转换为字典"""
        return {
            'filter_config': asdict(config.filter_config),
            'output_config': asdict(config.output_config),
            'last_used': config.last_used
        }
    
    def _dict_to_config(self, config_dict: Dict[str, Any]) -> BarcodeSplitConfig:
        """将字典转换为配置对象"""
        # 处理过滤配置的类型转换
        filter_config_data = config_dict.get('filter_config', {})
        filter_config = convert_filter_config_types(filter_config_data)
        
        output_config = BarcodeOutputConfig(**config_dict.get('output_config', {}))
        
        return BarcodeSplitConfig(
            filter_config=filter_config,
            output_config=output_config,
            last_used=config_dict.get('last_used', False)
        )
