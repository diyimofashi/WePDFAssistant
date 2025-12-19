"""OCR页面标签类
支持在PDF页面上叠加OCR识别的文本层
"""

from PyQt5.QtWidgets import QLabel, QApplication
from PyQt5.QtGui import QPixmap, QPainter, QFont, QColor, QPen
from PyQt5.QtCore import Qt, QRect, QPoint
import logging

logger = logging.getLogger(__name__)


class OCRPageLabel(QLabel):
    """支持OCR文本层的页面标签"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ocr_data = []  # OCR识别结果数据
        self.page_scale = 1.0  # 页面缩放比例
        self.page_offset = QPoint(0, 0)  # 页面偏移量
        
    def set_ocr_data(self, ocr_data, page_scale=1.0, page_offset=QPoint(0, 0)):
        """
        设置OCR数据
        
        Args:
            ocr_data: OCR识别结果数据列表
            page_scale: 页面缩放比例
            page_offset: 页面偏移量
        """
        print(f"set_ocr_data 调用，输入数据: {ocr_data}")
        self.ocr_data = ocr_data if ocr_data else []
        print(f"存储的OCR数据: {self.ocr_data}")
        self.page_scale = page_scale
        self.page_offset = page_offset
        print("触发重绘")
        self.update()  # 触发重绘
        
    def paintEvent(self, event):
        """重写绘制事件，绘制页面和OCR文本层"""
        print(f"OCRPageLabel.paintEvent 调用，OCR数据长度: {len(self.ocr_data)}")
        # 先绘制父类的内容（PDF页面图像）
        super().paintEvent(event)
        
        # 如果有OCR数据，则绘制文本层
        if self.ocr_data:
            print("开始绘制OCR文本层")
            self._draw_ocr_text_layer(event)
            print("OCR文本层绘制完成")
        else:
            print("没有OCR数据，跳过绘制")
    
    def _draw_ocr_text_layer(self, event):
        """绘制OCR文本层"""
        try:
            print(f"开始绘制OCR文本层，OCR数据: {self.ocr_data}")
            if not self.ocr_data:
                print("没有OCR数据，跳过绘制")
                return
                
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing, True)
            
            # 设置字体和颜色
            font = QFont("Arial", 12, QFont.Normal)  # 适中的字体大小
            painter.setFont(font)
            painter.setPen(QPen(QColor(255, 0, 0, 200)))  # 半透明红色
            
            # 绘制每个OCR识别的文本框
            for i, item in enumerate(self.ocr_data):
                print(f"处理第{i}个OCR项: {item}")
                if not isinstance(item, dict):
                    continue
                    
                text = item.get("text", "")
                bbox = item.get("bbox", [])
                
                # 检查边界框数据是否有效
                if not text:
                    print(f"第{i}个OCR项没有文本")
                    continue
                if not bbox:
                    print(f"第{i}个OCR项没有边界框")
                    continue
                
                # 处理不同格式的边界框
                if isinstance(bbox, list) and len(bbox) == 4 and isinstance(bbox[0], list):
                    # 格式: [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
                    flattened_bbox = []
                    for point in bbox:
                        if isinstance(point, list) and len(point) == 2:
                            flattened_bbox.extend(point)
                    bbox = flattened_bbox
                    print(f"转换边界框格式: {bbox}")
                
                if len(bbox) != 8:
                    print(f"第{i}个OCR项边界框长度不正确: {len(bbox)}")
                    continue
                
                print(f"第{i}个OCR项有效: 文本='{text}', 边界框={bbox}")
                
                # 转换边界框坐标（考虑缩放和偏移）
                scaled_bbox = self._scale_bbox(bbox)
                print(f"缩放后的边界框: {scaled_bbox}")
                
                # 创建包围矩形
                rect = self._bbox_to_rect(scaled_bbox)
                print(f"包围矩形: {rect}")
                
                # 如果矩形太小，使用默认大小（相对于页面坐标）
                if rect.width() < 50 or rect.height() < 30:
                    print("矩形太小，使用默认大小")
                    # 使用相对于页面的坐标
                    default_x = int(50 * self.page_scale)
                    default_y = int((50 + i * 50) * self.page_scale)
                    default_width = int(300 * self.page_scale)
                    default_height = int(40 * self.page_scale)
                    rect = QRect(default_x, default_y, default_width, default_height)
                    print(f"使用默认矩形: {rect}")
                
                # 绘制文本框边界
                painter.setPen(QPen(QColor(0, 255, 0, 100), 2))  # 半透明绿色边框
                painter.drawRect(rect)
                print(f"绘制绿色边框: {rect}")
                
                # 绘制文本背景
                painter.setPen(QPen(QColor(255, 255, 0, 80), 1))  # 半透明黄色背景
                painter.fillRect(rect, QColor(255, 255, 0, 80))
                print(f"绘制黄色背景: {rect}")
                
                # 绘制文本
                painter.setPen(QPen(QColor(255, 0, 0, 200), 1))  # 半透明红色文本
                painter.drawText(rect, Qt.AlignLeft | Qt.AlignVCenter | Qt.TextWordWrap, text)
                print(f"绘制文本: '{text}' 在 {rect}")
                
            painter.end()
            print("OCR文本层绘制完成")
            
        except Exception as e:
            logger.error(f"绘制OCR文本层失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _scale_bbox(self, bbox):
        """
        缩放边界框坐标
        
        Args:
            bbox: 原始边界框坐标 [x1, y1, x2, y2, x3, y3, x4, y4]
            
        Returns:
            缩放后的边界框坐标
        """
        scaled_bbox = []
        for i in range(0, len(bbox), 2):
            # 直接使用页面缩放，不添加偏移量，使坐标相对于页面本身
            x = bbox[i] * self.page_scale
            y = bbox[i+1] * self.page_scale
            scaled_bbox.extend([x, y])
        return scaled_bbox
    
    def _bbox_to_rect(self, bbox):
        """
        将边界框转换为矩形
        
        Args:
            bbox: 边界框坐标 [x1, y1, x2, y2, x3, y3, x4, y4]
            
        Returns:
            QRect: 包围矩形
        """
        if len(bbox) != 8:
            return QRect(0, 0, 0, 0)
            
        # 找到最小和最大坐标
        x_coords = [bbox[i] for i in range(0, 8, 2)]
        y_coords = [bbox[i] for i in range(1, 8, 2)]
        
        min_x = min(x_coords)
        max_x = max(x_coords)
        min_y = min(y_coords)
        max_y = max(y_coords)
        
        return QRect(int(min_x), int(min_y), int(max_x - min_x), int(max_y - min_y))