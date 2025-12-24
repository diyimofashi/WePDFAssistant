"""条码检测线程模块"""

import fitz
from typing import List, Optional, Callable
from PyQt5.QtCore import QThread, pyqtSignal
from app.core.barcode.barcode_detector import BarcodeDetector, BarcodeInfo
from app.utils.logger import get_logger

logger = get_logger('barcode_detection_thread')


class BarcodeDetectionThread(QThread):
    """条码检测线程"""
    
    progress_updated = pyqtSignal(int, int, str)  # 当前进度, 总数, 消息
    detection_completed = pyqtSignal(list)  # 检测完成信号，传递条码列表
    detection_error = pyqtSignal(str)  # 检测错误信号
    
    def __init__(self, pdf_path: str, enabled_types: List[str], method: str = "both"):
        super().__init__()
        self.pdf_path = pdf_path
        self.enabled_types = enabled_types
        self.method = method
        self._cancel_requested = False
        
    def request_cancel(self):
        """请求取消检测"""
        self._cancel_requested = True
        
    def run(self):
        """执行条码检测"""
        try:
            # 创建条码检测器
            detector = BarcodeDetector()
            detector.set_enabled_types(self.enabled_types)
            
            # 打开PDF文档
            doc = fitz.open(self.pdf_path)
            total_pages = len(doc)
            
            logger.debug(f"开始多线程检测条码，总页数: {total_pages}")
            
            # 检测条码
            barcodes = detector.detect_barcodes_in_document(
                doc,
                method=self.method,
                progress_callback=self._progress_callback,
                cancel_flag=self._cancel_flag
            )
            
            doc.close()
            
            # 检查是否被取消
            if self._cancel_flag():
                logger.info("条码检测被用户取消")
                return
            
            logger.debug(f"条码检测完成，共检测到 {len(barcodes)} 个条码")
            self.detection_completed.emit(barcodes)
            
        except Exception as e:
            logger.error(f"条码检测过程中出错: {e}")
            self.detection_error.emit(str(e))
    
    def _progress_callback(self, current: int, total: int, message: str):
        """进度回调"""
        if not self._cancel_flag():
            self.progress_updated.emit(current, total, message)
    
    def _cancel_flag(self) -> bool:
        """取消标志"""
        return self._cancel_requested