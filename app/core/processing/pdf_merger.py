"""PDF合并处理器模块"""

import os
from typing import List, Dict, Tuple, Optional
from PyPDF2 import PdfReader, PdfWriter
from PyPDF2.generic import Destination
from app.utils.logger import get_logger

logger = get_logger('pdf_merger')


class PDFMerger:
    """PDF合并处理器"""

    def __init__(self):
        self.files_info = []

    def merge_files(self, file_list: List[str], merge_config: Dict,
                   progress_callback=None) -> Tuple[bool, str, Optional[str]]:
        """
        合并多个PDF文件

        Args:
            file_list: PDF文件路径列表
            merge_config: 合并配置
            progress_callback: 进度回调函数

        Returns:
            (成功标志, 消息, 输出文件路径)
        """
        try:
            if not file_list:
                return False, "没有选择任何文件", None

            output_name = merge_config.get('output_name', 'merged.pdf')
            output_dir = merge_config.get('output_dir', '')
            preserve_page_numbers = merge_config.get('preserve_page_numbers', False)
            encrypt = merge_config.get('encrypt', False)
            password = merge_config.get('password', '')

            if not output_dir:
                output_dir = os.path.dirname(file_list[0])

            output_path = os.path.join(output_dir, output_name)

            # 验证所有文件
            valid_files = []
            for file_path in file_list:
                if self._validate_pdf(file_path):
                    valid_files.append(file_path)
                else:
                    logger.warning(f"文件无效或无法读取: {file_path}")

            if not valid_files:
                return False, "没有有效的PDF文件", None

            # 创建写入器
            writer = PdfWriter()

            # 合并文件
            total_files = len(valid_files)
            for idx, file_path in enumerate(valid_files):
                logger.debug(f"正在处理文件 {idx+1}/{total_files}: {file_path}")

                # 更新进度
                if progress_callback:
                    progress = int((idx / total_files) * 90)  # 保留10%用于最后保存
                    progress_callback.emit(progress, f"正在合并文件 {idx+1}/{total_files}: {os.path.basename(file_path)}")

                reader = PdfReader(file_path)
                file_name = os.path.basename(file_path)

                # 获取页面范围
                page_range = merge_config.get('page_ranges', {}).get(file_path, 'all')
                pages = self._parse_page_range(page_range, len(reader.pages))

                # 添加页面
                for page_num in pages:
                    if page_num < len(reader.pages):
                        page = reader.pages[page_num]
                        writer.add_page(page)

                # 保留元数据
                if idx == 0:
                    writer.metadata = reader.metadata

            # 更新进度 - 准备保存
            if progress_callback:
                progress_callback.emit(95, "正在保存文件...")

            # 加密
            if encrypt and password:
                writer.encrypt(password)

            # 保存文件
            with open(output_path, 'wb') as f:
                writer.write(f)

            logger.info(f"合并完成: {output_path}")
            return True, f"合并成功! 共合并 {len(valid_files)} 个文件, 生成 {len(writer.pages)} 页", output_path

        except Exception as e:
            logger.error(f"合并过程中出错: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False, f"合并失败: {str(e)}", None
    
    def merge_in_groups(self, file_list: List[str], group_size: int,
                       output_dir: str, base_name: str = 'group',
                       progress_callback=None) -> Tuple[bool, str, Optional[str]]:
        """
        分组合并PDF文件

        Args:
            file_list: PDF文件路径列表
            group_size: 每组文件数量
            output_dir: 输出目录
            base_name: 输出文件名前缀
            progress_callback: 进度回调函数

        Returns:
            (成功标志, 消息, 输出文件路径/目录)
        """
        try:
            if not file_list:
                return False, "没有选择任何文件", None

            output_files = []
            total_groups = (len(file_list) + group_size - 1) // group_size

            for group_idx in range(total_groups):
                start_idx = group_idx * group_size
                end_idx = min(start_idx + group_size, len(file_list))
                group_files = file_list[start_idx:end_idx]

                group_name = f"{base_name}_{group_idx+1:02d}.pdf"
                output_path = os.path.join(output_dir, group_name)

                # 更新进度
                if progress_callback:
                    progress = int((group_idx / total_groups) * 100)
                    progress_callback.emit(progress, f"正在合并第 {group_idx+1}/{total_groups} 组...")

                config = {
                    'output_name': group_name,
                    'output_dir': output_dir,
                    'page_ranges': {f: 'all' for f in group_files}
                }

                success, message, _ = self.merge_files(group_files, config)

                if success:
                    output_files.append(output_path)
                else:
                    return False, f"第 {group_idx+1} 组合并失败: {message}", None

            logger.info(f"分组合并完成: 共 {total_groups} 组")
            return True, f"分组合并成功! 共生成 {len(output_files)} 个文件", output_dir

        except Exception as e:
            logger.error(f"分组合并过程中出错: {e}")
            return False, f"分组合并失败: {str(e)}", None
    
    def _validate_pdf(self, file_path: str) -> bool:
        """验证PDF文件是否有效"""
        try:
            if not os.path.exists(file_path):
                return False
                
            if not file_path.lower().endswith('.pdf'):
                return False
                
            reader = PdfReader(file_path)
            return len(reader.pages) > 0
            
        except Exception as e:
            logger.error(f"验证PDF文件失败 {file_path}: {e}")
            return False
    
    def _parse_page_range(self, range_str: str, total_pages: int) -> List[int]:
        """
        解析页面范围字符串
        
        Args:
            range_str: 页面范围字符串, 如 "all", "1-5", "1,3,5", "1-5,8,10-12"
            total_pages: 总页数
            
        Returns:
            页面索引列表(0-based)
        """
        if range_str.lower() == 'all':
            return list(range(total_pages))
            
        pages = []
        parts = range_str.split(',')
        
        for part in parts:
            part = part.strip()
            if '-' in part:
                # 范围, 如 "1-5"
                start, end = part.split('-')
                start = int(start.strip()) - 1  # 转为0-based
                end = int(end.strip()) - 1
                pages.extend(range(start, end + 1))
            else:
                # 单页, 如 "1"
                page = int(part) - 1  # 转为0-based
                pages.append(page)
                
        # 过滤无效页码并去重
        pages = [p for p in sorted(set(pages)) if 0 <= p < total_pages]
        return pages
    
    def _add_bookmarks(self, writer: PdfWriter, bookmarks: List[Dict]):
        """
        添加书签到PDF

        Args:
            writer: PDF写入器
            bookmarks: 书签列表, [{'title': '文件名', 'page_obj': 页面对象}, ...]
        """
        for bookmark in bookmarks:
            title = bookmark['title']
            page_obj = bookmark['page_obj']

            try:
                # 添加书签，确保标题不为空
                if not title or title.strip() == '':
                    title = '未命名'

                # 使用页面对象添加书签
                writer.add_outline_item(
                    title=title,
                    page=page_obj,
                    parent=None,
                    color=None,
                    bold=False,
                    italic=False
                )
                logger.debug(f"添加书签成功: {title}")

            except Exception as e:
                logger.error(f"添加书签失败 {title}: {e}")
    
    def get_file_info(self, file_path: str) -> Dict:
        """
        获取PDF文件信息
        
        Args:
            file_path: PDF文件路径
            
        Returns:
            文件信息字典
        """
        try:
            reader = PdfReader(file_path)
            file_size = os.path.getsize(file_path)
            
            return {
                'path': file_path,
                'name': os.path.basename(file_path),
                'pages': len(reader.pages),
                'size': file_size,
                'size_mb': file_size / (1024 * 1024)
            }
            
        except Exception as e:
            logger.error(f"获取文件信息失败 {file_path}: {e}")
            return None
