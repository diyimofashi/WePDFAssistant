"""条码检测器模块"""

import fitz
from PIL import Image, ImageEnhance, ImageFilter
import io
import base64
import re
from typing import List, Dict, Optional, Tuple, Callable
from app.utils.logger import get_logger

logger = get_logger('barcode_detector')


class BarcodeInfo:
    """条码信息类"""
    
    def __init__(self, data: str, barcode_type: str, rect: Tuple[int, int, int, int], 
                 quality: int, page_num: int):
        self.data = data
        self.type = barcode_type
        self.rect = rect  # (left, top, width, height)
        self.quality = quality
        self.page_num = page_num
    
    def __str__(self):
        return f"Barcode(data='{self.data}', type='{self.type}', page={self.page_num})"


class BarcodeDetector:
    """条码检测器 - 负责从PDF页面中检测条码"""
    
    # 支持的条码类型映射
    BARCODE_TYPES = {
        'QRCODE': 'QRCODE',
        'CODE128': 'CODE128',
        'CODE39': 'CODE39',
        'CODE93': 'CODE93',
        'CODABAR': 'CODABAR',
        'EAN13': 'EAN13',
        'EAN8': 'EAN8',
        'EAN2': 'EAN2',
        'EAN5': 'EAN5',
        'UPCA': 'UPCA',
        'UPCE': 'UPCE',
        'DATABAR': 'DATABAR',
        'DATABAR_EXP': 'DATABAR_EXP',
        'PDF417': 'PDF417',
        'I25': 'I25',  # Interleaved 2 of 5
        'ISBN10': 'ISBN10',
        'ISBN13': 'ISBN13',
        'SQCODE': 'SQCODE',
        'COMPOSITE': 'COMPOSITE'
    }
    
    def __init__(self):
        """初始化条码检测器"""
        self.enabled_types = ['QRCODE', 'CODE128', 'EAN13', 'CODE39', 'PDF417', 'CODE93', 'I25', 'UPCA', 'UPCE']
        logger.debug(f"条码检测器初始化，启用类型: {self.enabled_types}")
    
    def detect_barcodes_in_page(self, doc: fitz.Document, page_num: int, 
                              dpi: int = 300, method: str = "both") -> List[BarcodeInfo]:
        """
        检测指定页面中的所有条码
        
        Args:
            doc: PyMuPDF文档对象
            page_num: 页码（从0开始）
            dpi: 渲染DPI
            method: 处理方法 "embedded" (仅嵌入图片), "render" (仅渲染页面), "both" (两者都使用)
            
        Returns:
            条码信息列表
        """
        try:
            logger.debug(f"开始检测第{page_num + 1}页的条码，当前启用的条码类型: {self.enabled_types}，方法: {method}")
            
            # 获取页面
            page = doc[page_num]
            all_barcodes = []
            
            # 方法1: 提取页面中的嵌入图片 (默认使用)
            if method in ["embedded", "both"]:
                logger.debug(f"提取第{page_num + 1}页中的嵌入图片进行条码检测")
                embedded_barcodes = self._detect_barcodes_in_embedded_images(doc, page, page_num)
                all_barcodes.extend(embedded_barcodes)
                logger.debug(f"从嵌入图片中检测到 {len(embedded_barcodes)} 个条码")
            
            # 方法2: 将整个页面渲染为图像并识别 (仅在指定时使用)
            if method in ["render", "both"]:
                # 使用多种DPI进行检测以提高识别率
                dpi_values = [dpi, 200, 150] if dpi > 200 else [dpi]
                processed_images = set()
                
                for current_dpi in dpi_values:
                    logger.debug(f"使用DPI {current_dpi} 渲染第{page_num + 1}页")
                    # 将页面渲染为图像
                    mat = fitz.Matrix(current_dpi / 72, current_dpi / 72)
                    pix = page.get_pixmap(matrix=mat)
                    
                    # 将图像数据转换为PIL图像
                    img_data = pix.tobytes("ppm")
                    image = Image.open(io.BytesIO(img_data))
                    
                    # 计算图像哈希以避免重复处理相同的图像
                    image_hash = hash(image.tobytes())
                    if method == "both" and any(barcode.page_num == page_num for barcode in all_barcodes):
                        logger.debug(f"跳过重复图像处理，DPI: {current_dpi}，因为已通过嵌入图片检测到条码")
                        continue
                    elif image_hash in processed_images:
                        logger.debug(f"跳过重复图像处理，DPI: {current_dpi}")
                        continue
                    processed_images.add(image_hash)
                    
                    # 预处理图像
                    processed_image = self._preprocess_image(image)
                    
                    # 检测条码
                    barcodes = self._detect_barcodes_in_image(processed_image, page_num)
                    
                    logger.debug(f"在DPI {current_dpi} 下检测到 {len(barcodes)} 个条码")
                    
                    # 合并结果，避免重复
                    for barcode in barcodes:
                        # 检查是否已存在相同数据和位置的条码
                        is_duplicate = False
                        for existing in all_barcodes:
                            if (existing.data == barcode.data and 
                                abs(existing.rect[0] - barcode.rect[0]) < 10 and
                                abs(existing.rect[1] - barcode.rect[1]) < 10):
                                is_duplicate = True
                                break
                        
                        if not is_duplicate:
                            all_barcodes.append(barcode)
                            logger.debug(f"新增条码: {barcode.data} (类型: {barcode.type})")
            
            logger.debug(f"第{page_num + 1}页总共检测到 {len(all_barcodes)} 个条码")
            return all_barcodes
            
        except Exception as e:
            logger.error(f"检测第{page_num + 1}页条码时出错: {e}")
            return []
    
    def detect_barcodes_in_document(self, doc: fitz.Document, 
                                 page_range: Optional[str] = None,
                                 method: str = "both",
                                 progress_callback: Optional[Callable] = None,
                                 cancel_flag: Optional[Callable] = None) -> List[BarcodeInfo]:
        """
        检测文档中所有页面的条码
        
        Args:
            doc: PyMuPDF文档对象
            page_range: 页面范围，如 "1-5,7,9-10"，None表示全部页面
            method: 处理方法 "embedded" (仅嵌入图片), "render" (仅渲染页面), "both" (两者都使用)
            progress_callback: 进度回调函数 (current, total, message) -> None
            cancel_flag: 取消标志回调函数 () -> bool，如果返回True则取消操作
            
        Returns:
            条码信息列表
        """
        try:
            total_pages = len(doc)
            page_indices = self._parse_page_range(page_range, total_pages)
            
            logger.debug(f"开始检测文档条码，总页数: {total_pages}，检测范围: {page_indices}，方法: {method}")
            
            all_barcodes = []
            for i, page_num in enumerate(page_indices):
                # 检查是否需要取消
                if cancel_flag and cancel_flag():
                    return all_barcodes
                    
                if progress_callback:
                    progress_callback(i + 1, len(page_indices), f"正在检测第 {page_num + 1} 页条码...")
                barcodes = self.detect_barcodes_in_page(doc, page_num, method=method)
                all_barcodes.extend(barcodes)
            
            return all_barcodes
            
        except Exception as e:
            logger.error(f"检测文档条码时出错: {e}")
            return []
    
    def _detect_barcodes_in_image(self, image: Image.Image, page_num: int) -> List[BarcodeInfo]:
        """在图像中检测条码"""
        try:
            logger.debug(f"开始在第{page_num + 1}页图像中检测条码，启用的类型: {self.enabled_types}")
            
            # 创建多个预处理版本的图像以提高识别率
            processed_images = self._create_processed_images(image)
            
            all_barcodes = []
            
            # 对每个预处理图像尝试检测
            for i, processed_image in enumerate(processed_images):
                logger.debug(f"正在使用预处理图像 {i+1}/{len(processed_images)} 进行条码检测")
                
                # 首先尝试使用pyzbar，针对启用的条码类型
                pyzbar_success = False
                try:
                    try:
                        from pyzbar.pyzbar import decode as pyzbar_decode, ZBarSymbol
                    except ImportError:
                        pyzbar_decode = None
                        ZBarSymbol = None
                        raise
                    
                    # 如果启用了所有类型，则不指定符号类型
                    if "ALL_TYPES" in self.enabled_types or len(self.enabled_types) == len(self.BARCODE_TYPES):
                        logger.debug("使用pyzbar检测所有类型条码")
                        codes = pyzbar_decode(processed_image)
                    else:
                        # 转换启用的类型为ZBarSymbol
                        symbols = []
                        type_mapping = {
                            'QRCODE': ZBarSymbol.QRCODE,
                            'CODE128': ZBarSymbol.CODE128,
                            'CODE39': ZBarSymbol.CODE39,
                            'CODE93': ZBarSymbol.CODE93,
                            'CODABAR': ZBarSymbol.CODABAR,
                            'EAN13': ZBarSymbol.EAN13,
                            'EAN8': ZBarSymbol.EAN8,
                            'EAN2': ZBarSymbol.EAN2,
                            'EAN5': ZBarSymbol.EAN5,
                            'UPCA': ZBarSymbol.UPCA,
                            'UPCE': ZBarSymbol.UPCE,
                            'DATABAR': ZBarSymbol.DATABAR,
                            'DATABAR_EXP': ZBarSymbol.DATABAR_EXP,
                            'PDF417': ZBarSymbol.PDF417,
                            'I25': ZBarSymbol.I25,
                            'ISBN10': ZBarSymbol.ISBN10,
                            'ISBN13': ZBarSymbol.ISBN13,
                            'SQCODE': ZBarSymbol.SQCODE,
                            'COMPOSITE': ZBarSymbol.COMPOSITE
                        }
                        
                        for type_name in self.enabled_types:
                            if type_name in type_mapping:
                                symbols.append(type_mapping[type_name])
                        
                        logger.debug(f"使用pyzbar检测指定类型条码: {symbols}")
                        codes = pyzbar_decode(processed_image, symbols=symbols) if symbols else pyzbar_decode(processed_image)
                    
                    barcodes = []
                    for c in codes:
                        barcode_info = BarcodeInfo(
                            data=c.data.decode("utf-8", errors="replace"),
                            barcode_type=c.type,
                            rect=(c.rect.left, c.rect.top, c.rect.width, c.rect.height),
                            quality=getattr(c, 'quality', 100),
                            page_num=page_num
                        )
                        barcodes.append(barcode_info)
                        logger.debug(f"pyzbar检测到条码: {barcode_info}")
                    
                    # 合并结果，避免重复
                    for barcode in barcodes:
                        if not any(existing.data == barcode.data and 
                                  abs(existing.rect[0] - barcode.rect[0]) < 10 and
                                  abs(existing.rect[1] - barcode.rect[1]) < 10 
                                  for existing in all_barcodes):
                            all_barcodes.append(barcode)
                    
                    if barcodes:
                        pyzbar_success = True
                        
                except ImportError:
                    logger.debug("pyzbar不可用")
                except Exception as e:
                    logger.debug(f"pyzbar检测失败: {e}")
                
                # 如果pyzbar没有检测到条码，尝试使用zxingcpp
                if not pyzbar_success:
                    try:
                        import zxingcpp
                        logger.debug("尝试使用zxingcpp检测条码")
                        codes = zxingcpp.read_barcodes(processed_image)
                        
                        barcodes = []
                        for c in codes:
                            if c.valid:
                                # 转换格式名称
                                format_name = c.format.name if hasattr(c.format, 'name') else str(c.format)
                                barcode_info = BarcodeInfo(
                                    data=c.text if hasattr(c, 'text') and c.text else "",
                                    barcode_type=format_name,
                                    rect=(
                                        int(c.position.top_left.x),
                                        int(c.position.top_left.y),
                                        int(c.position.bottom_right.x - c.position.top_left.x),
                                        int(c.position.bottom_right.y - c.position.top_left.y)
                                    ),
                                    quality=100,
                                    page_num=page_num
                                )
                                barcodes.append(barcode_info)
                                logger.debug(f"zxingcpp检测到条码: {barcode_info}")
                        
                        # 合并结果，避免重复
                        for barcode in barcodes:
                            if not any(existing.data == barcode.data and 
                                      abs(existing.rect[0] - barcode.rect[0]) < 10 and
                                      abs(existing.rect[1] - barcode.rect[1]) < 10 
                                      for existing in all_barcodes):
                                all_barcodes.append(barcode)
                        
                    except ImportError:
                        logger.debug("zxingcpp不可用")
                    except Exception as e:
                        logger.debug(f"zxingcpp检测失败: {e}")
                else:
                    logger.debug(f"pyzbar已检测到 {len([b for b in all_barcodes if any(b.data == barcode.data for barcode in barcodes)])} 个条码")
            
            if all_barcodes:
                logger.debug(f"总共检测到 {len(all_barcodes)} 个条码")
                for barcode in all_barcodes:
                    logger.debug(f"检测到的条码: {barcode.data} (类型: {barcode.type}, 页码: {barcode.page_num})")
                return all_barcodes
            else:
                logger.warning(f"第{page_num + 1}页没有检测到条码")
                return []
                
        except Exception as e:
            logger.error(f"图像条码检测出错: {e}")
            return []
    
    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """图像预处理 - 返回最佳质量的图像"""
        try:
            # 确保图像是RGB模式以减少zbar警告
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # 返回原始图像
            return image
        except Exception as e:
            logger.warning(f"图像预处理失败: {e}")
            return image
    
    def _detect_barcodes_in_embedded_images(self, doc: fitz.Document, page: fitz.Page, page_num: int) -> List[BarcodeInfo]:
        """检测页面中嵌入图片的条码"""
        try:
            barcodes = []
            
            # 获取页面中的所有图片
            image_list = page.get_images()
            logger.debug(f"第{page_num + 1}页找到 {len(image_list)} 个嵌入图片")
            
            # 遍历页面中的所有图片
            for img_index, img in enumerate(image_list):
                try:
                    xref = img[0]
                    # 提取图片
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    
                    # 使用PIL打开图片
                    img_obj = Image.open(io.BytesIO(image_bytes))
                    
                    # 确保图像是RGB模式以减少zbar警告
                    if img_obj.mode != 'RGB':
                        img_obj = img_obj.convert('RGB')
                    
                    # 对图片进行预处理
                    processed_img = self._preprocess_image(img_obj)
                    
                    # 检测条码
                    image_barcodes = self._detect_barcodes_in_image(processed_img, page_num)
                    barcodes.extend(image_barcodes)
                    
                    if image_barcodes:
                        logger.debug(f"从第{page_num + 1}页的嵌入图片 #{img_index + 1} 中检测到 {len(image_barcodes)} 个条码")
                    
                except Exception as e:
                    logger.debug(f"处理第{page_num + 1}页的嵌入图片 #{img_index + 1} 时出错: {e}")
                    continue
            
            return barcodes
            
        except Exception as e:
            logger.warning(f"检测嵌入图片条码时出错: {e}")
            return []
    
    def _create_processed_images(self, image: Image.Image) -> List[Image.Image]:
        """创建多种预处理版本的图像以提高识别率"""
        try:
            # 确保图像是RGB模式以减少zbar警告
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            processed_images = []
            
            # 原始图像
            processed_images.append(image.copy())
            
            # 灰度图像（通常对条码识别最有效）
            gray_image = image.convert('L').convert('RGB')
            processed_images.append(gray_image)
            
            # 适度的对比度增强（避免过度处理）
            try:
                # 增强对比度
                enhancer = ImageEnhance.Contrast(gray_image)
                contrast_image = enhancer.enhance(1.3)  # 增加30%对比度
                processed_images.append(contrast_image)
                
                # 轻微锐化
                sharpness_enhancer = ImageEnhance.Sharpness(gray_image)
                sharp_image = sharpness_enhancer.enhance(1.2)  # 增加20%锐度
                processed_images.append(sharp_image)
                
            except Exception as enhance_error:
                logger.debug(f"图像增强失败: {enhance_error}")
            
            # 去重：移除完全相同的图像
            unique_images = []
            seen_hashes = set()
            
            for img in processed_images:
                img_hash = hash(img.tobytes())
                if img_hash not in seen_hashes:
                    seen_hashes.add(img_hash)
                    unique_images.append(img)
            
            logger.debug(f"生成了 {len(unique_images)} 个不同的预处理图像")
            return unique_images
            
        except Exception as e:
            logger.warning(f"创建预处理图像失败: {e}")
            # 至少返回原始图像
            return [image]
    
    def filter_barcodes(self, barcodes: List[BarcodeInfo], 
                       min_length: int = 1, max_length: int = 1000,
                       include_keywords: List[str] = None,
                       exclude_keywords: List[str] = None,
                       include_regex: str = "",
                       exclude_regex: str = "") -> List[BarcodeInfo]:
        """
        根据规则过滤条码
        
        Args:
            barcodes: 条码信息列表
            min_length: 最小长度
            max_length: 最大长度
            include_keywords: 必须包含的关键词列表
            exclude_keywords: 必须排除的关键词列表
            include_regex: 必须匹配的正则表达式
            exclude_regex: 必须排除的正则表达式
            
        Returns:
            过滤后的条码列表
        """
        try:
            filtered = []
            
            # 编译正则表达式以提高性能
            include_pattern = None
            exclude_pattern = None
            
            if include_regex:
                try:
                    include_pattern = re.compile(include_regex, re.IGNORECASE)
                except Exception as e:
                    logger.warning(f"编译包含正则表达式失败: {e}")
            
            if exclude_regex:
                try:
                    exclude_pattern = re.compile(exclude_regex, re.IGNORECASE)
                except Exception as e:
                    logger.warning(f"编译排除正则表达式失败: {e}")
            
            for barcode in barcodes:
                # 长度过滤
                if len(barcode.data) < min_length or len(barcode.data) > max_length:
                    logger.debug(f"条码长度不符合: {barcode.data} (长度: {len(barcode.data)})")
                    continue
                
                # 包含关键词过滤
                if include_keywords:
                    if not any(keyword.lower() in barcode.data.lower() for keyword in include_keywords):
                        logger.debug(f"条码不包含指定关键词: {barcode.data}")
                        continue
                
                # 排除关键词过滤
                if exclude_keywords:
                    if any(keyword.lower() in barcode.data.lower() for keyword in exclude_keywords):
                        logger.debug(f"条码包含排除关键词: {barcode.data}")
                        continue
                
                # 包含正则表达式过滤
                if include_pattern:
                    if not include_pattern.search(barcode.data):
                        logger.debug(f"条码不匹配包含正则表达式: {barcode.data}")
                        continue
                
                # 排除正则表达式过滤
                if exclude_pattern:
                    if exclude_pattern.search(barcode.data):
                        logger.debug(f"条码匹配排除正则表达式: {barcode.data}")
                        continue
                
                filtered.append(barcode)
            
            logger.debug(f"条码过滤完成，从 {len(barcodes)} 个过滤到 {len(filtered)} 个")
            return filtered
            
        except Exception as e:
            logger.error(f"过滤条码时出错: {e}")
            return barcodes
    
    def group_barcodes_by_data(self, barcodes: List[BarcodeInfo]) -> Dict[str, List[BarcodeInfo]]:
        """
        按条码内容分组
        
        Args:
            barcodes: 条码信息列表
            
        Returns:
            按条码内容分组的字典 {条码数据: [条码信息列表]}
        """
        try:
            groups = {}
            for barcode in barcodes:
                if barcode.data not in groups:
                    groups[barcode.data] = []
                groups[barcode.data].append(barcode)
            
            logger.debug(f"条码分组完成，共 {len(groups)} 个不同条码值")
            return groups
            
        except Exception as e:
            logger.error(f"条码分组时出错: {e}")
            return {}
    
    def group_barcodes_by_page(self, barcodes: List[BarcodeInfo]) -> Dict[int, List[BarcodeInfo]]:
        """
        按页面分组条码
        
        Args:
            barcodes: 条码信息列表
            
        Returns:
            按页面分组的字典 {页码: [条码信息列表]}
        """
        try:
            groups = {}
            for barcode in barcodes:
                if barcode.page_num not in groups:
                    groups[barcode.page_num] = []
                groups[barcode.page_num].append(barcode)
            
            logger.debug(f"条码按页面分组完成，共 {len(groups)} 个不同页面")
            return groups
            
        except Exception as e:
            logger.error(f"条码按页面分组时出错: {e}")
            return {}
    
    def set_enabled_types(self, types: List[str]):
        """
        设置启用的条码类型
        
        Args:
            types: 条码类型列表，包含 "ALL_TYPES" 表示启用所有类型
        """
        logger.debug(f"设置启用的条码类型: {types}")
        if "ALL_TYPES" in types:
            # 启用所有类型
            self.enabled_types = list(self.BARCODE_TYPES.keys())
            logger.debug(f"启用所有条码类型: {self.enabled_types}")
        elif len(types) == 1 and types[0] == "ALL_TYPES":
            # 特殊情况：只有ALL_TYPES一项
            self.enabled_types = list(self.BARCODE_TYPES.keys())
            logger.debug(f"启用所有条码类型: {self.enabled_types}")
        else:
            valid_types = [t for t in types if t in self.BARCODE_TYPES]
            if valid_types:
                self.enabled_types = valid_types
                logger.debug(f"更新启用条码类型: {self.enabled_types}")
            elif not types:
                logger.warning("未选择任何条码类型")
            else:
                logger.warning(f"无效的条码类型: {types}")
    
    def get_supported_types(self) -> List[str]:
        """获取支持的条码类型列表（包含"所有类型"选项）"""
        return ["ALL_TYPES"] + list(self.BARCODE_TYPES.keys())
    
    def _parse_page_range(self, page_range: Optional[str], total_pages: int) -> List[int]:
        """
        解析页面范围字符串
        
        Args:
            page_range: 页面范围字符串，如 "1-5,7,9-10"
            total_pages: 总页数
            
        Returns:
            页码索引列表（从0开始）
        """
        if not page_range:
            return list(range(total_pages))
        
        try:
            pages = set()
            for part in page_range.split(','):
                part = part.strip()
                if '-' in part:
                    start, end = part.split('-')
                    start, end = int(start) - 1, int(end) - 1  # 转换为0索引
                    start = max(0, min(start, total_pages - 1))
                    end = max(0, min(end, total_pages - 1))
                    pages.update(range(start, end + 1))
                else:
                    page = int(part) - 1  # 转换为0索引
                    if 0 <= page < total_pages:
                        pages.add(page)
            
            return sorted(list(pages))
            
        except Exception as e:
            logger.warning(f"解析页面范围失败: {page_range}, 使用全部页面")
            return list(range(total_pages))


# 便捷函数
def detect_barcodes(pdf_path: str, page_range: Optional[str] = None) -> List[BarcodeInfo]:
    """
    便捷函数：检测PDF文件中的条码
    
    Args:
        pdf_path: PDF文件路径
        page_range: 页面范围
        
    Returns:
        条码信息列表
    """
    try:
        doc = fitz.open(pdf_path)
        detector = BarcodeDetector()
        barcodes = detector.detect_barcodes_in_document(doc, page_range)
        doc.close()
        return barcodes
    except Exception as e:
        logger.error(f"检测PDF条码失败: {e}")
        return []