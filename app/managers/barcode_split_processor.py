"""条码拆分处理器模块"""

import os
import fitz
import PyPDF2
from typing import Dict, List, Tuple, Optional, Callable
from dataclasses import dataclass
from PyQt5.QtCore import QThread, pyqtSignal

from app.utils.logger import get_logger
from app.managers.barcode_detector import BarcodeDetector, BarcodeInfo
from app.managers.barcode_split_config import BarcodeSplitConfig

logger = get_logger('barcode_split_processor')


@dataclass
class SplitResult:
    """拆分结果"""
    success: bool
    message: str
    files_created: List[str]
    barcodes_found: int
    pages_processed: int
    output_dir: str = ""


class BarcodeSplitThread(QThread):
    """条码拆分线程"""
    
    progress_updated = pyqtSignal(int, str)  # 进度百分比, 消息
    finished = pyqtSignal(object)  # SplitResult
    error_occurred = pyqtSignal(str)  # 错误消息
    
    def __init__(self, pdf_path: str, config: BarcodeSplitConfig, 
                 pre_detected_barcodes: Optional[List[BarcodeInfo]] = None,
                 progress_callback: Optional[Callable] = None):
        super().__init__()
        self.pdf_path = pdf_path
        self.config = config
        self.pre_detected_barcodes = pre_detected_barcodes
        self.progress_callback = progress_callback
        self.processor = BarcodeSplitProcessor()
    
    def run(self):
        """执行拆分操作"""
        try:
            def update_progress(percent: int, message: str):
                self.progress_updated.emit(percent, message)
                if self.progress_callback:
                    self.progress_callback(percent, message)
            
            result = self.processor.split_pdf(
                self.pdf_path, 
                self.config, 
                progress_callback=update_progress,
                pre_detected_barcodes=self.pre_detected_barcodes
            )
            self.finished.emit(result)
            
        except Exception as e:
            logger.error(f"条码拆分线程执行失败: {e}")
            self.error_occurred.emit(f"拆分过程中发生错误: {str(e)}")


class BarcodeSplitProcessor:
    """条码拆分处理器"""
    
    def __init__(self):
        """初始化处理器"""
        self.detector = BarcodeDetector()
        logger.debug("条码拆分处理器初始化")
    
    def split_pdf(self, pdf_path: str, config: BarcodeSplitConfig, 
                  progress_callback: Optional[Callable] = None,
                  pre_detected_barcodes: Optional[List[BarcodeInfo]] = None) -> SplitResult:
        """
        根据条码拆分PDF
        
        Args:
            pdf_path: PDF文件路径
            config: 拆分配置
            progress_callback: 进度回调函数 (percent, message) -> None
            pre_detected_barcodes: 预先检测的条码列表（可选）
            
        Returns:
            拆分结果
        """
        try:
            if progress_callback:
                progress_callback(5, "正在读取PDF文件...")
            
            # 验证文件
            if not os.path.exists(pdf_path):
                return SplitResult(
                    success=False,
                    message="PDF文件不存在",
                    files_created=[],
                    barcodes_found=0,
                    pages_processed=0,
                    output_dir=config.output_config.output_dir if config else ""
                )
            
            # 打开PDF文档
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            
            if progress_callback:
                progress_callback(10, f"PDF文件共 {total_pages} 页，开始检测条码...")
            
            # 配置检测器
            enabled_types = config.filter_config.enabled_types
            logger.debug(f"配置检测器，原始启用类型: {enabled_types}")
            # 特殊处理：如果只选择了ALL_TYPES，需要展开为所有具体类型
            if len(enabled_types) == 1 and enabled_types[0] == "ALL_TYPES":
                enabled_types = list(self.detector.BARCODE_TYPES.keys())
                logger.debug(f"展开ALL_TYPES为具体类型: {enabled_types}")
            self.detector.set_enabled_types(enabled_types)
            
            # 检测条码
            # 如果提供了预先检测的条码，则跳过检测步骤
            if pre_detected_barcodes is not None:
                all_barcodes = pre_detected_barcodes
                if progress_callback:
                    progress_callback(30, f"使用预先检测的 {len(all_barcodes)} 个条码，正在过滤...")
            else:
                # 使用both方法同时检测嵌入图片和渲染页面中的条码
                def page_progress_callback(current, total, message):
                    if progress_callback:
                        # 将页面进度映射到总体进度(15-30%)
                        overall_percent = 15 + int((current / total) * 15)
                        progress_callback(overall_percent, message)
                
                if progress_callback:
                    progress_callback(15, "正在检测条码...")
                all_barcodes = self.detector.detect_barcodes_in_document(doc, method="both", progress_callback=page_progress_callback)
                
                if progress_callback:
                    progress_callback(30, f"检测到 {len(all_barcodes)} 个条码，正在过滤...")
            
            # 过滤条码
            filtered_barcodes = self.detector.filter_barcodes(
                all_barcodes,
                min_length=config.filter_config.min_length,
                max_length=config.filter_config.max_length,
                include_keywords=config.filter_config.include_keywords,
                exclude_keywords=config.filter_config.exclude_keywords,
                include_regex=config.filter_config.include_regex,
                exclude_regex=config.filter_config.exclude_regex
            )
            
            if not filtered_barcodes:
                doc.close()
                return SplitResult(
                    success=False,
                    message="没有找到符合条件的条码",
                    files_created=[],
                    barcodes_found=len(all_barcodes),
                    pages_processed=total_pages,
                    output_dir=config.output_config.output_dir
                )
            
            if progress_callback:
                progress_callback(40, f"过滤后剩余 {len(filtered_barcodes)} 个条码，正在分组...")
            
            # 按条码值分组
            barcode_groups = self.detector.group_barcodes_by_data(filtered_barcodes)
            
            # 创建输出目录
            output_dir = config.output_config.output_dir
            os.makedirs(output_dir, exist_ok=True)
            
            if progress_callback:
                progress_callback(50, f"准备拆分 {len(barcode_groups)} 个组...")
            
            # 执行拆分
            files_created = []
            group_index = 0
            
            # 执行拆分
            files_created = []
            
            # 根据多条码处理模式决定处理方式
            if config.output_config.multi_barcode_handling == "duplicate_page":
                # 一页属于多个文档模式
                all_barcodes = []
                for barcode_list in barcode_groups.values():
                    all_barcodes.extend(barcode_list)
                files_created = self._create_split_files_for_multi_barcodes(
                    doc, all_barcodes, config, output_dir
                )
            else:
                # 默认模式：以第一个条码为准
                # 根据重复处理模式决定拆分策略
                if config.output_config.duplicate_handling == "merge":
                    # 合并模式：使用Combine模式分组逻辑
                    all_barcodes = []
                    for barcode_list in barcode_groups.values():
                        all_barcodes.extend(barcode_list)
                    files_created = self._group_and_merge_barcodes_combine_mode(
                        doc, all_barcodes, config, output_dir
                    )
                else:
                    # 分离模式：使用Filename模式分组逻辑
                    all_barcodes = []
                    for barcode_list in barcode_groups.values():
                        all_barcodes.extend(barcode_list)
                    files_created = self._group_and_merge_barcodes_filename_mode(
                        doc, all_barcodes, config, output_dir
                    )
            
            doc.close()
            
            if progress_callback:
                progress_callback(95, "清理临时文件...")
            
            # 清理
            self._cleanup()
            
            if progress_callback:
                progress_callback(100, "拆分完成")
            
            logger.info(f"PDF条码拆分完成，共创建 {len(files_created)} 个文件")
            
            return SplitResult(
                success=True,
                message=f"成功拆分PDF，创建了 {len(files_created)} 个文件",
                files_created=files_created,
                barcodes_found=len(all_barcodes),
                pages_processed=total_pages,
                output_dir=output_dir
            )
            
        except Exception as e:
            logger.error(f"PDF条码拆分失败: {e}")
            return SplitResult(
                success=False,
                message=f"拆分过程中发生错误: {str(e)}",
                files_created=[],
                barcodes_found=0,
                pages_processed=0
            )
    
    def _create_split_file(self, doc: fitz.Document, barcodes: List[BarcodeInfo], 
                          config: BarcodeSplitConfig, output_dir: str, 
                          index: int) -> Optional[str]:
        """
        创建拆分后的PDF文件
        
        Args:
            doc: 原始PDF文档
            barcodes: 条码信息列表
            config: 配置
            output_dir: 输出目录
            index: 索引（用于命名）
            
        Returns:
            创建的文件路径，失败返回None
        """
        try:
            if not barcodes:
                return None
            
            # 获取需要拆分的页面范围
            pages_to_extract = set()
            for barcode in barcodes:
                pages_to_extract.add(barcode.page_num)
            
            # 创建新的PDF文档
            new_doc = fitz.open()
            
            # 复制页面
            for page_num in sorted(pages_to_extract):
                new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
            
            # 生成文件名
            barcode_data = barcodes[0].data
            filename = config.output_config.get_filename(barcode_data, index)
            filename = f"{filename}.pdf"
            
            # 确保文件名唯一
            file_path = os.path.join(output_dir, filename)
            counter = 1
            while os.path.exists(file_path):
                name, ext = os.path.splitext(filename)
                file_path = os.path.join(output_dir, f"{name}_{counter}{ext}")
                counter += 1
            
            # 保存文件
            new_doc.save(file_path)
            new_doc.close()
            
            logger.debug(f"创建拆分文件: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"创建拆分文件失败: {e}")
            return None
    
    def _group_and_merge_barcodes_combine_mode(self, doc: fitz.Document, barcodes: List[BarcodeInfo], 
                                             config: BarcodeSplitConfig, output_dir: str) -> List[str]:
        """
        Combine模式实现：相同条码的页面合并为一组，无条码页面附加到前一组
        
        规则：无条码则追加，条码相同全部合併
        
        示例：
        頁1: 無條碼  
        頁2: 條碼A  
        頁3: 條碼A  
        頁4: 無條碼  
        頁5: 條碼B  
        頁6: 條碼A  
        頁7: 條碼A  
        頁8: 無條碼 
        
        合并规则：
        • 無條碼組：第1頁(無條碼) 獨立一組，生成文件 無條碼.pdf
        • 條碼A組：第2頁(條碼A), 第3頁(條碼A), 第4頁(無條碼), 第6頁(條碼A), 第7頁(條碼A), 第8頁(無條碼) 全部合併，生成文件 條碼A.pdf
        • 條碼B組：第5頁(條碼B) 獨立一組，生成文件 條碼B.pdf
        """
        try:
            files_created = []
            total_pages = len(doc)
            
            # 构建页面到条码的映射
            page_barcode_map = {}
            for barcode in barcodes:
                if barcode.page_num not in page_barcode_map:
                    page_barcode_map[barcode.page_num] = []
                page_barcode_map[barcode.page_num].append(barcode)
            
            # 存储每个条码值对应的页面列表，按首次出现顺序排列
            barcode_groups = {}
            # 存储尚未分配的无条码页面
            unassigned_pages = []
            # 当前活跃组（最新处理的条码组）
            active_group_barcode = None
            
            # 遍历所有页面
            for page_num in range(total_pages):
                if page_num in page_barcode_map and page_barcode_map[page_num]:
                    # 当前页面有条码
                    barcode_value = page_barcode_map[page_num][0].data.strip()
                    logger.debug(f"第{page_num + 1}页条码值: {barcode_value}")
                    
                    if barcode_value in barcode_groups:
                        # 该条码组已存在，将累积的无条码页面添加到该组
                        barcode_groups[barcode_value].extend(unassigned_pages)
                        unassigned_pages.clear()
                    else:
                        # 首次出现该条码，创建新组
                        barcode_groups[barcode_value] = []
                        logger.debug(f"第{page_num + 1}页出现新条码，创建新组: {barcode_value}")
                    
                    # 将当前页面添加到对应条码组
                    barcode_groups[barcode_value].append(page_num)
                    # 更新活跃组
                    active_group_barcode = barcode_value
                else:
                    # 当前页面无条码
                    if active_group_barcode is not None:
                        # 已有活跃组，将无条码页面添加到活跃组
                        barcode_groups[active_group_barcode].append(page_num)
                    else:
                        # 尚无活跃组（还未遇到任何条码），暂存无条码页面
                        unassigned_pages.append(page_num)
            
            # 处理开头的无条码页面组（如果有的话）
            if unassigned_pages:
                # 创建无条码组文件
                new_doc = fitz.open()
                for page_num in unassigned_pages:
                    new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
                
                # 生成文件名
                filename = "无条码.pdf"
                file_path = os.path.join(output_dir, filename)
                counter = 1
                while os.path.exists(file_path):
                    name, ext = os.path.splitext(filename)
                    file_path = os.path.join(output_dir, f"{name}_{counter}{ext}")
                    counter += 1
                
                # 保存文件
                new_doc.save(file_path)
                new_doc.close()
                files_created.append(file_path)
                logger.debug(f"创建无条码组文件: {file_path}，共{len(unassigned_pages)}页")
            
            # 跟踪每个条码值的文件计数
            barcode_file_counts = {}
            
            # 保存所有条码组
            for barcode_value, pages in barcode_groups.items():
                if pages:
                    # 创建新的PDF文档
                    new_doc = fitz.open()
                    
                    # 复制页面
                    for page_num in pages:
                    	new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
                    
                    # 为当前条码值增加计数
                    if barcode_value not in barcode_file_counts:
                        barcode_file_counts[barcode_value] = 0
                    barcode_file_counts[barcode_value] += 1
                    file_count = barcode_file_counts[barcode_value]
                    
                    # 生成文件名
                    filename = config.output_config.get_filename(barcode_value, file_count - 1)
                    filename = f"{filename}.pdf"
                    file_path = os.path.join(output_dir, filename)
                    counter = 1
                    while os.path.exists(file_path):
                        name, ext = os.path.splitext(filename)
                        file_path = os.path.join(output_dir, f"{name}_{counter}{ext}")
                        counter += 1
                    
                    # 保存文件
                    new_doc.save(file_path)
                    new_doc.close()
                    files_created.append(file_path)
                    logger.debug(f"创建条码组文件: {file_path}，{barcode_value}共{len(pages)}页")
            
            return files_created
            
        except Exception as e:
            logger.error(f"Combine模式条码分组合并失败: {e}")
            return []
    
    def _group_and_merge_barcodes_filename_mode(self, doc: fitz.Document, barcodes: List[BarcodeInfo], 
                                              config: BarcodeSplitConfig, output_dir: str) -> List[str]:
        """
        Filename模式实现：每个有条码的页面独立成组，无条码页面附加到前一组
        
        规则：无条码则追加，不合併
        
        示例：
        頁1: 無條碼 
        頁2: 條碼A  
        頁3: 條碼A  
        頁4: 無條碼 
        頁5: 條碼B  
        頁6: 條碼A  
        頁7: 條碼A  
        頁8: 無條碼
        
        合并规则：
        • 分組1：第1頁(無條碼) ，源文件.pdf
        • 分組2：第2頁(條碼A),條碼A_001.pdf 
        • 分組3：第3頁(條碼A),第4頁(無條碼 ),條碼A_002.pdf
        • 分組4：第5頁(條碼B)  條碼B_001.pdf 
        • 分組5：第6頁(條碼A) 條碼A_003.pdf 
        • 分組6：第7頁(條碼A),第8頁(無條碼 ) 條碼A_004.pdf 
        """
        try:
            files_created = []
            total_pages = len(doc)
            
            # 构建页面到条码的映射
            page_barcode_map = {}
            for barcode in barcodes:
                if barcode.page_num not in page_barcode_map:
                    page_barcode_map[barcode.page_num] = []
                page_barcode_map[barcode.page_num].append(barcode)
            
            # 跟踪每个条码值的文件计数
            barcode_file_counts = {}
            
            # 当前组的页面
            current_group = []
            current_barcode = None
            
            # 遍历所有页面
            for page_num in range(total_pages):
                if page_num in page_barcode_map and page_barcode_map[page_num]:
                    # 当前页面有条码
                    barcode_value = page_barcode_map[page_num][0].data.strip()
                    logger.debug(f"第{page_num + 1}页条码值: {barcode_value}")
                    
                    # 如果当前组已经有内容且条码值不同，则保存当前组
                    if current_barcode is not None and current_barcode != barcode_value:
                        # 保存当前组
                        if current_group:
                            new_doc = fitz.open()
                            for p in current_group:
                                new_doc.insert_pdf(doc, from_page=p, to_page=p)
                            
                            # 为当前条码值增加计数
                            if current_barcode not in barcode_file_counts:
                                barcode_file_counts[current_barcode] = 0
                            barcode_file_counts[current_barcode] += 1
                            file_count = barcode_file_counts[current_barcode]
                            
                            # 生成文件名
                            filename = f"{current_barcode}_{file_count:03d}.pdf"
                            file_path = os.path.join(output_dir, filename)
                            counter = 1
                            while os.path.exists(file_path):
                                name, ext = os.path.splitext(filename)
                                file_path = os.path.join(output_dir, f"{name}_{counter}{ext}")
                                counter += 1
                            
                            # 保存文件
                            new_doc.save(file_path)
                            new_doc.close()
                            files_created.append(file_path)
                            logger.debug(f"创建条码组文件: {file_path}，共{len(current_group)}页")
                            
                            current_group.clear()
                    
                    # 将当前页面添加到当前组
                    current_group.append(page_num)
                    current_barcode = barcode_value
                else:
                    # 当前页面无条码，将其添加到当前组
                    current_group.append(page_num)
            
            # 处理最后一组
            if current_group:
                if current_barcode:
                    # 有条码的组
                    new_doc = fitz.open()
                    for page_num in current_group:
                        new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
                    
                    # 为当前条码值增加计数
                    if current_barcode not in barcode_file_counts:
                        barcode_file_counts[current_barcode] = 0
                    barcode_file_counts[current_barcode] += 1
                    file_count = barcode_file_counts[current_barcode]
                    
                    # 生成文件名
                    filename = f"{current_barcode}_{file_count:03d}.pdf"
                    file_path = os.path.join(output_dir, filename)
                    counter = 1
                    while os.path.exists(file_path):
                        name, ext = os.path.splitext(filename)
                        file_path = os.path.join(output_dir, f"{name}_{counter}{ext}")
                        counter += 1
                    
                    # 保存文件
                    new_doc.save(file_path)
                    new_doc.close()
                    files_created.append(file_path)
                    logger.debug(f"创建条码组文件: {file_path}，共{len(current_group)}页")
                else:
                    # 无条码的组（开头的无条码页面）
                    new_doc = fitz.open()
                    for page_num in current_group:
                        new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
                    
                    # 生成文件名
                    filename = "源文件.pdf"
                    file_path = os.path.join(output_dir, filename)
                    counter = 1
                    while os.path.exists(file_path):
                        name, ext = os.path.splitext(filename)
                        file_path = os.path.join(output_dir, f"{name}_{counter}{ext}")
                        counter += 1
                    
                    # 保存文件
                    new_doc.save(file_path)
                    new_doc.close()
                    files_created.append(file_path)
                    logger.debug(f"创建无条码组文件: {file_path}，共{len(current_group)}页")
            
            return files_created
            
        except Exception as e:
            logger.error(f"Filename模式条码分组合并失败: {e}")
            return []
    
    def _create_split_files_for_multi_barcodes(self, doc: fitz.Document, barcodes: List[BarcodeInfo], 
                                              config: BarcodeSplitConfig, output_dir: str) -> List[str]:
        """
        为多条码页面创建拆分文件（一页属于多个文档）
        
        Args:
            doc: 原始PDF文档
            barcodes: 条码信息列表
            config: 配置
            output_dir: 输出目录
            
        Returns:
            创建的文件路径列表
        """
        try:
            files_created = []
            
            # 按页面分组条码
            page_groups = {}
            for barcode in barcodes:
                if barcode.page_num not in page_groups:
                    page_groups[barcode.page_num] = []
                page_groups[barcode.page_num].append(barcode)
            
            # 为每个条码创建对应的文件
            barcode_file_map = {}  # 记录每个条码对应的文件
            
            for page_num, barcodes_on_page in page_groups.items():
                # 对于每一页上的每个条码，都要复制该页面到对应的文档中
                for i, barcode in enumerate(barcodes_on_page):
                    if barcode.data not in barcode_file_map:
                        barcode_file_map[barcode.data] = []
                    
                    # 根据重复处理模式决定处理方式
                    if config.output_config.duplicate_handling == "merge":
                        # 合并模式：检查是否已经有该条码的文件
                        existing_entry = None
                        for entry in barcode_file_map[barcode.data]:
                            if page_num not in entry['pages']:
                                existing_entry = entry
                                break
                        
                        if existing_entry:
                            # 添加页面到现有条目
                            existing_entry['pages'].add(page_num)
                            existing_entry['barcodes'].append(barcode)
                        else:
                            # 创建新条目
                            barcode_file_map[barcode.data].append({
                                'pages': {page_num},
                                'barcodes': [barcode]
                            })
                    else:
                        # 分离模式：为每个条码创建单独条目
                        barcode_file_map[barcode.data].append({
                            'pages': {page_num},
                            'barcodes': [barcode]
                        })
            
            # 创建实际的文件
            created_files = []
            barcode_index = 0
            for barcode_data, entries in barcode_file_map.items():
                barcode_index += 1
                for i, entry in enumerate(entries):
                    pages = entry['pages']
                    barcodes_for_file = entry['barcodes']
                    
                    # 创建新的PDF文档
                    new_doc = fitz.open()
                    
                    # 复制页面
                    for page_num in sorted(pages):
                        new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
                    
                    # 生成文件名
                    filename = config.output_config.get_filename(barcode_data, i)
                    filename = f"{filename}.pdf"
                    
                    # 确保文件名唯一
                    file_path = os.path.join(output_dir, filename)
                    counter = 1
                    while os.path.exists(file_path):
                        name, ext = os.path.splitext(filename)
                        file_path = os.path.join(output_dir, f"{name}_{counter}{ext}")
                        counter += 1
                    
                    # 保存文件
                    new_doc.save(file_path)
                    new_doc.close()
                    
                    created_files.append(file_path)
                    logger.debug(f"创建拆分文件: {file_path}")
            
            return created_files
            
        except Exception as e:
            logger.error(f"创建多条码拆分文件失败: {e}")
            return []
    
    def preview_split(self, pdf_path: str, config: BarcodeSplitConfig) -> Dict:
        """
        预览拆分结果（不实际拆分）
        
        Args:
            pdf_path: PDF文件路径
            config: 拆分配置
            
        Returns:
            预览信息字典
        """
        try:
            if not os.path.exists(pdf_path):
                return {"error": "PDF文件不存在"}
            
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            
            # 配置检测器
            enabled_types = config.filter_config.enabled_types
            logger.debug(f"配置检测器(预览)，原始启用类型: {enabled_types}")
            # 特殊处理：如果只选择了ALL_TYPES，需要展开为所有具体类型
            if len(enabled_types) == 1 and enabled_types[0] == "ALL_TYPES":
                enabled_types = list(self.detector.BARCODE_TYPES.keys())
                logger.debug(f"展开ALL_TYPES为具体类型: {enabled_types}")
            self.detector.set_enabled_types(enabled_types)
            
            # 检测条码
            # 使用both方法同时检测嵌入图片和渲染页面中的条码
            def page_progress_callback(current, total, message):
                if progress_callback:
                    # 将页面进度映射到总体进度(15-30%)
                    overall_percent = 15 + int((current / total) * 15)
                    progress_callback(overall_percent, message)
            
            if progress_callback:
                progress_callback(15, "正在检测条码...")
            all_barcodes = self.detector.detect_barcodes_in_document(doc, method="both", progress_callback=page_progress_callback)
            
            # 过滤条码
            filtered_barcodes = self.detector.filter_barcodes(
                all_barcodes,
                min_length=config.filter_config.min_length,
                max_length=config.filter_config.max_length,
                include_keywords=config.filter_config.include_keywords,
                exclude_keywords=config.filter_config.exclude_keywords,
                include_regex=config.filter_config.include_regex,
                exclude_regex=config.filter_config.exclude_regex
            )
            
            # 分组
            barcode_groups = self.detector.group_barcodes_by_data(filtered_barcodes)
            
            # 生成文件名预览
            preview_groups = []
            
            # 根据多条码处理模式决定预览方式
            if config.output_config.multi_barcode_handling == "duplicate_page":
                # 一页属于多个文档模式
                all_barcodes = []
                for barcode_list in barcode_groups.values():
                    all_barcodes.extend(barcode_list)
                
                # 按页面分组条码
                page_groups = {}
                for barcode in all_barcodes:
                    if barcode.page_num not in page_groups:
                        page_groups[barcode.page_num] = []
                    page_groups[barcode.page_num].append(barcode)
                
                # 为每个条码生成预览
                barcode_file_map = {}
                for page_num, barcodes_on_page in page_groups.items():
                    for i, barcode in enumerate(barcodes_on_page):
                        if barcode.data not in barcode_file_map:
                            barcode_file_map[barcode.data] = []
                        
                        if config.output_config.duplicate_handling == "merge":
                            # 合并模式
                            existing_entry = None
                            for entry in barcode_file_map[barcode.data]:
                                if page_num not in entry['pages']:
                                    existing_entry = entry
                                    break
                            
                            if existing_entry:
                                existing_entry['pages'].add(page_num)
                            else:
                                barcode_file_map[barcode.data].append({
                                    'pages': {page_num},
                                    'barcodes': [barcode]
                                })
                        else:
                            # 分离模式
                            barcode_file_map[barcode.data].append({
                                'pages': {page_num},
                                'barcodes': [barcode]
                            })
                
                # 生成预览
                file_index = 0
                for barcode_data, entries in barcode_file_map.items():
                    for entry in entries:
                        pages = sorted(entry['pages'])
                        filename = config.output_config.get_filename(barcode_data, file_index) + ".pdf"
                        preview_groups.append({
                            "barcode": barcode_data,
                            "filename": filename,
                            "pages": [p + 1 for p in pages],  # 转换为1基索引
                            "page_count": len(pages)
                        })
                        file_index += 1
            else:
                # 默认模式
                for barcode_data, barcode_list in barcode_groups.items():
                    pages = sorted(set(barcode.page_num for barcode in barcode_list))
                    
                    if config.output_config.duplicate_handling == "merge":
                        # 合并模式
                        filename = config.output_config.get_filename(barcode_data, 0) + ".pdf"
                        preview_groups.append({
                            "barcode": barcode_data,
                            "filename": filename,
                            "pages": [p + 1 for p in pages],  # 转换为1基索引
                            "page_count": len(pages)
                        })
                    else:
                        # 分离模式
                        for i, barcode in enumerate(barcode_list):
                            filename = config.output_config.get_filename(barcode_data, i) + ".pdf"
                            preview_groups.append({
                                "barcode": barcode_data,
                                "filename": filename,
                                "pages": [barcode.page_num + 1],  # 转换为1基索引
                                "page_count": 1
                            })
            
            doc.close()
            
            return {
                "total_pages": total_pages,
                "total_barcodes": len(all_barcodes),
                "filtered_barcodes": len(filtered_barcodes),
                "groups": len(barcode_groups),
                "output_files": len(preview_groups),
                "preview": preview_groups
            }
            
        except Exception as e:
            logger.error(f"预览拆分结果失败: {e}")
            return {"error": f"预览失败: {str(e)}"}
    
    def _cleanup(self):
        """清理临时资源"""
        try:
            # 清理缓存等
            pass
        except Exception as e:
            logger.warning(f"清理资源时出现警告: {e}")


# 便捷函数
def split_pdf_by_barcodes(pdf_path: str, config: BarcodeSplitConfig, 
                         progress_callback: Optional[Callable] = None) -> SplitResult:
    """
    便捷函数：根据条码拆分PDF
    
    Args:
        pdf_path: PDF文件路径
        config: 拆分配置
        progress_callback: 进度回调函数
        
    Returns:
        拆分结果
    """
    processor = BarcodeSplitProcessor()
    return processor.split_pdf(pdf_path, config, progress_callback)