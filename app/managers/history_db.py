"""文件历史记录数据库模块 - 使用SQLite存储"""

import os
import sqlite3
from datetime import datetime
from app.utils.app_path import get_config_dir
from app.utils.logger import get_logger

logger = get_logger('history_db')


class HistoryDatabase:
    """文件历史记录数据库管理类"""

    def __init__(self):
        self.db_path = os.path.join(get_config_dir(), "file_history.db")
        self._connection = None
        self._initialize_database()

    @property
    def connection(self):
        """获取数据库连接（懒加载）"""
        if self._connection is None:
            self._connection = sqlite3.connect(self.db_path, timeout=10)
            self._connection.row_factory = sqlite3.Row
        return self._connection

    def close(self):
        """关闭数据库连接"""
        if self._connection:
            self._connection.close()
            self._connection = None

    def _initialize_database(self):
        """初始化数据库表结构"""
        try:
            conn = self.connection
            cursor = conn.cursor()

            # 分类表 - 存储目录分类信息
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    path TEXT NOT NULL UNIQUE
                )
            ''')

            # 文件表 - 存储文件历史记录
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category_id INTEGER REFERENCES categories(id) ON DELETE CASCADE,
                    path TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    open_time INTEGER NOT NULL DEFAULT 0,
                    open_count INTEGER NOT NULL DEFAULT 1,
                    last_page INTEGER NOT NULL DEFAULT 0,
                    page_count INTEGER NOT NULL DEFAULT 0
                )
            ''')

            # 创建索引提高查询性能
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_path ON files(path)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_category ON files(category_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_open_time ON files(open_time DESC)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_categories_path ON categories(path)')

            conn.commit()
            logger.debug(f"数据库初始化完成: {self.db_path}")
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise

    # ==================== 分类相关操作 ====================

    def get_or_create_category(self, name, path):
        """获取或创建分类"""
        cursor = self.connection.cursor()
        try:
            # 先尝试通过path获取
            cursor.execute('SELECT id FROM categories WHERE path = ?', (path,))
            row = cursor.fetchone()
            if row:
                logger.debug(f"找到已存在的分类: {name} ({path}), id={row['id']}")
                return row['id']

            # 不存在则创建
            cursor.execute('INSERT INTO categories (name, path) VALUES (?, ?)', (name, path))
            self.connection.commit()
            logger.info(f"创建新分类: {name} ({path}), id={cursor.lastrowid}")
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"获取/创建分类失败: {e}")
            raise

    def get_all_categories(self):
        """获取所有分类"""
        cursor = self.connection.cursor()
        try:
            cursor.execute('SELECT id, name, path FROM categories ORDER BY name')
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"获取分类列表失败: {e}")
            return []

    def get_category_by_id(self, category_id):
        """根据ID获取分类"""
        cursor = self.connection.cursor()
        try:
            cursor.execute('SELECT id, name, path FROM categories WHERE id = ?', (category_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"获取分类失败: {e}")
            return None

    def get_category_by_path(self, path):
        """根据路径获取分类"""
        cursor = self.connection.cursor()
        try:
            cursor.execute('SELECT id, name, path FROM categories WHERE path = ?', (path,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"获取分类失败: {e}")
            return None

    def delete_category(self, category_id):
        """删除分类（级联删除关联文件）"""
        cursor = self.connection.cursor()
        try:
            cursor.execute('DELETE FROM categories WHERE id = ?', (category_id,))
            self.connection.commit()
            logger.debug(f"删除分类: {category_id}")
        except Exception as e:
            logger.error(f"删除分类失败: {e}")
            raise

    def clear_category_files(self, category_id):
        """清空分类下的所有文件"""
        cursor = self.connection.cursor()
        try:
            cursor.execute('DELETE FROM files WHERE category_id = ?', (category_id,))
            self.connection.commit()
            logger.debug(f"清空分类文件: {category_id}")
        except Exception as e:
            logger.error(f"清空分类文件失败: {e}")
            raise

    # ==================== 文件相关操作 ====================

    def add_or_update_file(self, file_path, filename, category_id, page_count=0):
        """添加或更新文件记录"""
        cursor = self.connection.cursor()
        try:
            import time

            # 检查文件是否已存在
            cursor.execute('SELECT id, open_count FROM files WHERE path = ?', (file_path,))
            row = cursor.fetchone()

            if row:
                # 更新现有记录
                cursor.execute('''
                    UPDATE files
                    SET open_time = ?,
                        open_count = ?,
                        page_count = ?
                    WHERE id = ?
                ''', (int(time.time()), row['open_count'] + 1, page_count, row['id']))
                logger.info(f"更新文件记录: {filename}, id={row['id']}, open_count={row['open_count'] + 1}")
            else:
                # 插入新记录
                cursor.execute('''
                    INSERT INTO files (category_id, path, filename, open_time, open_count, page_count)
                    VALUES (?, ?, ?, ?, 1, ?)
                ''', (category_id, file_path, filename, int(time.time()), page_count))
                new_id = cursor.lastrowid
                logger.info(f"添加新文件记录: {filename}, id={new_id}, category_id={category_id}")

            self.connection.commit()
        except Exception as e:
            logger.error(f"添加/更新文件失败: {e}")
            self.connection.rollback()
            raise

    def get_files_by_category(self, category_id, limit=None):
        """获取分类下的文件列表"""
        cursor = self.connection.cursor()
        try:
            if limit:
                cursor.execute('''
                    SELECT id, category_id, path, filename, open_time, open_count, last_page, page_count
                    FROM files
                    WHERE category_id = ?
                    ORDER BY open_time DESC
                    LIMIT ?
                ''', (category_id, limit))
            else:
                cursor.execute('''
                    SELECT id, category_id, path, filename, open_time, open_count, last_page, page_count
                    FROM files
                    WHERE category_id = ?
                    ORDER BY open_time DESC
                ''', (category_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"获取分类文件失败: {e}")
            return []

    def get_file_by_path(self, file_path):
        """根据路径获取文件"""
        cursor = self.connection.cursor()
        try:
            cursor.execute('''
                SELECT id, category_id, path, filename, open_time, open_count, last_page, page_count
                FROM files
                WHERE path = ?
            ''', (file_path,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"获取文件失败: {e}")
            return None

    def remove_file(self, file_path):
        """删除文件记录"""
        cursor = self.connection.cursor()
        try:
            cursor.execute('DELETE FROM files WHERE path = ?', (file_path,))
            self.connection.commit()
            logger.debug(f"删除文件记录: {file_path}")
        except Exception as e:
            logger.error(f"删除文件失败: {e}")
            raise

    def remove_file_from_category(self, category_id, file_path):
        """从指定分类中删除文件"""
        cursor = self.connection.cursor()
        try:
            cursor.execute('DELETE FROM files WHERE category_id = ? AND path = ?', (category_id, file_path))
            self.connection.commit()
            logger.debug(f"从分类 {category_id} 中删除文件: {file_path}")
        except Exception as e:
            logger.error(f"删除文件失败: {e}")
            raise

    def update_file_last_page(self, file_path, page_num):
        """更新文件的最后阅读页码"""
        cursor = self.connection.cursor()
        try:
            cursor.execute('UPDATE files SET last_page = ? WHERE path = ?', (page_num, file_path))
            self.connection.commit()
        except Exception as e:
            logger.error(f"更新文件页码失败: {e}")
            raise

    def update_file_page_count(self, file_path, page_count):
        """更新文件的页数"""
        cursor = self.connection.cursor()
        try:
            cursor.execute('UPDATE files SET page_count = ? WHERE path = ?', (page_count, file_path))
            self.connection.commit()
        except Exception as e:
            logger.error(f"更新文件页数失败: {e}")
            raise

    # ==================== 最近文件相关操作 ====================

    def get_recent_files(self, limit=None):
        """获取最近打开的文件列表"""
        cursor = self.connection.cursor()
        try:
            if limit:
                cursor.execute('''
                    SELECT f.id, f.category_id, f.path, f.filename, f.open_time, f.open_count, f.last_page, f.page_count,
                           c.name as category_name, c.path as category_path
                    FROM files f
                    LEFT JOIN categories c ON f.category_id = c.id
                    ORDER BY f.open_time DESC
                    LIMIT ?
                ''', (limit,))
            else:
                cursor.execute('''
                    SELECT f.id, f.category_id, f.path, f.filename, f.open_time, f.open_count, f.last_page, f.page_count,
                           c.name as category_name, c.path as category_path
                    FROM files f
                    LEFT JOIN categories c ON f.category_id = c.id
                    ORDER BY f.open_time DESC
                ''')
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"获取最近文件失败: {e}")
            return []

    def clear_all_files(self):
        """清空所有文件记录"""
        cursor = self.connection.cursor()
        try:
            cursor.execute('DELETE FROM files')
            self.connection.commit()
            logger.info("已清空所有文件记录")
        except Exception as e:
            logger.error(f"清空文件记录失败: {e}")
            raise

    # ==================== 统计相关操作 ====================

    def get_statistics(self):
        """获取统计信息"""
        cursor = self.connection.cursor()
        try:
            stats = {}

            # 总文件数
            cursor.execute('SELECT COUNT(*) as count FROM files')
            stats['total_files'] = cursor.fetchone()['count']

            # 总分类数
            cursor.execute('SELECT COUNT(*) as count FROM categories')
            stats['total_categories'] = cursor.fetchone()['count']

            # 各分类文件数
            cursor.execute('''
                SELECT c.id, c.name, COUNT(f.id) as file_count
                FROM categories c
                LEFT JOIN files f ON c.id = f.category_id
                GROUP BY c.id, c.name
                ORDER BY c.name
            ''')
            stats['category_stats'] = {row['id']: {'name': row['name'], 'count': row['file_count']}
                                      for row in cursor.fetchall()}

            return stats
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}

    # ==================== 数据迁移 ====================

    def migrate_from_json(self, json_data):
        """从JSON数据迁移到SQLite"""
        cursor = self.connection.cursor()
        try:
            # 迁移分类和文件
            categories = json_data.get('categories', {})

            for key, value in categories.items():
                if not isinstance(value, dict) or 'files' not in value:
                    continue

                name = value.get('name', '')
                path = value.get('path', '')
                files = value.get('files', [])

                # 创建或获取分类
                category_id = self.get_or_create_category(name, path)

                # 迁移文件
                for file_record in files:
                    file_path = file_record.get('path', '')
                    filename = file_record.get('filename', '')
                    open_time = file_record.get('open_time', 0)
                    open_count = file_record.get('open_count', 1)
                    last_page = file_record.get('last_page', 0)
                    page_count = file_record.get('page_count', 0)

                    try:
                        cursor.execute('''
                            INSERT INTO files (category_id, path, filename, open_time, open_count, last_page, page_count)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (category_id, file_path, filename, open_time, open_count, last_page, page_count))
                    except sqlite3.IntegrityError:
                        # 文件已存在，跳过
                        pass

            self.connection.commit()
            logger.info(f"从JSON迁移完成，共 {len(categories)} 个分类")
            return True
        except Exception as e:
            logger.error(f"JSON迁移失败: {e}")
            self.connection.rollback()
            return False


# 全局数据库实例
_db_instance = None


def get_database():
    """获取数据库单例实例"""
    global _db_instance
    if _db_instance is None:
        _db_instance = HistoryDatabase()
    return _db_instance


def close_database():
    """关闭数据库连接"""
    global _db_instance
    if _db_instance:
        _db_instance.close()
        _db_instance = None
