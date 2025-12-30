"""
高级条码拆分插件 - API实现
支持首页规则、尾页规则、分隔页规则
"""

import os
import fitz
from io import BytesIO
from typing import Dict, List, Any, Optional
from PIL import Image
import pyzbar.pyzbar as pyzbar
from app.core.barcode.barcode_plugin_interface import BarcodePluginInterface, BarcodeResult, BarcodeErrorCode


class AdvancedBarcodePlugin(BarcodePluginInterface):
    """高级条码拆分插件实现"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.plugin_name = "advanced_barcode"
        self.plugin_version = "1.0.0"
        self.plugin_author = "Aurora PDF"
        self.config = config or {}

        self.enabled_types = self.config.get('enabled_types', ['ALL_TYPES'])
        self.min_length = self.config.get('min_length', 1)
        self.max_length = self.config.get('max_length', 1000)
        self.include_keywords = self.config.get('include_keywords', [])
        self.exclude_keywords = self.config.get('exclude_keywords', [])
        self.include_regex = self.config.get('include_regex', '')
        self.exclude_regex = self.config.get('exclude_regex', '')
        self.max_barcode_count = self.config.get('max_barcode_count', 100)

        self.split_position_rule = self.config.get('split_position_rule', 'first_page')
        self.remove_barcode_pages = self.config.get('remove_barcode_pages', False)
        self.horizontal_only = self.config.get('horizontal_only', False)
        self.filter_region = self.config.get('filter_region', None)
        self.merge_same_barcode = self.config.get('merge_same_barcode', False)
        self.use_barcode_filename = self.config.get('use_barcode_filename', True)
        self.filename_template = self.config.get('filename_template', '{barcode}_{index}')

        self.is_initialized = False

    def initialize(self, config: Dict[str, Any]) -> BarcodeResult:
        try:
            self.config.update(config)
            self.enabled_types = self.config.get('enabled_types', ['ALL_TYPES'])
            self.min_length = int(self.config.get('min_length', 1))
            self.max_length = int(self.config.get('max_length', 1000))
            self.include_keywords = self.config.get('include_keywords', [])
            self.exclude_keywords = self.config.get('exclude_keywords', [])
            self.include_regex = self.config.get('include_regex', '')
            self.exclude_regex = self.config.get('exclude_regex', '')
            self.max_barcode_count = int(self.config.get('max_barcode_count', 100))
            self.split_position_rule = self.config.get('split_position_rule', 'first_page')
            self.remove_barcode_pages = self.config.get('remove_barcode_pages', False)
            self.horizontal_only = self.config.get('horizontal_only', False)
            self.filter_region = self.config.get('filter_region', None)
            self.merge_same_barcode = self.config.get('merge_same_barcode', False)
            self.use_barcode_filename = self.config.get('use_barcode_filename', True)
            self.filename_template = self.config.get('filename_template', '{barcode}_{index}')

            self.is_initialized = True
            return BarcodeResult(code=BarcodeErrorCode.SUCCESS, message="插件初始化成功")
        except Exception as e:
            return BarcodeResult(code=BarcodeErrorCode.INIT_ERROR, message=f"插件初始化失败: {str(e)}")

    def detect_from_file(self, file_path: str) -> BarcodeResult:
        try:
            if not self.is_initialized:
                return BarcodeResult(code=BarcodeErrorCode.INIT_ERROR, message="插件未初始化")

            if not file_path or not os.path.exists(file_path):
                return BarcodeResult(code=BarcodeErrorCode.FILE_NOT_FOUND, message=f"文件不存在: {file_path}")

            image = Image.open(file_path)
            if image.mode != 'RGB':
                image = image.convert('RGB')

            barcodes = pyzbar.decode(image)
            filtered_barcodes = self._filter_and_format_barcodes(barcodes)

            return BarcodeResult(code=BarcodeErrorCode.SUCCESS, data=filtered_barcodes, message=f"检测到 {len(filtered_barcodes)} 个条码")
        except Exception as e:
            return BarcodeResult(code=BarcodeErrorCode.DETECTION_FAILED, message=f"从文件检测条码失败: {str(e)}")

    def detect_from_bytes(self, image_bytes: bytes) -> BarcodeResult:
        try:
            if not self.is_initialized:
                return BarcodeResult(code=BarcodeErrorCode.INIT_ERROR, message="插件未初始化")

            image = Image.open(BytesIO(image_bytes))
            if image.mode != 'RGB':
                image = image.convert('RGB')

            barcodes = pyzbar.decode(image)
            filtered_barcodes = self._filter_and_format_barcodes(barcodes)

            return BarcodeResult(code=BarcodeErrorCode.SUCCESS, data=filtered_barcodes, message=f"检测到 {len(filtered_barcodes)} 个条码")
        except Exception as e:
            return BarcodeResult(code=BarcodeErrorCode.DETECTION_FAILED, message=f"从字节流检测条码失败: {str(e)}")

    def detect_from_base64(self, base64_string: str) -> BarcodeResult:
        try:
            if not self.is_initialized:
                return BarcodeResult(code=BarcodeErrorCode.INIT_ERROR, message="插件未初始化")

            import base64
            image_bytes = base64.b64decode(base64_string)
            image = Image.open(BytesIO(image_bytes))
            if image.mode != 'RGB':
                image = image.convert('RGB')

            barcodes = pyzbar.decode(image)
            filtered_barcodes = self._filter_and_format_barcodes(barcodes)

            return BarcodeResult(code=BarcodeErrorCode.SUCCESS, data=filtered_barcodes, message=f"检测到 {len(filtered_barcodes)} 个条码")
        except Exception as e:
            return BarcodeResult(code=BarcodeErrorCode.DETECTION_FAILED, message=f"从Base64字符串检测条码失败: {str(e)}")

    def get_supported_types(self) -> List[str]:
        return ['CODE128', 'CODE39', 'CODE93', 'CODABAR', 'EAN13', 'EAN8', 'UPCA', 'UPCE', 'I25', 'PDF417', 'QR']

    def detect_from_pdf(self, doc: 'fitz.Document', config: Optional[Dict[str, Any]] = None) -> BarcodeResult:
        from .split_logic import detect_barcodes_enhanced, filter_barcodes

        try:
            if not self.is_initialized:
                return BarcodeResult(code=BarcodeErrorCode.INIT_ERROR, message="插件未初始化")

            if config is None:
                config = self.config.copy()

            all_barcodes = detect_barcodes_enhanced(doc, config)
            filtered_barcodes = filter_barcodes(all_barcodes, config)

            results = []
            for barcode in filtered_barcodes:
                results.append({
                    "data": barcode.data,
                    "type": barcode.type,
                    "bbox": [barcode.rect.left, barcode.rect.top, barcode.rect.left + barcode.rect.width, barcode.rect.top + barcode.rect.height],
                    "confidence": 1.0,
                    "page_num": barcode.page_num
                })

            if results:
                return BarcodeResult(code=BarcodeErrorCode.SUCCESS, data=results, message=f"在PDF中检测到 {len(results)} 个条码")
            else:
                return BarcodeResult(code=BarcodeErrorCode.SUCCESS, data=[], message="未在PDF中检测到条码")
        except Exception as e:
            return BarcodeResult(code=BarcodeErrorCode.DETECTION_FAILED, message=f"从PDF文档检测条码失败: {str(e)}")

    def split_document_by_barcodes(self, doc: fitz.Document, output_dir: str,
                                 config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._split_with_progress(doc, output_dir, config, None)

    def split_document_by_barcodes_with_progress(self, doc: fitz.Document, output_dir: str,
                                             config: Optional[Dict[str, Any]] = None, progress_callback=None) -> Dict[str, Any]:
        return self._split_with_progress(doc, output_dir, config, progress_callback)

    def _split_with_progress(self, doc: fitz.Document, output_dir: str,
                            config: Optional[Dict[str, Any]] = None, progress_callback=None) -> Dict[str, Any]:
        from .split_logic import (detect_barcodes_enhanced, filter_barcodes,
                                    split_by_first_page_rule, split_by_last_page_rule, split_by_separator_page_rule)
        from app.utils.logger import get_logger
        import traceback

        logger = get_logger(__name__)

        try:
            if not self.is_initialized:
                logger.error("插件未初始化")
                return {"success": False, "message": "插件未初始化", "files_created": [], "barcodes_found": 0, "pages_processed": 0}

            os.makedirs(output_dir, exist_ok=True)
            if config is None:
                config = self.config.copy()

            logger.info(f"开始拆分文档: output_dir={output_dir}, split_position_rule={config.get('split_position_rule')}")

            total_pages = len(doc)

            if progress_callback:
                if not progress_callback(0, 100, "开始拆分..."):
                    logger.info("用户取消了操作")
                    return {"success": False, "message": "用户取消了操作", "files_created": [], "barcodes_found": 0, "pages_processed": 0}

            logger.info("开始检测条码...")
            all_barcodes = detect_barcodes_enhanced(doc, config, progress_callback)
            filtered_barcodes = filter_barcodes(all_barcodes, config)
            logger.info(f"条码检测完成: all_barcodes={len(all_barcodes)}, filtered_barcodes={len(filtered_barcodes)}")

            if not filtered_barcodes:
                logger.warning("没有找到符合条件的条码")
                return {"success": False, "message": "没有找到符合条件的条码", "files_created": [], "barcodes_found": len(all_barcodes), "pages_processed": total_pages}

            if progress_callback:
                if not progress_callback(50, 100, f"检测到 {len(filtered_barcodes)} 个条码，开始拆分..."):
                    logger.info("用户取消了操作")
                    return {"success": False, "message": "用户取消了操作", "files_created": [], "barcodes_found": len(all_barcodes), "pages_processed": total_pages}

            split_position_rule = config.get('split_position_rule', 'first_page')
            logger.info(f"拆分规则: {split_position_rule}")

            logger.info(f"开始执行拆分逻辑: {split_position_rule}")
            if split_position_rule == "first_page":
                files_created = split_by_first_page_rule(doc, filtered_barcodes, config, output_dir, progress_callback, self._clean_filename)
            elif split_position_rule == "last_page":
                files_created = split_by_last_page_rule(doc, filtered_barcodes, config, output_dir, progress_callback, self._clean_filename)
            elif split_position_rule == "separator_page":
                files_created = split_by_separator_page_rule(doc, filtered_barcodes, config, output_dir, progress_callback, self._clean_filename)
            else:
                logger.error(f"未知的拆分规则: {split_position_rule}")
                files_created = []

            logger.info(f"拆分完成: files_created={len(files_created)}")

            if progress_callback:
                progress_callback(100, 100, "拆分完成")

            return {"success": True, "message": f"成功拆分PDF，创建了 {len(files_created)} 个文件", "files_created": files_created, "barcodes_found": len(all_barcodes), "pages_processed": total_pages}
        except Exception as e:
            logger.error(f"插件拆分逻辑出错: {str(e)}", exc_info=True)
            logger.error(traceback.format_exc())
            return {"success": False, "message": f"插件拆分逻辑出错: {str(e)}", "files_created": [], "barcodes_found": 0, "pages_processed": 0}

    def preview_split_result(self, doc: fitz.Document, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        from .split_logic import (detect_barcodes_enhanced, filter_barcodes,
                                    preview_first_page_rule, preview_last_page_rule, preview_separator_page_rule)

        try:
            if not self.is_initialized:
                return {"error": "插件未初始化"}

            if config is None:
                config = self.config.copy()

            total_pages = len(doc)
            all_barcodes = detect_barcodes_enhanced(doc, config)
            filtered_barcodes = filter_barcodes(all_barcodes, config)

            if not filtered_barcodes:
                return {"total_pages": total_pages, "total_barcodes": len(all_barcodes), "filtered_barcodes": 0, "groups": 0, "output_files": 0, "preview": []}

            split_position_rule = config.get('split_position_rule', 'first_page')

            if split_position_rule == "first_page":
                preview_groups = preview_first_page_rule(total_pages, filtered_barcodes, config, self._clean_filename)
            elif split_position_rule == "last_page":
                preview_groups = preview_last_page_rule(total_pages, filtered_barcodes, config, self._clean_filename)
            elif split_position_rule == "separator_page":
                preview_groups = preview_separator_page_rule(total_pages, filtered_barcodes, config, self._clean_filename)
            else:
                preview_groups = []

            return {"total_pages": total_pages, "total_barcodes": len(all_barcodes), "filtered_barcodes": len(filtered_barcodes), "groups": len(preview_groups), "output_files": len(preview_groups), "preview": preview_groups}
        except Exception as e:
            return {"error": f"预览拆分结果时发生错误: {str(e)}"}

    def _filter_and_format_barcodes(self, barcodes: List[Any]) -> List[Dict[str, Any]]:
        """过滤并格式化条码"""
        results = []
        max_count = self.max_barcode_count

        for barcode in barcodes[:max_count]:
            try:
                barcode_data_str = barcode.data.decode('utf-8')
            except Exception:
                continue

            if not isinstance(barcode_data_str, str):
                try:
                    barcode_data_str = str(barcode_data_str)
                except Exception:
                    continue

            barcode_len = len(barcode_data_str)
            if barcode_len < self.min_length or barcode_len > self.max_length:
                continue

            if self.include_keywords:
                if not any(k.lower() in barcode_data_str.lower() for k in self.include_keywords):
                    continue

            if self.exclude_keywords:
                if any(k.lower() in barcode_data_str.lower() for k in self.exclude_keywords):
                    continue

            if self.include_regex:
                import re
                try:
                    if not re.search(self.include_regex, barcode_data_str):
                        continue
                except re.error:
                    pass

            if self.exclude_regex:
                import re
                try:
                    if re.search(self.exclude_regex, barcode_data_str):
                        continue
                except re.error:
                    pass

            results.append({
                "data": barcode_data_str,
                "type": barcode.type,
                "bbox": [barcode.rect.left, barcode.rect.top, barcode.rect.left + barcode.rect.width, barcode.rect.top + barcode.rect.height],
                "confidence": 1.0,
                "page_num": 0
            })

        return results

    def _clean_filename(self, filename: str) -> str:
        illegal_chars = '<>:"/\\|?*'
        for char in illegal_chars:
            filename = filename.replace(char, '_')
        filename = filename.strip('. ')
        if len(filename) > 50:
            filename = filename[:50]
        return filename

    def cleanup(self) -> None:
        self.is_initialized = False

    def get_plugin_info(self) -> Dict[str, Any]:
        return {
            "name": self.plugin_name,
            "version": self.plugin_version,
            "author": self.plugin_author,
            "initialized": self.is_initialized
        }
