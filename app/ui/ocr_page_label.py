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
from PyQt5.QtCore import Qt, QRect, QPoint, pyqtSignal


class OCRPageLabel(QWidget):
    """支持OCR文本层的页面标签 - 双层架构"""

    # 调试模式切换信号
    debug_mode_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ocr_data = []  # OCR识别结果数据
        self.page_scale = 1.0  # 页面缩放比例
        self.page_offset = QPoint(0, 0)  # 页面偏移量
        self.debug_mode = True  # 默认启用调试模式，方便用户测试
        self.pixmap = None  # 存储当前pixmap

        # 初始化UI
        self._init_ui()

        logger.info(f"[OCRPageLabel.__init__] 初始化完成，默认debug_mode={self.debug_mode}")

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

        logger.info(f"[OCRPageLabel.setPixmap] 设置图像尺寸: {pixmap.width()}x{pixmap.height()}, widget: {self.size()}")

    def set_ocr_data(self, ocr_data, page_scale=1.0, page_offset=QPoint(0, 0)):
        """
        设置OCR数据

        Args:
            ocr_data: OCR识别结果数据列表
            page_scale: 页面缩放比例
            page_offset: 页面偏移量
        """
        logger.info(f"[OCRPageLabel.set_ocr_data] 开始设置OCR数据")
        logger.info(f"[OCRPageLabel.set_ocr_data] page_scale={page_scale}, page_offset={page_offset}")

        self.ocr_data = ocr_data if ocr_data else []
        self.page_scale = page_scale
        self.page_offset = page_offset

        logger.info(f"[OCRPageLabel.set_ocr_data] OCR数据条数: {len(self.ocr_data)}")

        # 更新文本层
        if self.ocr_data:
            logger.info(f"[OCRPageLabel.set_ocr_data] OCR数据不为空，调用_update_text_layer")
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
                block.setStyleSheet("""
                    QTextEdit {
                        background-color: rgba(255, 255, 0, 80);
                        border: 1px solid rgba(0, 255, 0, 150);
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
        """更新文本层内容 - 根据bbox创建独立的文本块"""
        try:
            # 清除旧的文本块
            self._clear_text_blocks()

            logger.info(f"开始更新文本层，OCR数据条数: {len(self.ocr_data)}")

            # 获取图像标签的位置（在OCRPageLabel中，所以是(0,0)）
            # 图像和文本块都是OCRPageLabel的子控件

            # 为每个OCR文本块创建独立的文本区域
            for idx, item in enumerate(self.ocr_data):
                if not isinstance(item, dict):
                    continue

                text = item.get("text", "")
                # 兼容两种bbox格式: "bbox" 和 "box"
                bbox = item.get("bbox") or item.get("box", [])
                # 获取end字段，用于处理换行
                end = item.get("end", "")

                if not text:
                    logger.warning(f"文本块 {idx}: 文本为空，跳过")
                    continue

                if not bbox:
                    logger.warning(f"文本块 {idx} '{text[:30]}': bbox为空，跳过")
                    continue

                logger.debug(f"处理文本块 {idx}: text='{text[:30]}...', bbox={bbox}, end='{repr(end)}'")

                # 处理bbox格式：[[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
                # 例如：[[583, 146], [903, 129], [906, 172], [585, 189]]
                if isinstance(bbox, list) and len(bbox) == 4:
                    # 扁平化bbox
                    flattened_bbox = []
                    for point in bbox:
                        if isinstance(point, list) and len(point) >= 2:
                            flattened_bbox.extend(point)

                    # 计算文本框位置
                    if len(flattened_bbox) >= 8:
                        rect = self._bbox_to_rect(flattened_bbox)
                        # 缩放位置
                        scaled_rect = self._scale_rect(rect)

                        logger.debug(f"文本块 {idx}: 原始rect={rect}, 缩放后rect={scaled_rect}")

                        # 创建文本块标签（相对于OCRPageLabel的绝对定位）
                        self._create_text_block(text, scaled_rect, end)
                    else:
                        logger.warning(f"文本块 {idx}: bbox扁平化后长度不足8，跳过")
                else:
                    logger.warning(f"文本块 {idx}: bbox格式不正确，需要4个点的坐标数组")

            logger.info(f"文本层更新完成，创建了 {len(self.text_blocks)} 个文本块")

        except Exception as e:
            logger.error(f"更新文本层失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

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
        """
        # 根据end字段处理文本换行
        if end == "\n":
            # OCR返回end=\n表示需要换行，但文本选择时需要保持完整
            display_text = text
        else:
            display_text = text

        # 创建文本块
        text_block = QTextEdit(self)
        text_block.setReadOnly(True)
        text_block.setPlainText(display_text)
        text_block.setFrameStyle(QTextEdit.NoFrame)
        text_block.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        text_block.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # 禁用文本换行，确保文本在一行内显示
        text_block.setLineWrapMode(QTextEdit.NoWrap)
        # 设置文本垂直居中对齐
        text_block.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        # 计算字体大小
        font_size = max(int(rect.height() * 0.5), 8)
        font = QFont("Arial", font_size)
        text_block.setFont(font)

        logger.debug(f"[OCRPageLabel._create_text_block] 字体大小: {font_size} (rect.height={rect.height()})")

        #  计算文本所需宽高
        # 2. 逐步减小字体，直到文本宽度 ≤ rect.width()
        fm = QFontMetrics(font)
        while fm.horizontalAdvance(text) > rect.width() and font_size > 6:
            font_size -= 1
            font.setPointSize(font_size)
            fm = QFontMetrics(font)

        # 3. 根据最终字体高度，同步调整 rect 的高度（宽不变）
        text_height = fm.height()
        padding = 0
        rect.setHeight(text_height + padding * 2)

        text_block.setFont(font)
        text_block.setGeometry(rect)

        # 设置样式
        if self.debug_mode:
            text_block.setStyleSheet("""
                QTextEdit {
                    background-color: rgba(255, 255, 0, 80);
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

        # 设置位置和大小（相对于OCRPageLabel）
        text_block.setGeometry(rect)

        # 提升到最上层，确保在图像之上
        text_block.raise_()
        text_block.show()  # 确保文本块可见

        # 添加到列表
        self.text_blocks.append(text_block)

        logger.debug(f"[OCRPageLabel._create_text_block] 创建文本块完成: text='{text[:20]}...', pos={text_block.pos()}, size={text_block.size()}, visible={text_block.isVisible()}")

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

        return QRect(int(min_x), int(min_y), int(max_x - min_x), int(max_y - min_y))
