"""文件历史记录管理器模块"""

import os
import re
from datetime import datetime
from app.utils.logger import get_logger
from app.config.settings import AppSettings
from app.managers.history_db import get_database

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
        logger.info(f"[add_file_to_history] 开始添加文件到历史记录: {file_path}, page_count={page_count}")

        if not file_path:
            logger.warning("[add_file_to_history] file_path 为空，跳过添加")
            return

        if not os.path.exists(file_path):
            logger.warning(f"[add_file_to_history] 文件不存在: {file_path}")
            return

        # 检查是否为临时文件
        if self._is_temp_file(file_path):
            logger.info(f"[add_file_to_history] 跳过临时文件: {file_path}")
            return

        filename = os.path.basename(file_path)
        db = get_database()

        # 获取分类信息
        category_info = self._get_category_for_file(file_path)
        logger.info(f"[add_file_to_history] 文件分类: {category_info}")

        # 添加到数据库
        category_id = db.get_or_create_category(category_info['name'], category_info['path'])
        db.add_or_update_file(file_path, filename, category_id, page_count)

        logger.info(f"[add_file_to_history] 已添加/更新文件到历史记录: {filename} (分类: {category_info['name']}, 路径: {category_info['path']})")

    def _is_temp_file(self, file_path):
        """检查是否为临时文件"""
        temp_dir = os.path.normpath(os.path.join(os.environ.get('TEMP', '/tmp'), ''))
        file_dir = os.path.normpath(os.path.dirname(file_path))

        # 检查是否在临时目录中
        if file_dir.startswith(temp_dir):
            logger.debug(f"文件在临时目录中: {file_path}")
            return True

        # 检查文件名是否包含临时标记
        filename = os.path.basename(file_path)
        if filename.startswith('temp_') or filename.startswith('~'):
            logger.debug(f"文件名包含临时标记: {file_path}")
            return True

        return False

    def _get_category_for_file(self, file_path):
        """根据文件路径获取分类名称（返回包含完整路径的分类信息）"""
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
            # 用户自定义分类，使用配置的分类名和匹配的路径
            return {'name': matched_category, 'path': matched_path}

        # 2. 根据目录名智能分类
        dir_name = os.path.basename(file_dir)

        # 检查目录名是否包含关键词
        for keyword, category in self.KEYWORD_MAPPING.items():
            if keyword in dir_name:
                return {'name': category, 'path': file_dir}

        # 3. 只使用最后一个目录名作为分类名
        if dir_name:
            # 清理目录名，移除特殊字符
            category_name = re.sub(r'[<>:"/\\|?*]', '', dir_name)
            return {'name': category_name, 'path': file_dir}

        # 4. 无法分类，归为"未分类"
        return {'name': '未分类', 'path': file_dir}

    def get_recent_files(self):
        """获取最近文件列表（不进行文件存在性检查，避免阻塞）"""
        db = get_database()
        recent_files = db.get_recent_files()

        # 转换为兼容格式（移除数据库内部字段）
        result = []
        for file in recent_files:
            result.append({
                'path': file.get('path', ''),
                'filename': file.get('filename', ''),
                'open_time': file.get('open_time', 0),
                'open_count': file.get('open_count', 1),
                'last_page': file.get('last_page', 0),
                'page_count': file.get('page_count', 0)
            })
        return result

    def get_categories(self):
        """获取所有分类及文件（不进行文件存在性检查，避免阻塞）"""
        db = get_database()
        categories = db.get_all_categories()

        # 为每个分类获取文件列表
        result = {}
        for category in categories:
            category_id = category['id']
            category_name = category['name']
            category_path = category['path']

            files = db.get_files_by_category(category_id)

            # 转换文件格式
            file_list = []
            for file in files:
                file_list.append({
                    'path': file.get('path', ''),
                    'filename': file.get('filename', ''),
                    'open_time': file.get('open_time', 0),
                    'open_count': file.get('open_count', 1),
                    'last_page': file.get('last_page', 0),
                    'page_count': file.get('page_count', 0)
                })

            # 使用完整路径作为键（兼容原有逻辑）
            result[f"{category_name}|||{category_path}"] = {
                'name': category_name,
                'path': category_path,
                'id': category_id,
                'files': file_list
            }

        return result

    def _filter_valid_files(self, files_list):
        """过滤出仍存在的有效文件（已废弃，保留用于兼容性）"""
        return files_list

    def clear_recent_files(self):
        """清除所有最近文件记录"""
        db = get_database()
        db.clear_all_files()
        logger.info("已清除所有最近文件记录")

    def clear_category(self, category_key_or_name):
        """清空指定分类的文件记录（支持分类键或分类名）"""
        db = get_database()

        # 如果传入的是分类键（格式: "name|||path"）
        if '|||' in category_key_or_name:
            parts = category_key_or_name.split('|||')
            category_path = parts[1] if len(parts) > 1 else ''
            category = db.get_category_by_path(category_path)
            if category:
                db.clear_category_files(category['id'])
                logger.info(f"已清除分类 '{category['name']}' 的文件记录")
                return
        else:
            # 如果传入的是分类名，查找对应的分类
            categories = db.get_all_categories()
            for category in categories:
                if category['name'] == category_key_or_name:
                    db.clear_category_files(category['id'])
                    logger.info(f"已清除分类 '{category['name']}' 的文件记录")
                    return

        logger.warning(f"未找到分类 '{category_key_or_name}'")

    def remove_file_from_recent(self, file_path):
        """从最近文件中移除指定文件"""
        db = get_database()
        db.remove_file(file_path)
        logger.debug(f"已从最近文件中移除: {file_path}")

    def remove_file_from_category(self, category_name, file_path):
        """从指定分类中移除文件"""
        db = get_database()

        # 查找分类
        categories = db.get_all_categories()
        category = None
        for cat in categories:
            if cat['name'] == category_name:
                category = cat
                break

        if category:
            db.remove_file_from_category(category['id'], file_path)
            logger.debug(f"已从分类 '{category_name}' 中移除: {file_path}")
        else:
            logger.warning(f"未找到分类 '{category_name}'")

    def update_file_last_page(self, file_path, page_num):
        """更新文件的最后阅读页码"""
        db = get_database()
        db.update_file_last_page(file_path, page_num)

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
            elif delta.days == 2:
                return "前天"
            else:
                return dt.strftime("%Y-%m-%d")
        except Exception as e:
            logger.error(f"格式化时间失败: {e}")
            return str(timestamp)

    def get_statistics(self):
        """获取历史记录统计信息"""
        db = get_database()
        stats = db.get_statistics()

        total_files = stats.get('total_files', 0)
        total_categories = stats.get('total_categories', 0)
        category_stats = stats.get('category_stats', {})

        # 转换category_stats格式以兼容原有逻辑
        result_stats = {}
        for cat_id, cat_info in category_stats.items():
            result_stats[cat_info['name']] = cat_info['count']

        return {
            'total_recent': total_files,
            'total_categories': total_categories,
            'total_category_files': total_files,
            'category_stats': result_stats
        }

    def get_files_by_month(self, month):
        """获取指定月份的文件列表"""
        db = get_database()
        recent_files = db.get_recent_files()
        month_files = []

        for record in recent_files:
            open_time = record.get('open_time', 0)
            if open_time:
                dt = datetime.fromtimestamp(open_time)
                month_key = dt.strftime("%Y-%m")
                if month_key == month:
                    month_files.append({
                        'path': record.get('path', ''),
                        'filename': record.get('filename', ''),
                        'open_time': open_time,
                        'open_count': record.get('open_count', 1),
                        'last_page': record.get('last_page', 0),
                        'page_count': record.get('page_count', 0)
                    })

        # 按打开时间降序排序
        month_files.sort(key=lambda x: x.get('open_time', 0), reverse=True)

        return month_files

    def update_file_page_count(self, file_path, page_count):
        """更新文件的页数"""
        if not file_path or page_count <= 0:
            return

        db = get_database()
        db.update_file_page_count(file_path, page_count)
        logger.debug(f"更新文件页数: {file_path} -> {page_count} 页")
