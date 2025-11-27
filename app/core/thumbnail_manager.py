"""
缩略图管理模块
负责PDF页面缩略图的生成、显示和管理
"""

from PyQt5.QtWidgets import QListWidget, QListWidgetItem, QMenu, QAction, QFileDialog, QMessageBox
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt, pyqtSignal, QSize
import os

# 导入页面编辑功能
from app.features.editor.page_editor import PageEditor


class ThumbnailManager(QListWidget):
    """缩略图管理器"""
    
    # 信号定义
    thumbnail_clicked = pyqtSignal(int)  # 缩略图点击信号
    thumbnail_right_clicked = pyqtSignal(int)  # 缩略图右键点击信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.pdf_processor = None
        self.page_editor = None  # 页面编辑器
        self.thumbnails = []  # 缩略图缓存
        
        self.init_ui()
        
    def init_ui(self):
        """初始化界面"""
        # 设置缩略图列表属性
        self.setIconSize(QSize(200, 234))  # 缩略图尺寸 (增加30%高度)
        self.setSpacing(5)  # 增加项目间距
        
        # 设置布局和显示模式
        self.setFlow(QListWidget.LeftToRight)  # 从左到右排列
        self.setResizeMode(QListWidget.Adjust)
        self.setWrapping(True)  # 允许换行
        self.setMovement(QListWidget.Static)
        self.setViewMode(QListWidget.IconMode)  # 图标模式
        self.setUniformItemSizes(True)  # 统一项目大小
        
        # 设置滚动条策略
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # 隐藏水平滚动条
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)  # 垂直滚动条按需显示
        
        # 设置对齐方式
        self.setProperty("alignment", Qt.AlignCenter)
        self.setUniformItemSizes(True)  # 统一项目大小以确保正确布局
        
        # 设置样式
        self.setStyleSheet("""
            QListWidget {
                background-color: #FFFFFF;
                border: none;
                padding: 5px;  /* 增加内边距 */
                margin: 0px;
                text-align: center;
                alignment: center;
            }
            QListWidget::item {
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                padding: 5px;  /* 增加内边距 */
                margin: 5px;   /* 增加外边距 */
                text-align: center;
                alignment: center;
                width: 200px;  /* 固定宽度 */
            }
            QListWidget::item:selected {
                border: 2px solid #0066CC;
                background-color: #E6F0FF;
            }
            QListWidget::item:selected {
                color: #000000;
                font-weight: bold;
            }
        """)
        
        # 连接事件
        self.itemClicked.connect(self.on_thumbnail_clicked)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.on_context_menu)
        
    def set_pdf_processor(self, pdf_processor):
        """设置PDF处理器"""
        self.pdf_processor = pdf_processor
        # 初始化页面编辑器
        if pdf_processor:
            self.page_editor = PageEditor(pdf_processor)
        
    def load_thumbnails(self):
        """加载PDF页面缩略图"""
        if not self.pdf_processor or not self.pdf_processor.fitz_document:
            return
            
        # 清空现有缩略图
        self.clear()
        self.thumbnails = []
        
        total_pages = self.pdf_processor.get_total_pages()
        
        # 生成每页的缩略图
        for page_num in range(total_pages):
            # 使用PDF处理器生成缩略图
            thumbnail_pixmap = self.pdf_processor.render_thumbnail(page_num, 200, 234)
            if thumbnail_pixmap:
                # 创建列表项
                item = QListWidgetItem()
                item.setIcon(QIcon(thumbnail_pixmap))
                item.setText(f"第 {page_num + 1} 页")  # 显示页码
                item.setData(Qt.UserRole, page_num)  # 存储页码信息
                item.setTextAlignment(Qt.AlignCenter)  # 文字居中
                
                self.addItem(item)
                self.thumbnails.append(thumbnail_pixmap)
                
                # 如果是当前页面，设置为选中状态
                current_page = self.pdf_processor.get_current_page()  # 获取当前页面
                if page_num == current_page - 1:  # current_page从1开始，page_num从0开始
                    item.setSelected(True)
                    # 确保选中的项可见
                    self.scrollToItem(item)
                    
        # 确保整个列表居中显示
        self.center_content()
                    
    def update_thumbnail_selection(self, current_page):
        """更新缩略图选中状态"""
        if self.count() > 0:
            # 取消之前的所有选中项
            self.clearSelection()
            
            # 选中当前页面的缩略图
            if current_page <= self.count():
                item = self.item(current_page - 1)
                if item:
                    item.setSelected(True)
                    # 确保选中的项可见
                    self.scrollToItem(item)
                    
    def center_content(self):
        """确保内容居中显示"""
        # 通过样式确保居中
        self.setStyleSheet(self.styleSheet() + "\nQListWidget {\n    alignment: center;\n}")
        # 强制更新布局
        self.updateGeometry()
                    
    def on_thumbnail_clicked(self, item):
        """处理缩略图点击事件"""
        page_num = item.data(Qt.UserRole)
        if page_num is not None:
            self.thumbnail_clicked.emit(page_num + 1)  # 发送页码信号（从1开始）
            
    def on_context_menu(self, position):
        """处理右键菜单事件"""
        item = self.itemAt(position)
        if item:
            page_num = item.data(Qt.UserRole)
            if page_num is not None:
                # 如果右键点击的页面不是当前选中的页面，则选中该页面
                current_selected = self.selectedItems()
                if not current_selected or current_selected[0] != item:
                    # 取消之前的所有选中项
                    self.clearSelection()
                    # 选中右键点击的项
                    item.setSelected(True)
                    
                # 发送右键点击信号
                self.thumbnail_right_clicked.emit(page_num + 1)  # 发送页码信号（从1开始）
                
                # 创建右键菜单
                self.create_context_menu(page_num + 1, self.mapToGlobal(position))
                
    def create_context_menu(self, page_num, position):
        """创建右键菜单"""
        menu = QMenu(self)
        
        # 页面操作菜单项
        insert_blank_action = QAction("插入空白页", self)
        insert_pdf_action = QAction("插入PDF页面", self)
        insert_image_action = QAction("插入图片", self)
        copy_page_action = QAction("复制页面", self)
        delete_page_action = QAction("删除页面", self)
        rotate_cw_action = QAction("顺时针旋转90°", self)
        rotate_ccw_action = QAction("逆时针旋转90°", self)
        rotate_all_cw_action = QAction("全部页面顺时针旋转90°", self)
        print_action = QAction("打印", self)
        extract_action = QAction("提取页面", self)
        ocr_action = QAction("OCR识别", self)
        
        # 添加菜单项
        menu.addAction(insert_blank_action)
        menu.addAction(insert_pdf_action)
        menu.addAction(insert_image_action)
        menu.addSeparator()
        menu.addAction(copy_page_action)
        menu.addAction(delete_page_action)
        menu.addSeparator()
        menu.addAction(rotate_cw_action)
        menu.addAction(rotate_ccw_action)
        menu.addAction(rotate_all_cw_action)
        menu.addSeparator()
        menu.addAction(print_action)
        menu.addAction(extract_action)
        menu.addAction(ocr_action)
        
        # 连接信号
        insert_blank_action.triggered.connect(lambda: self.on_insert_blank_page(page_num))
        insert_pdf_action.triggered.connect(lambda: self.on_insert_pdf_page(page_num))
        insert_image_action.triggered.connect(lambda: self.on_insert_image_page(page_num))
        copy_page_action.triggered.connect(lambda: self.on_copy_page(page_num))
        delete_page_action.triggered.connect(lambda: self.on_delete_page(page_num))
        rotate_cw_action.triggered.connect(lambda: self.on_rotate_page(page_num, 90))
        rotate_ccw_action.triggered.connect(lambda: self.on_rotate_page(page_num, -90))
        rotate_all_cw_action.triggered.connect(lambda: self.on_rotate_all_pages(90))
        print_action.triggered.connect(lambda: self.on_print_page(page_num))
        extract_action.triggered.connect(lambda: self.on_extract_pages(page_num))
        ocr_action.triggered.connect(lambda: self.on_ocr_page(page_num))
        
        # 显示菜单
        menu.exec_(position)
        
    def on_insert_blank_page(self, page_num):
        """插入空白页"""
        if not self.page_editor:
            QMessageBox.warning(self, "错误", "页面编辑器未初始化")
            return
        
        success, message = self.page_editor.insert_blank_page(page_num)
        if success:
            # 重新加载缩略图
            self.load_thumbnails()
            # 发送信号通知主窗口更新内容区域
            self.thumbnail_clicked.emit(page_num + 1)  # 跳转到插入页面的下一页
        else:
            QMessageBox.critical(self, "错误", message)
        
    def on_insert_pdf_page(self, page_num):
        """插入PDF页面"""
        if not self.page_editor:
            QMessageBox.warning(self, "错误", "页面编辑器未初始化")
            return
        
        # 选择PDF文件
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择PDF文件", "", "PDF文件 (*.pdf)")
        
        if file_path:
            success, message = self.page_editor.insert_pdf_pages(page_num, file_path)
            if success:
                # 重新加载缩略图
                self.load_thumbnails()
                # 发送信号通知主窗口更新内容区域
                self.thumbnail_clicked.emit(page_num + 1)  # 跳转到插入页面的下一页
            else:
                QMessageBox.critical(self, "错误", message)
        
    def on_insert_image_page(self, page_num):
        """插入图片页面"""
        if not self.page_editor:
            QMessageBox.warning(self, "错误", "页面编辑器未初始化")
            return
        
        # 选择图片文件
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择图片文件", "", "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif)")
        
        if file_path:
            success, message = self.page_editor.insert_image_page(page_num, file_path)
            if success:
                # 重新加载缩略图
                self.load_thumbnails()
                # 发送信号通知主窗口更新内容区域
                self.thumbnail_clicked.emit(page_num + 1)  # 跳转到插入页面的下一页
            else:
                QMessageBox.critical(self, "错误", message)
        
    def on_copy_page(self, page_num):
        """复制页面"""
        if not self.page_editor:
            QMessageBox.warning(self, "错误", "页面编辑器未初始化")
            return
        
        success, message = self.page_editor.copy_page(page_num)
        if success:
            # 重新加载缩略图
            self.load_thumbnails()
            # 发送信号通知主窗口更新内容区域
            self.thumbnail_clicked.emit(page_num)
        else:
            QMessageBox.critical(self, "错误", message)
        
    def on_delete_page(self, page_num):
        """删除页面"""
        if not self.page_editor:
            QMessageBox.warning(self, "错误", "页面编辑器未初始化")
            return
        
        # 确认删除
        reply = QMessageBox.question(
            self, "确认删除", f"确定要删除第 {page_num} 页吗？", 
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            success, message = self.page_editor.delete_page(page_num)
            if success:
                # 重新加载缩略图
                self.load_thumbnails()
                # 发送信号通知主窗口更新内容区域
                # 删除页面后跳转到前一页或第一页
                if page_num > 1:
                    self.thumbnail_clicked.emit(page_num - 1)
                else:
                    self.thumbnail_clicked.emit(1)
            else:
                QMessageBox.critical(self, "错误", message)
        
    def on_rotate_page(self, page_num, angle):
        """旋转页面"""
        if not self.page_editor:
            QMessageBox.warning(self, "错误", "页面编辑器未初始化")
            return
        
        success, message = self.page_editor.rotate_page(page_num, angle)
        if success:
            # 重新加载缩略图
            self.load_thumbnails()
            # 发送信号通知主窗口更新内容区域
            self.thumbnail_clicked.emit(page_num)
        else:
            QMessageBox.critical(self, "错误", message)
        
    def on_rotate_all_pages(self, angle):
        """旋转所有页面"""
        if not self.page_editor:
            QMessageBox.warning(self, "错误", "页面编辑器未初始化")
            return
        
        # 确认旋转所有页面
        reply = QMessageBox.question(
            self, "确认旋转", f"确定要旋转所有页面 {angle} 度吗？", 
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            success, message = self.page_editor.rotate_all_pages(angle)
            if success:
                # 重新加载缩略图
                self.load_thumbnails()
                # 发送信号通知主窗口更新内容区域
                self.thumbnail_clicked.emit(1)  # 跳转到第一页
            else:
                QMessageBox.critical(self, "错误", message)
        
    def on_print_page(self, page_num):
        """打印页面"""
        if not self.pdf_processor:
            QMessageBox.warning(self, "错误", "PDF处理器未初始化")
            return
        
        # 调用PDF处理器的打印功能
        # 这里简化实现，仅提供概念性代码
        QMessageBox.information(self, "打印", f"打印第 {page_num} 页功能开发中...")
        
    def on_extract_pages(self, page_num):
        """提取页面"""
        if not self.pdf_processor:
            QMessageBox.warning(self, "错误", "PDF处理器未初始化")
            return
        
        # 选择保存位置
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存提取的页面", f"page_{page_num}.pdf", "PDF文件 (*.pdf)")
        
        if file_path:
            # 这里简化实现，仅提供概念性代码
            QMessageBox.information(self, "提取页面", f"提取第 {page_num} 页到 {os.path.basename(file_path)} 功能开发中...")
        
    def on_ocr_page(self, page_num):
        """OCR识别页面"""
        if not self.pdf_processor:
            QMessageBox.warning(self, "错误", "PDF处理器未初始化")
            return
        
        # 调用OCR功能
        # 这里简化实现，仅提供概念性代码
        QMessageBox.information(self, "OCR识别", f"OCR识别第 {page_num} 页功能开发中...")