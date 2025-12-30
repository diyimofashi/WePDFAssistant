"""
条码插件模板API实现
这是一个示例插件，展示如何实现条码插件接口
"""

import base64
import os
import fitz  # PyMuPDF
from io import BytesIO
from typing import Dict, List, Any, Union
from PIL import Image
import pyzbar.pyzbar as pyzbar
from pyzbar.wrapper import ZBarSymbol
from app.core.barcode.barcode_plugin_interface import BarcodePluginInterface, BarcodeResult, BarcodeErrorCode


class BarcodePluginTemplate(BarcodePluginInterface):
    """条码插件模板实现"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化插件
        
        Args:
            config: 插件配置参数
        """
        super().__init__()
        self.plugin_name = "barcode_template"
        self.plugin_version = "1.0.0"
        self.plugin_author = "Aurora PDF"
        self.config = config or {}
        
        # 初始化插件特定的配置项
        self.enabled_types = self.config.get('enabled_types', ['ALL_TYPES'])
        self.min_length = self.config.get('min_length', 1)
        self.max_length = self.config.get('max_length', 1000)
        self.include_keywords = self.config.get('include_keywords', [])
        self.exclude_keywords = self.config.get('exclude_keywords', [])
        self.include_regex = self.config.get('include_regex', '')
        self.exclude_regex = self.config.get('exclude_regex', '')
        self.duplicate_handling = self.config.get('duplicate_handling', 'merge')
        self.multi_barcode_handling = self.config.get('multi_barcode_handling', 'first')
        self.output_dir = self.config.get('output_dir', '')
        self.use_barcode_filename = self.config.get('use_barcode_filename', True)
        self.filename_template = self.config.get('filename_template', '{barcode}_{index}')
        self.enable_rotation = self.config.get('enable_rotation', True)
        self.max_barcode_count = self.config.get('max_barcode_count', 100)
        self.min_confidence = self.config.get('min_confidence', 0.5)
        
        self.is_initialized = False
    
    def initialize(self, config: Dict[str, Any]) -> BarcodeResult:
        """
        初始化插件
        
        Args:
            config: 插件配置参数
            
        Returns:
            BarcodeResult: 初始化结果
        """
        try:
            self.config.update(config)
            
            # 更新插件特定的配置项
            self.enabled_types = self.config.get('enabled_types', ['ALL_TYPES'])
            self.min_length = self.config.get('min_length', 1)
            self.max_length = self.config.get('max_length', 1000)
            self.include_keywords = self.config.get('include_keywords', [])
            self.exclude_keywords = self.config.get('exclude_keywords', [])
            self.include_regex = self.config.get('include_regex', '')
            self.exclude_regex = self.config.get('exclude_regex', '')
            self.duplicate_handling = self.config.get('duplicate_handling', 'merge')
            self.multi_barcode_handling = self.config.get('multi_barcode_handling', 'first')
            self.output_dir = self.config.get('output_dir', '')
            self.use_barcode_filename = self.config.get('use_barcode_filename', True)
            self.filename_template = self.config.get('filename_template', '{barcode}_{index}')
            self.enable_rotation = self.config.get('enable_rotation', True)
            self.max_barcode_count = self.config.get('max_barcode_count', 100)
            self.min_confidence = self.config.get('min_confidence', 0.5)
            
            self.is_initialized = True
            return BarcodeResult(
                code=BarcodeErrorCode.SUCCESS,
                message="插件初始化成功"
            )
        except Exception as e:
            return BarcodeResult(
                code=BarcodeErrorCode.INIT_ERROR,
                message=f"插件初始化失败: {str(e)}"
            )
    
    def detect_from_file(self, file_path: str) -> BarcodeResult:
        """
        从文件路径检测条码
        
        Args:
            file_path: 图片文件路径
            
        Returns:
            BarcodeResult: 检测结果
        """
        try:
            if not self.is_initialized:
                return BarcodeResult(
                    code=BarcodeErrorCode.INIT_ERROR,
                    message="插件未初始化"
                )
            
            # 检查文件是否存在
            if not file_path or not os.path.exists(file_path):
                return BarcodeResult(
                    code=BarcodeErrorCode.FILE_NOT_FOUND,
                    message=f"文件不存在: {file_path}"
                )
            
            # 使用PIL打开图片
            image = Image.open(file_path)
            
            # 转换为RGB模式（如果需要）
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # 使用pyzbar检测条码
            barcodes = pyzbar.decode(image)

            # 确保数值类型的配置项是正确的类型
            max_count = self.config.get('max_barcode_count', 100)
            try:
                max_count = int(max_count)
            except (ValueError, TypeError):
                max_count = 100

            min_length = self.config.get('min_length', 1)
            try:
                min_length = int(min_length)
            except (ValueError, TypeError):
                min_length = 1

            max_length = self.config.get('max_length', 1000)
            try:
                max_length = int(max_length)
            except (ValueError, TypeError):
                max_length = 1000

            # 根据配置限制条码数量
            barcodes = barcodes[:max_count]

            # 根据配置过滤条码
            filtered_barcodes = []
            include_keywords = self.config.get('include_keywords', [])
            exclude_keywords = self.config.get('exclude_keywords', [])
            include_regex = self.config.get('include_regex', '')
            exclude_regex = self.config.get('exclude_regex', '')

            for barcode in barcodes:
                try:
                    barcode_data_str = barcode.data.decode('utf-8')
                except Exception:
                    continue

                # 确保barcode_data_str是字符串类型
                if not isinstance(barcode_data_str, str):
                    try:
                        barcode_data_str = str(barcode_data_str)
                    except Exception:
                        continue

                # 长度过滤（确保所有比较都是int vs int或str vs str）
                barcode_len = len(barcode_data_str)
                if barcode_len < min_length or barcode_len > max_length:
                    continue
                
                # 包含关键词过滤
                if include_keywords:
                    if not any(keyword.lower() in barcode_data_str.lower() for keyword in include_keywords):
                        continue
                
                # 排除关键词过滤
                if exclude_keywords:
                    if any(keyword.lower() in barcode_data_str.lower() for keyword in exclude_keywords):
                        continue
                
                # 包含正则表达式过滤
                if include_regex:
                    import re
                    try:
                        if not re.search(include_regex, barcode_data_str):
                            continue
                    except re.error:
                        # 正则表达式错误，跳过
                        continue
                
                # 排除正则表达式过滤
                if exclude_regex:
                    import re
                    try:
                        if re.search(exclude_regex, barcode_data_str):
                            continue
                    except re.error:
                        # 正则表达式错误，跳过
                        continue
                
                filtered_barcodes.append(barcode)
            
            # 格式化检测结果
            results = []
            for barcode in filtered_barcodes:
                barcode_data = {
                    "data": barcode.data.decode('utf-8'),
                    "type": barcode.type,
                    "bbox": [
                        barcode.rect.left,
                        barcode.rect.top,
                        barcode.rect.left + barcode.rect.width,
                        barcode.rect.top + barcode.rect.height
                    ],
                    "confidence": 1.0,  # pyzbar不提供置信度，设为1.0
                    "page_num": 0  # 单页图片
                }
                results.append(barcode_data)
            
            return BarcodeResult(
                code=BarcodeErrorCode.SUCCESS,
                data=results,
                message=f"检测到 {len(results)} 个条码"
            )
            
        except Exception as e:
            return BarcodeResult(
                code=BarcodeErrorCode.DETECTION_FAILED,
                message=f"从文件检测条码失败: {str(e)}"
            )
    
    def detect_from_bytes(self, image_bytes: bytes) -> BarcodeResult:
        """
        从字节流检测条码
        
        Args:
            image_bytes: 图片字节流
            
        Returns:
            BarcodeResult: 检测结果
        """
        try:
            if not self.is_initialized:
                return BarcodeResult(
                    code=BarcodeErrorCode.INIT_ERROR,
                    message="插件未初始化"
                )
            
            # 从字节流创建图片
            image = Image.open(BytesIO(image_bytes))
            
            # 转换为RGB模式（如果需要）
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # 使用pyzbar检测条码
            barcodes = pyzbar.decode(image)

            # 确保数值类型的配置项是正确的类型
            max_count = self.config.get('max_barcode_count', 100)
            try:
                max_count = int(max_count)
            except (ValueError, TypeError):
                max_count = 100

            min_length = self.config.get('min_length', 1)
            try:
                min_length = int(min_length)
            except (ValueError, TypeError):
                min_length = 1

            max_length = self.config.get('max_length', 1000)
            try:
                max_length = int(max_length)
            except (ValueError, TypeError):
                max_length = 1000

            # 根据配置限制条码数量
            barcodes = barcodes[:max_count]

            # 根据配置过滤条码
            filtered_barcodes = []
            include_keywords = self.config.get('include_keywords', [])
            exclude_keywords = self.config.get('exclude_keywords', [])
            include_regex = self.config.get('include_regex', '')
            exclude_regex = self.config.get('exclude_regex', '')

            for barcode in barcodes:
                try:
                    barcode_data_str = barcode.data.decode('utf-8')
                except Exception:
                    continue

                # 确保barcode_data_str是字符串类型
                if not isinstance(barcode_data_str, str):
                    try:
                        barcode_data_str = str(barcode_data_str)
                    except Exception:
                        continue

                # 长度过滤（确保所有比较都是int vs int或str vs str）
                barcode_len = len(barcode_data_str)
                if barcode_len < min_length or barcode_len > max_length:
                    continue
                
                # 包含关键词过滤
                if include_keywords:
                    if not any(keyword.lower() in barcode_data_str.lower() for keyword in include_keywords):
                        continue
                
                # 排除关键词过滤
                if exclude_keywords:
                    if any(keyword.lower() in barcode_data_str.lower() for keyword in exclude_keywords):
                        continue
                
                # 包含正则表达式过滤
                if include_regex:
                    import re
                    try:
                        if not re.search(include_regex, barcode_data_str):
                            continue
                    except re.error:
                        # 正则表达式错误，跳过
                        continue
                
                # 排除正则表达式过滤
                if exclude_regex:
                    import re
                    try:
                        if re.search(exclude_regex, barcode_data_str):
                            continue
                    except re.error:
                        # 正则表达式错误，跳过
                        continue
                
                filtered_barcodes.append(barcode)
            
            # 格式化检测结果
            results = []
            for barcode in filtered_barcodes:
                barcode_data = {
                    "data": barcode.data.decode('utf-8'),
                    "type": barcode.type,
                    "bbox": [
                        barcode.rect.left,
                        barcode.rect.top,
                        barcode.rect.left + barcode.rect.width,
                        barcode.rect.top + barcode.rect.height
                    ],
                    "confidence": 1.0,  # pyzbar不提供置信度，设为1.0
                    "page_num": 0  # 单页图片
                }
                results.append(barcode_data)
            
            return BarcodeResult(
                code=BarcodeErrorCode.SUCCESS,
                data=results,
                message=f"检测到 {len(results)} 个条码"
            )
            
        except Exception as e:
            return BarcodeResult(
                code=BarcodeErrorCode.DETECTION_FAILED,
                message=f"从字节流检测条码失败: {str(e)}"
            )
    
    def detect_from_base64(self, base64_string: str) -> BarcodeResult:
        """
        从Base64字符串检测条码
        
        Args:
            base64_string: Base64编码的图片字符串
            
        Returns:
            BarcodeResult: 检测结果
        """
        try:
            if not self.is_initialized:
                return BarcodeResult(
                    code=BarcodeErrorCode.INIT_ERROR,
                    message="插件未初始化"
                )
            
            # 解码Base64字符串
            image_bytes = base64.b64decode(base64_string)
            
            # 从字节流创建图片
            image = Image.open(BytesIO(image_bytes))
            
            # 转换为RGB模式（如果需要）
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # 使用pyzbar检测条码
            barcodes = pyzbar.decode(image)

            # 确保数值类型的配置项是正确的类型
            max_count = self.config.get('max_barcode_count', 100)
            try:
                max_count = int(max_count)
            except (ValueError, TypeError):
                max_count = 100

            min_length = self.config.get('min_length', 1)
            try:
                min_length = int(min_length)
            except (ValueError, TypeError):
                min_length = 1

            max_length = self.config.get('max_length', 1000)
            try:
                max_length = int(max_length)
            except (ValueError, TypeError):
                max_length = 1000

            # 根据配置限制条码数量
            barcodes = barcodes[:max_count]

            # 根据配置过滤条码
            filtered_barcodes = []
            include_keywords = self.config.get('include_keywords', [])
            exclude_keywords = self.config.get('exclude_keywords', [])
            include_regex = self.config.get('include_regex', '')
            exclude_regex = self.config.get('exclude_regex', '')

            for barcode in barcodes:
                try:
                    barcode_data_str = barcode.data.decode('utf-8')
                except Exception:
                    continue

                # 确保barcode_data_str是字符串类型
                if not isinstance(barcode_data_str, str):
                    try:
                        barcode_data_str = str(barcode_data_str)
                    except Exception:
                        continue

                # 长度过滤（确保所有比较都是int vs int或str vs str）
                barcode_len = len(barcode_data_str)
                if barcode_len < min_length or barcode_len > max_length:
                    continue
                
                # 包含关键词过滤
                if include_keywords:
                    if not any(keyword.lower() in barcode_data_str.lower() for keyword in include_keywords):
                        continue
                
                # 排除关键词过滤
                if exclude_keywords:
                    if any(keyword.lower() in barcode_data_str.lower() for keyword in exclude_keywords):
                        continue
                
                # 包含正则表达式过滤
                if include_regex:
                    import re
                    try:
                        if not re.search(include_regex, barcode_data_str):
                            continue
                    except re.error:
                        # 正则表达式错误，跳过
                        continue
                
                # 排除正则表达式过滤
                if exclude_regex:
                    import re
                    try:
                        if re.search(exclude_regex, barcode_data_str):
                            continue
                    except re.error:
                        # 正则表达式错误，跳过
                        continue
                
                filtered_barcodes.append(barcode)
            
            # 格式化检测结果
            results = []
            for barcode in filtered_barcodes:
                barcode_data = {
                    "data": barcode.data.decode('utf-8'),
                    "type": barcode.type,
                    "bbox": [
                        barcode.rect.left,
                        barcode.rect.top,
                        barcode.rect.left + barcode.rect.width,
                        barcode.rect.top + barcode.rect.height
                    ],
                    "confidence": 1.0,  # pyzbar不提供置信度，设为1.0
                    "page_num": 0  # 单页图片
                }
                results.append(barcode_data)
            
            return BarcodeResult(
                code=BarcodeErrorCode.SUCCESS,
                data=results,
                message=f"检测到 {len(results)} 个条码"
            )
            
        except Exception as e:
            return BarcodeResult(
                code=BarcodeErrorCode.DETECTION_FAILED,
                message=f"从Base64字符串检测条码失败: {str(e)}"
            )
    
    def get_supported_types(self) -> List[str]:
        """
        获取支持的条码类型列表
        
        Returns:
            List[str]: 支持的条码类型标识列表
        """
        # pyzbar支持的条码类型
        return [
            'CODE128', 'CODE39', 'CODE93', 'CODABAR',
            'EAN13', 'EAN8', 'EAN5', 'EAN2',
            'UPCA', 'UPCE',
            'I25', 'DATABAR', 'DATABAR_EXP',
            'PDF417', 'QR'
        ]
    
    def detect_from_pdf(self, doc: 'fitz.Document', config: Dict[str, Any] = None) -> BarcodeResult:
        """
        从PDF文档检测条码
        
        Args:
            doc: PyMuPDF文档对象
            config: 检测配置参数
            
        Returns:
            BarcodeResult: 检测结果
        """
        try:
            if not self.is_initialized:
                return BarcodeResult(
                    code=BarcodeErrorCode.INIT_ERROR,
                    message="插件未初始化"
                )

            # 使用增强的检测方法
            if config is None:
                config = {}
            
            all_barcodes = self._detect_barcodes_in_document_enhanced(doc, config)
            
            # 转换为标准格式
            results = []
            for barcode in all_barcodes:
                barcode_data = {
                    "data": barcode.data,
                    "type": barcode.type,
                    "bbox": [
                        barcode.rect.left,
                        barcode.rect.top,
                        barcode.rect.left + barcode.rect.width,
                        barcode.rect.top + barcode.rect.height
                    ],
                    "confidence": 1.0,
                    "page_num": barcode.page_num
                }
                results.append(barcode_data)

            if results:
                return BarcodeResult(
                    code=BarcodeErrorCode.SUCCESS,
                    data=results,
                    message=f"在PDF中检测到 {len(results)} 个条码"
                )
            else:
                return BarcodeResult(
                    code=BarcodeErrorCode.SUCCESS,
                    data=[],
                    message="未在PDF中检测到条码"
                )

        except Exception as e:
            return BarcodeResult(
                code=BarcodeErrorCode.DETECTION_FAILED,
                message=f"从PDF文档检测条码失败: {str(e)}"
            )
    
    def split_document_by_barcodes_with_progress(self, 
                                 doc: fitz.Document, 
                                 output_dir: str, 
                                 config: Dict[str, Any] = None,
                                 progress_callback=None) -> Dict[str, Any]:
        """
        根据条码拆分PDF文档（带进度反馈）
        
        Args:
            doc: PyMuPDF文档对象
            output_dir: 输出目录
            config: 拆分配置参数
            progress_callback: 进度回调函数
            
        Returns:
            Dict[str, Any]: 拆分结果
        """
        try:
            if not self.is_initialized:
                return {
                    "success": False,
                    "message": "插件未初始化",
                    "files_created": [],
                    "barcodes_found": 0,
                    "pages_processed": 0
                }
            
            # 使用插件自己的拆分逻辑
            return self._split_document_with_plugin_logic(doc, output_dir, config, progress_callback)
            
        except Exception as e:
            return {
                "success": False,
                "message": f"拆分文档时发生错误: {str(e)}",
                "files_created": [],
                "barcodes_found": 0,
                "pages_processed": 0
            }

    def _split_document_with_plugin_logic(self, doc: fitz.Document, output_dir: str, config: Dict[str, Any] = None, progress_callback=None) -> Dict[str, Any]:
        """
        插件自己的拆分逻辑实现
        
        Args:
            doc: PyMuPDF文档对象
            output_dir: 输出目录
            config: 拆分配置参数
            progress_callback: 进度回调函数
            
        Returns:
            拆分结果字典
        """
        try:
            import os

            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)

            # 检测文档中的所有条码
            if progress_callback:
                if not progress_callback(10, 100, "正在检测条码..."):
                    return {
                        "success": False,
                        "message": "用户取消了操作",
                        "files_created": [],
                        "barcodes_found": 0,
                        "pages_processed": 0
                    }

            # 使用插件配置
            if config is None:
                config = {}

            total_pages = len(doc)

            # 检测条码 - 使用多种方法提高识别率
            all_barcodes = self._detect_barcodes_in_document_enhanced(doc, config)

            total_barcodes = len(all_barcodes)

            if progress_callback:
                if not progress_callback(30, 100, f"检测到 {total_barcodes} 个条码，正在过滤..."):
                    return {
                        "success": False,
                        "message": "用户取消了操作",
                        "files_created": [],
                        "barcodes_found": 0,
                        "pages_processed": 0
                    }

            # 过滤条码
            filtered_barcodes = self._filter_barcodes(all_barcodes, config)

            if not filtered_barcodes:
                return {
                    "success": False,
                    "message": "没有找到符合条件的条码",
                    "files_created": [],
                    "barcodes_found": total_barcodes,
                    "pages_processed": total_pages
                }

            if progress_callback:
                if not progress_callback(40, f"过滤后剩余 {len(filtered_barcodes)} 个条码，正在分组..."):
                    return {
                        "success": False,
                        "message": "用户取消了操作",
                        "files_created": [],
                        "barcodes_found": total_barcodes,
                        "pages_processed": total_pages
                    }

            # 根据重复处理模式决定拆分策略
            duplicate_handling = config.get('duplicate_handling', 'merge')
            multi_barcode_handling = config.get('multi_barcode_handling', 'first')

            files_created = []

            if progress_callback:
                if not progress_callback(50, f"准备拆分为 {len(filtered_barcodes)} 个组..."):
                    return {
                        "success": False,
                        "message": "用户取消了操作",
                        "files_created": [],
                        "barcodes_found": total_barcodes,
                        "pages_processed": total_pages
                    }

            # 根据处理模式拆分
            if duplicate_handling == "merge":
                # 合并模式：使用Combine模式
                files_created = self._split_by_combine_mode(doc, filtered_barcodes, config, output_dir, progress_callback)
            else:
                # 分离模式：使用Filename模式
                files_created = self._split_by_filename_mode(doc, filtered_barcodes, config, output_dir, progress_callback)

            if progress_callback:
                if not progress_callback(100, 100, "拆分完成"):
                    return {
                        "success": False,
                        "message": "用户取消了操作",
                        "files_created": files_created,
                        "barcodes_found": total_barcodes,
                        "pages_processed": total_pages
                    }

            return {
                "success": True,
                "message": f"成功拆分PDF，创建了 {len(files_created)} 个文件",
                "files_created": files_created,
                "barcodes_found": total_barcodes,
                "pages_processed": total_pages
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"插件拆分逻辑出错: {str(e)}",
                "files_created": [],
                "barcodes_found": 0,
                "pages_processed": 0
            }

    def _detect_barcodes_in_document_enhanced(self, doc: fitz.Document, config: Dict[str, Any]) -> List[Any]:
        """
        使用增强方法检测文档中的所有条码
        
        Args:
            doc: PyMuPDF文档对象
            config: 配置参数
            
        Returns:
            条码信息列表
        """
        try:
            all_barcodes = []
            total_pages = len(doc)
            
            # 使用多个DPI值以提高识别率
            dpi_values = [300, 200, 150]
            
            for page_num in range(total_pages):
                page = doc[page_num]
                page_barcodes = set()  # 使用集合避免重复
                
                # 方法1: 检测嵌入图片中的条码
                embedded_barcodes = self._detect_barcodes_in_embedded_images(doc, page, page_num)
                for barcode in embedded_barcodes:
                    key = (barcode.data, barcode.page_num)
                    if key not in page_barcodes:
                        page_barcodes.add(key)
                        all_barcodes.append(barcode)
                
                # 方法2: 渲染页面检测
                for dpi in dpi_values:
                    mat = fitz.Matrix(dpi / 72, dpi / 72)
                    pix = page.get_pixmap(matrix=mat)
                    img_data = pix.tobytes("ppm")
                    img = Image.open(BytesIO(img_data))
                    
                    # 确保是RGB模式
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # 使用pyzbar检测条码
                    codes = pyzbar.decode(img)
                    
                    for code in codes:
                        try:
                            barcode_data_str = code.data.decode('utf-8', errors='replace')
                            
                            # 检查是否已经检测到过
                            key = (barcode_data_str, page_num)
                            if key not in page_barcodes:
                                # 创建条码信息对象
                                class BarcodeInfo:
                                    def __init__(self, data, type, rect, page_num):
                                        self.data = data
                                        self.type = type
                                        self.rect = rect
                                        self.page_num = page_num
                                
                                barcode = BarcodeInfo(
                                    data=barcode_data_str,
                                    type=code.type,
                                    rect=code.rect,
                                    page_num=page_num
                                )
                                page_barcodes.add(key)
                                all_barcodes.append(barcode)
                        except Exception:
                            pass
                
                # 限制每页的条码数量
                max_barcodes_per_page = config.get('max_barcode_count', 100)
                if len([b for b in all_barcodes if b.page_num == page_num]) >= max_barcodes_per_page:
                    break
            
            return all_barcodes
        except Exception:
            return []

    def _detect_barcodes_in_embedded_images(self, doc: fitz.Document, page: fitz.Page, page_num: int) -> List[Any]:
        """
        检测页面中嵌入图片的条码
        
        Args:
            doc: PyMuPDF文档对象
            page: 页面对象
            page_num: 页码
            
        Returns:
            条码信息列表
        """
        try:
            barcodes = []
            image_list = page.get_images()
            
            for img_index, img in enumerate(image_list):
                try:
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    
                    img_obj = Image.open(BytesIO(image_bytes))
                    if img_obj.mode != 'RGB':
                        img_obj = img_obj.convert('RGB')
                    
                    # 使用pyzbar检测
                    codes = pyzbar.decode(img_obj)
                    
                    for code in codes:
                        try:
                            barcode_data_str = code.data.decode('utf-8', errors='replace')
                            
                            class BarcodeInfo:
                                def __init__(self, data, type, rect, page_num):
                                    self.data = data
                                    self.type = type
                                    self.rect = rect
                                    self.page_num = page_num
                            
                            barcode = BarcodeInfo(
                                data=barcode_data_str,
                                type=code.type,
                                rect=code.rect,
                                page_num=page_num
                            )
                            barcodes.append(barcode)
                        except Exception:
                            pass
                except Exception:
                    continue
            
            return barcodes
        except Exception:
            return []

    def _filter_barcodes(self, barcodes: List[Any], config: Dict[str, Any]) -> List[Any]:
        """
        过滤条码
        
        Args:
            barcodes: 条码列表
            config: 配置参数
            
        Returns:
            过滤后的条码列表
        """
        try:
            # 获取过滤参数
            min_length = config.get('min_length', 1)
            try:
                min_length = int(min_length)
            except (ValueError, TypeError):
                min_length = 1

            max_length = config.get('max_length', 1000)
            try:
                max_length = int(max_length)
            except (ValueError, TypeError):
                max_length = 1000

            max_barcode_count = config.get('max_barcode_count', 100)
            try:
                max_barcode_count = int(max_barcode_count)
            except (ValueError, TypeError):
                max_barcode_count = 100

            include_keywords = config.get('include_keywords', [])
            exclude_keywords = config.get('exclude_keywords', [])
            include_regex = config.get('include_regex', '')
            exclude_regex = config.get('exclude_regex', '')

            filtered_barcodes = []
            for barcode in barcodes:
                barcode_data_str = barcode.data
                
                # 确保是字符串
                if not isinstance(barcode_data_str, str):
                    try:
                        barcode_data_str = str(barcode_data_str)
                    except Exception:
                        continue

                # 长度过滤
                barcode_len = len(barcode_data_str)
                if barcode_len < min_length or barcode_len > max_length:
                    continue

                # 包含关键词过滤
                if include_keywords:
                    if not any(keyword.lower() in barcode_data_str.lower() for keyword in include_keywords):
                        continue

                # 排除关键词过滤
                if exclude_keywords:
                    if any(keyword.lower() in barcode_data_str.lower() for keyword in exclude_keywords):
                        continue

                # 包含正则表达式过滤
                if include_regex:
                    import re
                    try:
                        if not re.search(include_regex, barcode_data_str):
                            continue
                    except re.error:
                        pass

                # 排除正则表达式过滤
                if exclude_regex:
                    import re
                    try:
                        if re.search(exclude_regex, barcode_data_str):
                            continue
                    except re.error:
                        pass

                filtered_barcodes.append(barcode)
                
                # 检查是否达到最大条码数量
                if len(filtered_barcodes) >= max_barcode_count:
                    break

            return filtered_barcodes
        except Exception:
            return []

    def _split_by_combine_mode(self, doc: fitz.Document, barcodes: List[Any], 
                              config: Dict[str, Any], output_dir: str, 
                              progress_callback=None) -> List[str]:
        """
        Combine模式拆分：相同条码的页面合并为一组，无条码页面附加到前一组
        
        Args:
            doc: PDF文档
            barcodes: 条码列表
            config: 配置
            output_dir: 输出目录
            progress_callback: 进度回调
            
        Returns:
            创建的文件列表
        """
        try:
            import os
            files_created = []
            total_pages = len(doc)
            
            # 构建页面到条码的映射
            page_barcode_map = {}
            for barcode in barcodes:
                if barcode.page_num not in page_barcode_map:
                    page_barcode_map[barcode.page_num] = []
                page_barcode_map[barcode.page_num].append(barcode)
            
            # 存储每个条码值对应的页面列表
            barcode_groups = {}
            # 存储尚未分配的无条码页面
            unassigned_pages = []
            # 当前活跃组
            active_group_barcode = None
            
            # 遍历所有页面
            for page_num in range(total_pages):
                if page_num in page_barcode_map and page_barcode_map[page_num]:
                    # 当前页面有条码
                    barcode_value = page_barcode_map[page_num][0].data.strip()
                    
                    if barcode_value in barcode_groups:
                        # 该条码组已存在，将累积的无条码页面添加到该组
                        barcode_groups[barcode_value].extend(unassigned_pages)
                        unassigned_pages.clear()
                    else:
                        # 首次出现该条码，创建新组
                        barcode_groups[barcode_value] = []
                    
                    # 将当前页面添加到对应条码组
                    barcode_groups[barcode_value].append(page_num)
                    active_group_barcode = barcode_value
                else:
                    # 当前页面无条码
                    if active_group_barcode is not None:
                        # 已有活跃组，将无条码页面添加到活跃组
                        barcode_groups[active_group_barcode].append(page_num)
                    else:
                        # 尚无活跃组，暂存无条码页面
                        unassigned_pages.append(page_num)
            
            # 处理开头的无条码页面
            if unassigned_pages:
                new_doc = fitz.open()
                for page_num in unassigned_pages:
                    new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
                
                filename = "无条码.pdf"
                file_path = os.path.join(output_dir, filename)
                counter = 1
                while os.path.exists(file_path):
                    name, ext = os.path.splitext(filename)
                    file_path = os.path.join(output_dir, f"{name}_{counter}{ext}")
                    counter += 1
                
                new_doc.save(file_path)
                new_doc.close()
                files_created.append(file_path)
            
            # 保存所有条码组
            barcode_file_counts = {}
            file_index = 0
            for barcode_value, pages in list(barcode_groups.items()):
                if pages:
                    new_doc = fitz.open()
                    for page_num in pages:
                        new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
                    
                    if barcode_value not in barcode_file_counts:
                        barcode_file_counts[barcode_value] = 0
                    barcode_file_counts[barcode_value] += 1
                    file_count = barcode_file_counts[barcode_value]
                    
                    # 生成文件名
                    filename_template = config.get('filename_template', '{barcode}_{index}')
                    clean_barcode = self._clean_filename(barcode_value)
                    formatted_index = f"{file_count:03d}"
                    filename = filename_template.format(
                        barcode=clean_barcode,
                        index=formatted_index
                    )
                    filename = f"{filename}.pdf"
                    
                    file_path = os.path.join(output_dir, filename)
                    counter = 1
                    while os.path.exists(file_path):
                        name, ext = os.path.splitext(filename)
                        file_path = os.path.join(output_dir, f"{name}_{counter}{ext}")
                        counter += 1
                    
                    new_doc.save(file_path)
                    new_doc.close()
                    files_created.append(file_path)
                    
                    # 更新进度
                    if progress_callback:
                        progress = 50 + int(((file_index + 1) / len(barcode_groups)) * 50)
                        if not progress_callback(progress, 100, f"已创建 {file_index + 1}/{len(barcode_groups)} 个文件"):
                            break
                    
                    file_index += 1
            
            return files_created
        except Exception:
            return []

    def _split_by_filename_mode(self, doc: fitz.Document, barcodes: List[Any],
                              config: Dict[str, Any], output_dir: str,
                              progress_callback=None) -> List[str]:
        """
        Filename模式拆分：每个有条码的页面独立成组，无条码页面附加到前一组

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
        • 分組1：第1頁(無條碼)，源文件.pdf
        • 分組2：第2頁(條碼A)，條碼A_001.pdf
        • 分組3：第3頁(條碼A), 第4頁(無條碼)，條碼A_002.pdf
        • 分組4：第5頁(條碼B)，條碼B_001.pdf
        • 分組5：第6頁(條碼A)，條碼A_003.pdf
        • 分組6：第7頁(條碼A), 第8頁(無條碼)，條碼A_004.pdf

        Args:
            doc: PDF文档
            barcodes: 条码列表
            config: 配置
            output_dir: 输出目录
            progress_callback: 进度回调

        Returns:
            创建的文件列表
        """
        try:
            import os
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
                            filename_template = config.get('filename_template', '{barcode}_{index}')
                            clean_barcode = self._clean_filename(current_barcode)
                            formatted_index = f"{file_count:03d}"
                            filename = filename_template.format(
                                barcode=clean_barcode,
                                index=formatted_index
                            )
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
                    filename_template = config.get('filename_template', '{barcode}_{index}')
                    clean_barcode = self._clean_filename(current_barcode)
                    formatted_index = f"{file_count:03d}"
                    filename = filename_template.format(
                        barcode=clean_barcode,
                        index=formatted_index
                    )
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

                    # 更新进度
                    if progress_callback:
                        progress = 50 + int((len(files_created) / max(1, len(files_created))) * 50)
                        if not progress_callback(progress, 100, f"已创建 {len(files_created)} 个文件"):
                            pass
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

                    # 更新进度
                    if progress_callback:
                        progress = 50 + int((len(files_created) / max(1, len(files_created))) * 50)
                        if not progress_callback(progress, 100, f"已创建 {len(files_created)} 个文件"):
                            pass

            return files_created
        except Exception:
            return []

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

    def split_document_by_barcodes(self, 
                                 doc: fitz.Document, 
                                 output_dir: str, 
                                 config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        根据条码拆分PDF文档（使用系统已有的功能）
        
        Args:
            doc: PyMuPDF文档对象
            output_dir: 输出目录
            config: 拆分配置参数
            
        Returns:
            Dict[str, Any]: 拆分结果
        """
        try:
            if not self.is_initialized:
                return {
                    "success": False,
                    "message": "插件未初始化",
                    "files_created": [],
                    "barcodes_found": 0,
                    "pages_processed": 0
                }
            
            # 使用插件自己的拆分逻辑
            return self._split_document_with_plugin_logic(doc, output_dir, config, None)
            
        except Exception as e:
            return {
                "success": False,
                "message": f"拆分文档时发生错误: {str(e)}",
                "files_created": [],
                "barcodes_found": 0,
                "pages_processed": 0
            }

    def preview_split_result(self, 
                            doc: fitz.Document, 
                            config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        预览拆分结果
        
        Args:
            doc: PyMuPDF文档对象
            config: 拆分配置参数
            
        Returns:
            Dict[str, Any]: 预览结果
        """
        try:
            if not self.is_initialized:
                return {
                    "error": "插件未初始化"
                }

            # 使用插件配置
            if config is None:
                config = {}

            total_pages = len(doc)

            # 使用增强的检测方法
            all_barcodes = self._detect_barcodes_in_document_enhanced(doc, config)

            # 过滤条码
            filtered_barcodes = self._filter_barcodes(all_barcodes, config)

            if not filtered_barcodes:
                return {
                    "total_pages": total_pages,
                    "total_barcodes": len(all_barcodes),
                    "filtered_barcodes": 0,
                    "groups": 0,
                    "output_files": 0,
                    "preview": []
                }

            # 根据处理模式预览分组
            duplicate_handling = config.get('duplicate_handling', 'merge')

            if duplicate_handling == "merge":
                preview_groups = self._preview_combine_mode(doc, filtered_barcodes, config)
            else:
                preview_groups = self._preview_filename_mode(doc, filtered_barcodes, config)

            return {
                "total_pages": total_pages,
                "total_barcodes": len(all_barcodes),
                "filtered_barcodes": len(filtered_barcodes),
                "groups": len(preview_groups),
                "output_files": len(preview_groups),
                "preview": preview_groups
            }

        except Exception as e:
            return {
                "error": f"预览拆分结果时发生错误: {str(e)}"
            }

    def _preview_combine_mode(self, doc: fitz.Document, barcodes: List[Any], config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """预览Combine模式的拆分结果"""
        try:
            total_pages = len(doc)
            
            # 构建页面到条码的映射
            page_barcode_map = {}
            for barcode in barcodes:
                if barcode.page_num not in page_barcode_map:
                    page_barcode_map[barcode.page_num] = []
                page_barcode_map[barcode.page_num].append(barcode)
            
            # 存储每个条码值对应的页面列表
            barcode_groups = {}
            # 存储尚未分配的无条码页面
            unassigned_pages = []
            # 当前活跃组
            active_group_barcode = None
            
            # 遍历所有页面
            for page_num in range(total_pages):
                if page_num in page_barcode_map and page_barcode_map[page_num]:
                    barcode_value = page_barcode_map[page_num][0].data.strip()
                    
                    if barcode_value in barcode_groups:
                        barcode_groups[barcode_value].extend(unassigned_pages)
                        unassigned_pages.clear()
                    else:
                        barcode_groups[barcode_value] = []
                    
                    barcode_groups[barcode_value].append(page_num)
                    active_group_barcode = barcode_value
                else:
                    if active_group_barcode is not None:
                        barcode_groups[active_group_barcode].append(page_num)
                    else:
                        unassigned_pages.append(page_num)
            
            # 生成预览信息
            preview_groups = []
            filename_template = config.get('filename_template', '{barcode}_{index}')
            file_index = 0
            
            # 处理无条码组
            if unassigned_pages:
                preview_groups.append({
                    "barcode": "",
                    "filename": "无条码.pdf",
                    "pages": [p + 1 for p in unassigned_pages],
                    "page_count": len(unassigned_pages)
                })
                file_index += 1
            
            # 处理条码组
            barcode_file_counts = {}
            for barcode_value, pages in list(barcode_groups.items()):
                if pages:
                    if barcode_value not in barcode_file_counts:
                        barcode_file_counts[barcode_value] = 0
                    barcode_file_counts[barcode_value] += 1
                    file_count = barcode_file_counts[barcode_value]
                    
                    clean_barcode = self._clean_filename(barcode_value)
                    formatted_index = f"{file_count:03d}"
                    filename = filename_template.format(
                        barcode=clean_barcode,
                        index=formatted_index
                    )
                    filename = f"{filename}.pdf"
                    
                    preview_groups.append({
                        "barcode": barcode_value,
                        "filename": filename,
                        "pages": [p + 1 for p in pages],
                        "page_count": len(pages)
                    })
            
            return preview_groups
        except Exception:
            return []

    def _preview_filename_mode(self, doc: fitz.Document, barcodes: List[Any], config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """预览Filename模式的拆分结果"""
        try:
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

            # 生成预览组
            preview_groups = []

            # 遍历所有页面
            for page_num in range(total_pages):
                if page_num in page_barcode_map and page_barcode_map[page_num]:
                    # 当前页面有条码
                    barcode_value = page_barcode_map[page_num][0].data.strip()

                    # 如果当前组已经有内容且条码值不同，则保存当前组
                    if current_barcode is not None and current_barcode != barcode_value:
                        # 保存当前组
                        if current_group:
                            # 为当前条码值增加计数
                            if current_barcode not in barcode_file_counts:
                                barcode_file_counts[current_barcode] = 0
                            barcode_file_counts[current_barcode] += 1
                            file_count = barcode_file_counts[current_barcode]

                            # 生成文件名
                            filename_template = config.get('filename_template', '{barcode}_{index}')
                            clean_barcode = self._clean_filename(current_barcode)
                            formatted_index = f"{file_count:03d}"
                            filename = filename_template.format(
                                barcode=clean_barcode,
                                index=formatted_index
                            )
                            filename = f"{filename}.pdf"

                            preview_groups.append({
                                "barcode": current_barcode,
                                "filename": filename,
                                "pages": [p + 1 for p in current_group],
                                "page_count": len(current_group)
                            })

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
                    # 为当前条码值增加计数
                    if current_barcode not in barcode_file_counts:
                        barcode_file_counts[current_barcode] = 0
                    barcode_file_counts[current_barcode] += 1
                    file_count = barcode_file_counts[current_barcode]

                    # 生成文件名
                    filename_template = config.get('filename_template', '{barcode}_{index}')
                    clean_barcode = self._clean_filename(current_barcode)
                    formatted_index = f"{file_count:03d}"
                    filename = filename_template.format(
                        barcode=clean_barcode,
                        index=formatted_index
                    )
                    filename = f"{filename}.pdf"

                    preview_groups.append({
                        "barcode": current_barcode,
                        "filename": filename,
                        "pages": [p + 1 for p in current_group],
                        "page_count": len(current_group)
                    })
                else:
                    # 无条码的组（开头的无条码页面）
                    filename = "源文件.pdf"

                    preview_groups.append({
                        "barcode": "",
                        "filename": filename,
                        "pages": [p + 1 for p in current_group],
                        "page_count": len(current_group)
                    })

            return preview_groups
        except Exception:
            return []

    def cleanup(self) -> None:
        """
        清理资源
        在插件卸载或应用关闭时调用
        """
        self.is_initialized = False
        # 在这里添加资源清理代码