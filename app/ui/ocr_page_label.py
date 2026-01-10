"""OCR页面标签类
支持在PDF页面上叠加OCR识别的文本层，文本可选择和复制
"""

import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.utils.logger import get_logger
logger = get_logger('ocr_page_label')

from PyQt5.QtWidgets import QLabel, QWidget, QTextEdit, QApplication, QVBoxLayout, QHBoxLayout
from PyQt5.QtGui import QPixmap, QFont, QFontMetrics
from PyQt5.QtCore import Qt, QRect, QPoint, pyqtSignal, QTimer


class OCRPageLabel(QWidget):
    """支持OCR文本层的页面标签 - 双层架构"""

    # 调试模式切换信号
    debug_mode_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ocr_data = []  # OCR识别结果数据
        self.page_scale = 1.0  # 页面缩放比例
        self.page_offset = QPoint(0, 0)  # 页面偏移量
        self.debug_mode = False  # 默认禁用调试模式
        self.pixmap = None  # 存储当前pixmap

        # 初始化UI
        self._init_ui()

    def _init_ui(self):
        """初始化UI组件"""
        # 直接使用垂直布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 创建底层 - PDF图像标签
        self.image_label = QLabel(self)
        self.image_label.setStyleSheet("background-color: #FFFFFF;")
        self.main_layout.addWidget(self.image_label)

        # 文本块列表 - 存储根据bbox定位的文本块
        self.text_blocks = []

    def setPixmap(self, pixmap):
        """设置PDF图像"""
        self.pixmap = pixmap
        self.image_label.setPixmap(pixmap)

        # 调整自身大小以适应pixmap
        self.setFixedSize(pixmap.width(), pixmap.height())
        self.image_label.setFixedSize(pixmap.width(), pixmap.height())

    def set_ocr_data(self, ocr_data, page_scale=1.0, page_offset=QPoint(0, 0)):
        """
        设置OCR数据

        Args:
            ocr_data: OCR识别结果数据列表
            page_scale: 页面缩放比例
            page_offset: 页面偏移量
        """
        self.ocr_data = ocr_data if ocr_data else []
        self.page_scale = page_scale
        self.page_offset = page_offset

        # 更新文本层
        if self.ocr_data:
            self._update_text_layer()
        else:
            logger.warning(f"[OCRPageLabel.set_ocr_data] OCR数据为空，跳过更新")

    def update_page_scale(self, new_scale):
        """
        更新页面缩放比例

        Args:
            new_scale: 新的缩放比例
        """
        self.page_scale = new_scale
        # 重新更新文本层以适应新的缩放
        if self.ocr_data:
            self._update_text_layer()

    def set_debug_mode(self, enabled):
        """
        设置调试模式

        Args:
            enabled: 是否启用调试模式（文本可见）
        """
        self.debug_mode = enabled
        # 更新所有文本块的样式
        for block in self.text_blocks:
            if enabled:
                # 调试模式：黄色背景，透明度0.3
                block.setStyleSheet("""
                    QTextEdit {
                        background-color: rgba(255, 255, 0, 77);
                        border: none;
                        color: rgba(0, 0, 0, 255);
                    }
                """)
            else:
                block.setStyleSheet("""
                    QTextEdit {
                        background-color: transparent;
                        border: none;
                        color: transparent;
                    }
                """)
        self.debug_mode_changed.emit(enabled)

    def get_selected_text(self):
        """
        获取选中的文本

        Returns:
            str: 选中的文本，如果没有选中则返回空字符串
        """
        selected_text = ""
        for block in self.text_blocks:
            text = block.textCursor().selectedText()
            if text:
                selected_text += text
        return selected_text.strip()

    def _update_text_layer(self):
        """更新文本层内容 - 根据bbox创建独立的文本块（延迟执行以优化性能）"""
        # 使用QTimer延迟执行，避免阻塞UI
        QTimer.singleShot(0, self._do_update_text_layer)

    def _do_update_text_layer(self):
        """实际执行文本层更新（分批处理以保持UI响应）"""
        try:
            # 清除旧的文本块
            self._clear_text_blocks()

            # 分批处理，每批处理50个文本块
            batch_size = 50
            self._current_batch = 0
            self._batches = []

            # 准备批次数据
            current_batch_data = []
            for idx, item in enumerate(self.ocr_data):
                if not isinstance(item, dict):
                    continue

                text = item.get("text", "")
                bbox = item.get("bbox") or item.get("box", [])
                end = item.get("end", "")

                if not text or not bbox:
                    continue

                # 处理bbox格式：[[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
                if isinstance(bbox, list) and len(bbox) == 4:
                    flattened_bbox = []
                    for point in bbox:
                        if isinstance(point, list) and len(point) >= 2:
                            flattened_bbox.extend(point)

                    if len(flattened_bbox) >= 8:
                        rect = self._bbox_to_rect(flattened_bbox)
                        scaled_rect = self._scale_rect(rect)
                        current_batch_data.append((text, scaled_rect, end))

                        # 达到批次大小，添加到批次列表
                        if len(current_batch_data) >= batch_size:
                            self._batches.append(current_batch_data)
                            current_batch_data = []

            # 添加剩余的数据
            if current_batch_data:
                self._batches.append(current_batch_data)

            # 开始处理第一批
            self._process_next_batch()

        except Exception as e:
            logger.error(f"更新文本层失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def _process_next_batch(self):
        """处理下一批文本块"""
        if self._current_batch >= len(self._batches):
            self._batches.clear()
            self._current_batch = 0
            return

        batch_data = self._batches[self._current_batch]
        new_text_blocks = []

        for text, rect, end in batch_data:
            text_block = self._create_text_block(text, rect, end)
            if text_block:
                new_text_blocks.append(text_block)

        # 批量添加到列表
        self.text_blocks.extend(new_text_blocks)
        # 继续处理下一批
        self._current_batch += 1
        QTimer.singleShot(0, self._process_next_batch)

    def _clear_text_blocks(self):
        """清除所有文本块"""
        for block in self.text_blocks:
            block.setParent(None)
        self.text_blocks.clear()

    def _create_text_block(self, text, rect, end=""):
        """
        创建文本块标签

        Args:
            text: 文本内容
            rect: QRect，文本块的位置和大小（已缩放）
            end: 文本结束标记，"\n" 表示换行

        Returns:
            QTextEdit: 创建的文本块，如果失败返回None
        """
        try:
            # 计算字体大小
            font_size = max(int(rect.height() * 0.5), 8)

            # 计算合适的字体大小 - 使用二分查找优化
            font = QFont("Arial", font_size)
            fm = QFontMetrics(font)
            text_width = fm.horizontalAdvance(text)

            # 如果文本宽度超过矩形宽度，调整字体大小
            if text_width > rect.width() and font_size > 6:
                # 计算需要的缩放比例
                scale_ratio = rect.width() / text_width
                font_size = max(int(font_size * scale_ratio * 0.95), 6)  # 0.95是安全边距
                font.setPointSize(font_size)

            # 计算最终文本高度
            fm = QFontMetrics(font)
            text_height = fm.height()

            # 创建文本块
            text_block = QTextEdit(self)
            text_block.setReadOnly(True)
            text_block.setPlainText(text)
            text_block.setFrameStyle(QTextEdit.NoFrame)
            text_block.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            text_block.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            text_block.setLineWrapMode(QTextEdit.NoWrap)
            text_block.setAlignment(Qt.AlignLeft)  # 只水平左对齐
            text_block.setFont(font)

            # 直接使用PDF的bbox，不做任何调整
            # PyMuPDF的bbox已经是文本的精确位置
            adjusted_rect = QRect(rect.x(), rect.y(), rect.width(), rect.height())
            text_block.setGeometry(adjusted_rect)

            # 调试日志：输出位置信息
            if len(self.text_blocks) < 3:  # 只记录前3个文本块
                fm = QFontMetrics(font)
                ascent = fm.ascent()
                descent = fm.descent()
                logger.debug(f"[OCRPageLabel._create_text_block] 文本='{text[:10]}...', "
                           f"rect=({rect.x()}, {rect.y()}, {rect.width()}, {rect.height()}), "
                           f"text_height={text_height}, font_size={font_size}, "
                           f"ascent={ascent}, descent={descent}")

            # 设置样式
            if self.debug_mode:
                # 调试模式：黄色背景，透明度0.3 (0.3 * 255 ≈ 77)
                text_block.setStyleSheet("""
                    QTextEdit {
                        background-color: rgba(255, 255, 0, 77);
                        border: none;
                        color: rgba(0, 0, 0, 255);
                    }
                """)
            else:
                text_block.setStyleSheet("""
                    QTextEdit {
                        background-color: transparent;
                        border: none;
                        color: transparent;
                    }
                """)

            # 显示文本块
            text_block.raise_()
            text_block.show()

            return text_block

        except Exception as e:
            logger.error(f"创建文本块失败: {e}")
            return None

    def _scale_rect(self, rect):
        """
        缩放矩形

        Args:
            rect: QRect，原始矩形

        Returns:
            QRect: 缩放后的矩形
        """
        scaled_x = rect.x() * self.page_scale
        scaled_y = rect.y() * self.page_scale
        scaled_width = rect.width() * self.page_scale
        scaled_height = rect.height() * self.page_scale
        return QRect(int(scaled_x), int(scaled_y), int(scaled_width), int(scaled_height))

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

        return QRect(int(min_x), int(min_y + 7), int(max_x - min_x), int(max_y - min_y))
