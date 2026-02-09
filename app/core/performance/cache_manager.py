"""
缓存管理器
实现高效的LRU缓存策略，管理页面渲染和缩略图缓存
"""

import os
import time
import pickle
import sys
import hashlib
# 添加项目根目录到Python路径，解决模块导入问题
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 导入日志模块
from app.utils.logger import get_logger
logger = get_logger('cache_manager')

from collections import OrderedDict
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import QObject, QTimer, QByteArray, QBuffer, QIODevice


class LRUCache:
    """线程安全的LRU缓存实现"""
    
    def __init__(self, max_size=50):
        self.max_size = max_size
        self.cache = OrderedDict()
        self.hit_count = 0
        self.miss_count = 0
        self.total_requests = 0
        
    def get(self, key):
        """获取缓存项"""
        self.total_requests += 1
        if key in self.cache:
            # 移动到末尾（最近使用）
            value = self.cache.pop(key)
            self.cache[key] = value
            self.hit_count += 1
            return value
        else:
            self.miss_count += 1
            return None
            
    def put(self, key, value):
        """添加缓存项"""
        if key in self.cache:
            # 更新现有项
            self.cache.pop(key)
        elif len(self.cache) >= self.max_size:
            # 移除最久未使用的项
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
            
        self.cache[key] = value
        
    def remove(self, key):
        """移除缓存项"""
        if key in self.cache:
            del self.cache[key]
            
    def clear(self):
        """清空缓存"""
        self.cache.clear()
        self.hit_count = 0
        self.miss_count = 0
        self.total_requests = 0
        
    def size(self):
        """获取缓存大小"""
        return len(self.cache)
        
    def get_hit_rate(self):
        """获取缓存命中率"""
        if self.total_requests == 0:
            return 0.0
        return self.hit_count / self.total_requests


class RenderCache(QObject):
    """页面渲染缓存管理器"""
    
    def __init__(self, max_memory_mb=200, max_items=50):
        super().__init__()
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.max_items = max_items
        
        # 不同类型缓存
        self.page_cache = LRUCache(max_items)
        self.thumbnail_cache = LRUCache(max_items * 2)  # 缩略图可以更多
        
        # 内存使用估算
        self.current_memory_usage = 0
        self.cache_memory_map = {}  # key -> estimated memory size
        
        # 定期清理
        self.cleanup_timer = QTimer()
        self.cleanup_timer.timeout.connect(self._auto_cleanup)
        self.cleanup_timer.start(30000)  # 每30秒清理一次
        
    def _estimate_memory_usage(self, pixmap):
        """估算QPixmap的内存使用量"""
        if pixmap is None:
            return 0
        # 近似计算：width * height * 4字节(RGBA)
        return pixmap.width() * pixmap.height() * 4
        
    def _get_cache_key(self, page_num, zoom_factor, render_size):
        """生成缓存键"""
        return f"page_{page_num}_zoom_{zoom_factor:.2f}_size_{render_size[0]}x{render_size[1]}"

    def _get_render_key(self, page_num, zoom_factor, render_size, file_id=None):
        """生成页面渲染缓存键"""
        if file_id:
            return f"{file_id}_page_{page_num}_zoom_{zoom_factor:.2f}_size_{render_size[0]}x{render_size[1]}"
        return self._get_cache_key(page_num, zoom_factor, render_size)

    def get_rendered_page(self, page_num, zoom_factor, render_size, file_id=None):
        """获取渲染的页面"""
        key = self._get_render_key(page_num, zoom_factor, render_size, file_id)
        pixmap = self.page_cache.get(key)

        if pixmap:
            # 更新内存使用估算（如果需要）
            if key not in self.cache_memory_map:
                self.cache_memory_map[key] = self._estimate_memory_usage(pixmap)

        return pixmap

    def put_rendered_page(self, page_num, zoom_factor, render_size, pixmap, file_id=None):
        """缓存渲染的页面"""
        key = self._get_render_key(page_num, zoom_factor, render_size, file_id)
        estimated_size = self._estimate_memory_usage(pixmap)

        # 检查内存限制
        if self.current_memory_usage + estimated_size > self.max_memory_bytes:
            self._cleanup_memory(estimated_size)

        # 如果还是放不下，不缓存
        if self.current_memory_usage + estimated_size > self.max_memory_bytes:
            return False

        # 更新内存使用
        if key in self.cache_memory_map:
            self.current_memory_usage -= self.cache_memory_map[key]

        self.page_cache.put(key, pixmap)
        self.cache_memory_map[key] = estimated_size
        self.current_memory_usage += estimated_size

        return True

    def get_thumbnail(self, page_num, size, file_id=None):
        """获取缩略图"""
        key = self._get_thumbnail_key(page_num, size, file_id)
        return self.thumbnail_cache.get(key)

    def put_thumbnail(self, page_num, size, pixmap, file_id=None):
        """缓存缩略图"""
        key = self._get_thumbnail_key(page_num, size, file_id)
        estimated_size = self._estimate_memory_usage(pixmap)

        # 缩略图缓存相对宽松，但仍需控制总内存
        if self.current_memory_usage + estimated_size > self.max_memory_bytes * 1.5:
            self._cleanup_memory(estimated_size)

        self.thumbnail_cache.put(key, pixmap)

        if key not in self.cache_memory_map:
            self.cache_memory_map[key] = estimated_size
            self.current_memory_usage += estimated_size

    def _get_thumbnail_key(self, page_num, size, file_id=None):
        """生成缩略图缓存键"""
        if file_id:
            return f"{file_id}_thumb_{page_num}_size_{size[0]}x{size[1]}"
        return f"thumb_{page_num}_size_{size[0]}x{size[1]}"
            
    def _cleanup_memory(self, needed_bytes):
        """清理内存以满足需求"""
        freed = 0
        # 优先清理缩略图缓存（较小）
        for key in list(self.thumbnail_cache.cache.keys()):
            if freed >= needed_bytes:
                break
            if key in self.cache_memory_map:
                freed += self.cache_memory_map[key]
                del self.cache_memory_map[key]
            self.thumbnail_cache.remove(key)
            
        self.current_memory_usage = sum(self.cache_memory_map.values())
        
    def _auto_cleanup(self):
        """自动清理过期缓存"""
        # 清理命中率很低的缓存项
        if self.page_cache.get_hit_rate() < 0.1 and self.page_cache.size() > 10:
            # 清理一半的页面缓存
            keys_to_remove = list(self.page_cache.cache.keys())[:self.page_cache.size() // 2]
            for key in keys_to_remove:
                if key in self.cache_memory_map:
                    self.current_memory_usage -= self.cache_memory_map[key]
                    del self.cache_memory_map[key]
                self.page_cache.remove(key)
                
    def clear_all(self):
        """清空所有缓存"""
        self.page_cache.clear()
        self.thumbnail_cache.clear()
        self.cache_memory_map.clear()
        self.current_memory_usage = 0
        
    def get_stats(self):
        """获取缓存统计信息"""
        return {
            'page_cache_size': self.page_cache.size(),
            'page_cache_hit_rate': self.page_cache.get_hit_rate(),
            'thumbnail_cache_size': self.thumbnail_cache.size(),
            'thumbnail_cache_hit_rate': self.thumbnail_cache.get_hit_rate(),
            'current_memory_usage_mb': self.current_memory_usage / (1024 * 1024),
            'max_memory_usage_mb': self.max_memory_bytes / (1024 * 1024)
        }


class DiskCache:
    """磁盘缓存管理器"""
    
    def __init__(self, cache_dir="cache", max_size_mb=500):
        self.cache_dir = cache_dir
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.ensure_cache_dir()
        
    def ensure_cache_dir(self):
        """确保缓存目录存在"""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
            
    def _get_cache_path(self, key):
        """获取缓存文件路径"""
        # 对key进行哈希以避免文件名过长
        hash_key = hashlib.md5(str(key).encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{hash_key}.cache")
        
    def get(self, key):
        """从磁盘缓存获取"""
        cache_path = self._get_cache_path(key)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'rb') as f:
                    data = pickle.load(f)
                    # 检查是否过期（24小时）
                    if time.time() - data['timestamp'] < 86400:
                        # 检查是否是QPixmap对象的序列化数据
                        if isinstance(data['value'], dict) and 'pixmap_data' in data['value']:
                            # 从字节数据重建QPixmap
                            try:
                                pixmap = QPixmap()
                                pixmap_data = data['value']['pixmap_data']
                                # 确保pixmap_data是bytes类型
                                if isinstance(pixmap_data, str):
                                    pixmap_data = pixmap_data.encode('latin1')
                                elif not isinstance(pixmap_data, bytes):
                                    pixmap_data = bytes(pixmap_data)
                                    
                                if pixmap.loadFromData(pixmap_data):
                                    return pixmap
                                else:
                                    # 如果loadFromData失败，尝试其他方法
                                    byte_array = QByteArray(pixmap_data)
                                    if pixmap.loadFromData(byte_array):
                                        return pixmap
                            except Exception as e:
                                logger.error(f"重建QPixmap对象失败: {e}")
                                pass  # 如果重建失败，返回None
                        return data['value']
                    else:
                        # 过期，删除文件
                        os.remove(cache_path)
            except Exception as e:
                logger.error(f"读取磁盘缓存失败: {e}")
                pass
        return None
        
    def put(self, key, value):
        """保存到磁盘缓存"""
        cache_path = self._get_cache_path(key)
        try:
            # 如果是QPixmap对象，先转换为字节数据
            if str(type(value)).find('QPixmap') != -1 or hasattr(value, 'saveToData'):  # 更可靠的QPixmap检测
                try:
                    # 尝试使用saveToData方法
                    pixmap_data = value.saveToData()
                    if pixmap_data:  # 如果转换成功
                        value = {'pixmap_data': pixmap_data}
                    else:
                        # 如果saveToData失败，尝试其他方法
                        byte_array = QByteArray()
                        buffer = QBuffer(byte_array)
                        buffer.open(QIODevice.WriteOnly)
                        value.save(buffer, "PNG")
                        value = {'pixmap_data': bytes(byte_array.data())}  # 确保转换为bytes
                except Exception as e:
                    # 如果上面的方法都失败了，使用另一种方法
                    try:
                        byte_array = QByteArray()
                        buffer = QBuffer(byte_array)
                        buffer.open(QIODevice.WriteOnly)
                        value.save(buffer, "PNG")
                        value = {'pixmap_data': bytes(byte_array.data())}
                    except Exception as e2:
                        # 如果所有方法都失败，记录错误但不中断主流程
                        logger.error(f"无法序列化QPixmap对象: {e2}")
                        return  # 不缓存这个对象
            
            data = {
                'value': value,
                'timestamp': time.time()
            }
            with open(cache_path, 'wb') as f:
                pickle.dump(data, f)
                
            # 检查磁盘缓存大小
            self._cleanup_if_needed()
        except Exception as e:
            logger.error(f"保存磁盘缓存失败: {e}")
            
    def _cleanup_if_needed(self):
        """如果需要，清理磁盘缓存"""
        total_size = 0
        cache_files = []
        
        for filename in os.listdir(self.cache_dir):
            if filename.endswith('.cache'):
                filepath = os.path.join(self.cache_dir, filename)
                try:
                    size = os.path.getsize(filepath)
                    mtime = os.path.getmtime(filepath)
                    cache_files.append((filepath, size, mtime))
                    total_size += size
                except:
                    pass
                    
        # 如果超过限制，删除最旧的文件
        if total_size > self.max_size_bytes:
            # 按修改时间排序
            cache_files.sort(key=lambda x: x[2])
            
            for filepath, size, _ in cache_files:
                try:
                    os.remove(filepath)
                    total_size -= size
                    if total_size <= self.max_size_bytes * 0.8:  # 保留20%空间
                        break
                except:
                    pass
                    
    def clear_all(self):
        """清空磁盘缓存"""
        try:
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.cache'):
                    os.remove(os.path.join(self.cache_dir, filename))
        except:
            pass