"""文件历史记录管理器模块"""

import os
import re
from datetime import datetime
from app.utils.logger import get_logger
from app.config.settings import AppSettings

logger = get_logger('history_manager')


class HistoryManager:
    """文件历史记录管理器 - 负责管理文件的打开历史和分类"""

    # 常见目录关键词到分类的映射
    KEYWORD_MAPPING = {
        '工作': '工作文档',
        '文档': '工作文档',
        '项目': '工作文档',
        '学习': '学习资料',
        '教程': '学习资料',
        '书籍': '电子书籍',
        '图书': '电子书籍',
        '资料': '学习资料',
        '下载': '下载文件',
        '临时': '临时文件'
    }

    def __init__(self, parent_window):
        self.parent = parent_window

    def add_file_to_history(self, file_path, page_count=0):
        """添加文件到历史记录（同时更新最近项目和分类记录）"""
        if not file_path or not os.path.exists(file_path):
            return

        # 检查是否为临时文件
        if self._is_temp_file(file_path):
            logger.debug(f"跳过临时文件: {file_path}")
            return

        filename = os.path.basename(file_path)

        # 1. 添加到最近项目
        AppSettings.add_recent_file(file_path, filename, page_count)

        # 2. 添加到分类
        category_name = self._get_category_for_file(file_path)
        AppSettings.add_file_to_category(file_path, filename, category_name, page_count)

        logger.debug(f"已添加文件到历史记录: {filename} (分类: {category_name})")

    def _is_temp_file(self, file_path):
        """检查是否为临时文件"""
        temp_dir = os.path.normpath(os.path.join(os.environ.get('TEMP', '/tmp'), ''))
        file_dir = os.path.normpath(os.path.dirname(file_path))

        # 检查是否在临时目录中
        if file_dir.startswith(temp_dir):
            return True

        # 检查文件名是否包含临时标记
        filename = os.path.basename(file_path)
        if filename.startswith('temp_') or filename.startswith('~'):
            return True

        return False

    def _get_category_for_file(self, file_path):
        """根据文件路径获取分类名称"""
        file_dir = os.path.dirname(file_path)

        # 1. 检查用户自定义的映射规则
        category_mapping = AppSettings.get_category_mapping()

        # 使用最长前缀匹配
        matched_path = None
        matched_category = None

        for dir_path, category in category_mapping.items():
            if file_dir.startswith(dir_path):
                if matched_path is None or len(dir_path) > len(matched_path):
                    matched_path = dir_path
                    matched_category = category

        if matched_category:
            return matched_category

        # 2. 根据目录名智能分类
        dir_name = os.path.basename(file_dir)

        # 检查目录名是否包含关键词
        for keyword, category in self.KEYWORD_MAPPING.items():
            if keyword in dir_name:
                return category

        # 3. 使用目录名作为分类
        if dir_name:
            # 清理目录名，移除特殊字符
            category_name = re.sub(r'[<>:"/\\|?*]', '', dir_name)
            return category_name

        # 4. 无法分类，归为"未分类"
        return '未分类'

    def get_recent_files(self):
        """获取最近文件列表（不进行文件存在性检查，避免阻塞）"""
        recent_files = AppSettings.get_recent_files()
        return recent_files

    def get_categories(self):
        """获取所有分类及文件（不进行文件存在性检查，避免阻塞）"""
        categories = AppSettings.get_file_categories()
        return categories

    def _filter_valid_files(self, files_list):
        """过滤出仍存在的有效文件（已废弃，保留用于兼容性）"""
        return files_list

    def clear_recent_files(self):
        """清除所有最近文件记录"""
        AppSettings.clear_recent_files()
        logger.info("已清除所有最近文件记录")

    def clear_category(self, category_name):
        """清空指定分类的文件记录"""
        AppSettings.clear_category(category_name)
        logger.info(f"已清除分类 '{category_name}' 的文件记录")

    def remove_file_from_recent(self, file_path):
        """从最近文件中移除指定文件"""
        AppSettings.remove_file_from_recent(file_path)
        logger.debug(f"已从最近文件中移除: {file_path}")

    def remove_file_from_category(self, category_name, file_path):
        """从指定分类中移除文件"""
        AppSettings.remove_file_from_category(category_name, file_path)
        logger.debug(f"已从分类 '{category_name}' 中移除: {file_path}")

    def update_file_last_page(self, file_path, page_num):
        """更新文件的最后阅读页码"""
        AppSettings.update_file_last_page(file_path, page_num)

    def format_open_time(self, timestamp):
        """格式化打开时间"""
        try:
            dt = datetime.fromtimestamp(timestamp)
            now = datetime.now()
            delta = now - dt

            if delta.days == 0:
                if delta.seconds < 3600:
                    minutes = delta.seconds // 60
                    if minutes == 0:
                        return "刚刚"
                    return f"{minutes}分钟前"
                else:
                    hours = delta.seconds // 3600
                    return f"{hours}小时前"
            elif delta.days == 1:
                return "昨天"
            elif delta.days < 7:
                return f"{delta.days}天前"
            else:
                return dt.strftime("%Y-%m-%d")
        except Exception as e:
            logger.error(f"格式化时间失败: {e}")
            return str(timestamp)

    def get_statistics(self):
        """获取历史记录统计信息"""
        recent_files = AppSettings.get_recent_files()
        categories = AppSettings.get_file_categories()

        total_recent = len(recent_files)
        total_categories = len(categories)

        category_stats = {}
        total_category_files = 0

        for category_name, files in categories.items():
            count = len(files)
            category_stats[category_name] = count
            total_category_files += count

        return {
            'total_recent': total_recent,
            'total_categories': total_categories,
            'total_category_files': total_category_files,
            'category_stats': category_stats
        }

    def get_files_by_month(self, month):
        """获取指定月份的文件列表"""
        from datetime import datetime
        recent_files = AppSettings.get_recent_files()
        month_files = []

        for record in recent_files:
            open_time = record.get('open_time', 0)
            if open_time:
                dt = datetime.fromtimestamp(open_time)
                month_key = dt.strftime("%Y-%m")
                if month_key == month:
                    month_files.append(record)

        # 按打开时间降序排序
        month_files.sort(key=lambda x: x.get('open_time', 0), reverse=True)

        return month_files

    def update_file_page_count(self, file_path, page_count):
        """更新文件的页数"""
        if not file_path or page_count <= 0:
            return

        # 更新最近文件中的页数
        AppSettings.update_recent_file_page_count(file_path, page_count)

        # 更新分类文件中的页数
        categories = AppSettings.get_file_categories()
        for category_name, files in categories.items():
            for record in files:
                if record.get('path') == file_path:
                    AppSettings.update_category_file_page_count(category_name, file_path, page_count)
                    logger.debug(f"更新文件页数: {file_path} -> {page_count} 页")
                    return
