"""
缩略图管理模块
负责PDF页面缩略图的生成、显示和管理
"""

from PyQt5.QtWidgets import QListWidget, QListWidgetItem, QMenu, QAction, QFileDialog, QMessageBox
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QThread, QTimer
import logging

# 导入页面编辑功能
from ..editing.page_editor import PageEditor

logger = logging.getLogger(__name__)


class AsyncThumbnailLoader(QThread):
    """异步缩略图加载器"""
    
    # 信号定义
    thumbnail_ready = pyqtSignal(int, object)  # 页码, QPixmap
    loading_finished = pyqtSignal()  # 加载完成
    
    def __init__(self, pdf_processor, page_nums, parent=None):
        super().__init__(parent)
        self.pdf_processor = pdf_processor
        self.page_nums = page_nums
        self.is_cancelled = False
        
    def run(self):
        """异步加载缩略图"""
        try:
            logger.info(f"开始异步加载缩略图，页数: {len(self.page_nums)}")
            for page_num in self.page_nums:
                if self.is_cancelled:
                    logger.info("缩略图加载已取消")
                    break

                try:
                    # 生成缩略图
                    thumbnail_pixmap = self.pdf_processor.render_thumbnail(page_num, 200, 234)
                    if thumbnail_pixmap:
                        self.thumbnail_ready.emit(page_num, thumbnail_pixmap)
                        logger.debug(f"第 {page_num + 1} 页缩略图生成成功")
                    else:
                        logger.warning(f"第 {page_num + 1} 页缩略图生成失败，返回None")
                except Exception as e:
                    logger.error(f"生成第 {page_num + 1} 页缩略图时出错: {e}")

                # 短暂延迟，避免阻塞UI
                self.msleep(10)

            if not self.is_cancelled:
                logger.info("所有缩略图加载完成")
                self.loading_finished.emit()
        except Exception as e:
            logger.error(f"异步加载缩略图失败: {e}")
            import traceback
            traceback.print_exc()
            
    def cancel(self):
        """取消加载"""
        self.is_cancelled = True


class ThumbnailManager(QListWidget):
    """缩略图管理器"""
    
    # 信号定义
    thumbnail_clicked = pyqtSignal(int)  # 缩略图点击信号
    thumbnail_right_clicked = pyqtSignal(int)  # 缩略图右键点击信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pdf_processor = None
        self.page_editor = None  # 页面编辑器
        self.thumbnails = []  # 缩略图缓存
        self.async_loader = None  # 异步加载器
        
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

        # 设置最小和最大宽度，确保容器宽度合适
        self.setMinimumWidth(280)
        self.setMaximumWidth(280)  # 固定宽度，确保水平居中

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
        logger.debug(f"设置PDF处理器: {pdf_processor}")
        self.pdf_processor = pdf_processor
        # 初始化页面编辑器
        if pdf_processor:
            logger.debug("初始化页面编辑器")
            # 如果pdf_processor已经有page_editor，则使用它；否则创建新的
            if pdf_processor.page_editor:
                logger.debug(f"使用pdf_processor已有的page_editor: {pdf_processor.page_editor}")
                self.page_editor = pdf_processor.page_editor
            else:
                self.page_editor = PageEditor(pdf_processor)
                pdf_processor.page_editor = self.page_editor
                logger.debug(f"创建新的page_editor并设置到pdf_processor: {self.page_editor}")
            logger.debug(f"页面编辑器初始化完成: {self.page_editor}")

            # 连接页面编辑器的状态变化信号到主窗口
            if hasattr(self, 'parent') and self.parent():
                main_window = self.parent()
                logger.debug(f"找到主窗口: {main_window}")
                if hasattr(main_window, 'update_save_actions_state'):
                    logger.debug("连接PageEditor状态变化信号到主窗口")
                    self.page_editor.state_changed.connect(main_window.update_save_actions_state)
                else:
                    logger.debug("主窗口没有update_save_actions_state方法")
            else:
                logger.debug("没有找到父窗口或父窗口无效")
        else:
            logger.debug("PDF处理器为空，未初始化页面编辑器")
        
    def load_thumbnails(self):
        """加载PDF页面缩略图"""
        if not self.pdf_processor or not self.pdf_processor.fitz_document:
            logger.warning("无法加载缩略图: PDF处理器或文档不存在")
            return

        logger.info(f"开始加载缩略图，总页数: {self.pdf_processor.get_total_pages()}")
        logger.info(f"缩略图面板可见性: {self.isVisible()}")
        logger.info(f"缩略图面板尺寸: {self.size().width()}x{self.size().height()}")
        logger.info(f"缩略图面板最小宽度: {self.minimumWidth()}")

        # 清空现有缩略图
        self.clear()
        self.thumbnails = []

        total_pages = self.pdf_processor.get_total_pages()
        logger.debug(f"PDF总页数: {total_pages}")

        # 生成每页的缩略图占位符
        for page_num in range(total_pages):
            # 创建列表项
            item = QListWidgetItem()
            # 使用占位符图标
            placeholder_pixmap = self._create_placeholder()
            item.setIcon(QIcon(placeholder_pixmap))
            item.setText(f"第 {page_num + 1} 页")  # 显示页码
            item.setData(Qt.UserRole, page_num)  # 存储页码信息
            item.setTextAlignment(Qt.AlignCenter)  # 文字居中

            self.addItem(item)
            self.thumbnails.append(None)  # 占位符

            # 如果是当前页面，设置为选中状态
            current_page = self.pdf_processor.get_current_page()  # 获取当前页面
            if page_num == current_page - 1:  # current_page从1开始，page_num从0开始
                item.setSelected(True)
                # 确保选中的项可见
                self.scrollToItem(item)

        logger.debug(f"添加了{total_pages}个缩略图占位符")
        logger.debug(f"当前列表项数量: {self.count()}")

        # 确保整个列表居中显示
        self.center_content()

        # 强制更新显示
        self.updateGeometry()
        self.update()
        self.repaint()

        # 异步加载缩略图
        logger.debug("开始异步加载缩略图")
        self._load_thumbnails_async()
        logger.info("缩略图加载请求已发送")
                    
    def _create_placeholder(self):
        """创建占位符缩略图"""
        pixmap = QPixmap(200, 234)
        pixmap.fill(Qt.lightGray)
        return pixmap
        
    def _load_thumbnails_async(self):
        """异步加载缩略图"""
        if not self.pdf_processor or not self.pdf_processor.fitz_document:
            return
            
        # 取消之前的加载任务
        if self.async_loader and self.async_loader.isRunning():
            self.async_loader.cancel()
            self.async_loader.wait()
            
        total_pages = self.pdf_processor.get_total_pages()
        page_nums = list(range(total_pages))
        
        # 创建异步加载器
        self.async_loader = AsyncThumbnailLoader(self.pdf_processor, page_nums)
        
        # 连接信号
        self.async_loader.thumbnail_ready.connect(self._on_thumbnail_ready)
        self.async_loader.loading_finished.connect(self._on_loading_finished)
        
        # 开始异步加载
        self.async_loader.start()
        
    def _on_thumbnail_ready(self, page_num, pixmap):
        """缩略图就绪回调"""
        logger.debug(f"缩略图就绪: 页码 {page_num}, 尺寸: {pixmap.width()}x{pixmap.height()}")
        if page_num < self.count():
            item = self.item(page_num)
            if item:
                item.setIcon(QIcon(pixmap))
                self.thumbnails[page_num] = pixmap
                logger.debug(f"已更新第 {page_num + 1} 页的缩略图")
            else:
                logger.warning(f"未找到页码 {page_num} 的列表项")
        else:
            logger.warning(f"页码 {page_num} 超出范围，总页数: {self.count()}")
                
    def _on_loading_finished(self):
        """加载完成回调"""
        pass
        
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
                
                # 尝试使用主窗口的右键菜单系统
                parent = self.parent()
                while parent and not hasattr(parent, 'show_context_menu_at'):
                    parent = parent.parent()
                
                if parent and hasattr(parent, 'show_context_menu_at'):
                    # 使用主窗口的右键菜单系统
                    global_pos = self.mapToGlobal(position)
                    local_pos = parent.mapFromGlobal(global_pos)
                    parent.show_context_menu_at(local_pos)
                else:
                    # 使用原有的右键菜单
                    self.create_context_menu(page_num + 1, self.mapToGlobal(position))
    
    def get_page_at_position(self, pos):
        """获取指定位置的缩略图页码
        
        Args:
            pos: 相对于缩略图列表的位置 (QPoint)
            
        Returns:
            int: 页码，如果无法获取则返回None
        """
        try:
            item = self.itemAt(pos)
            if item:
                page_num = item.data(Qt.UserRole)
                return page_num
            return None
        except Exception as e:
            logger.error(f"获取缩略图页码失败: {e}")
            return None


                
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
        
    def _notify_main_window_changes(self):
        """通知主窗口更新保存操作状态"""
        # 更新保存操作状态
        main_window = self.parent()
        logger.debug(f"通知主窗口更新状态: main_window={main_window}")
        if main_window and hasattr(main_window, 'update_save_actions_state'):
            logger.debug("调用主窗口的update_save_actions_state方法")
            # 检查主窗口中的页面编辑器状态
            if hasattr(main_window, 'pdf_processor') and main_window.pdf_processor:
                if hasattr(main_window.pdf_processor, 'page_editor') and main_window.pdf_processor.page_editor:
                    page_editor = main_window.pdf_processor.page_editor
                    logger.debug(f"主窗口页面编辑器状态: can_undo={page_editor.can_undo()}, history_length={len(page_editor.history)})")
            # 检查缩略图管理器中的页面编辑器状态
            if hasattr(self, 'page_editor') and self.page_editor:
                logger.debug(f"缩略图管理器页面编辑器状态: can_undo={self.page_editor.can_undo()}, history_length={len(self.page_editor.history)})")
            main_window.update_save_actions_state()
        else:
            logger.debug("无法找到主窗口或update_save_actions_state方法")

    def on_insert_blank_page(self, page_num):
        """插入空白页"""
        if not self.page_editor:
            QMessageBox.warning(self, "错误", "页面编辑器未初始化")
            return
        
        logger.debug(f"开始插入空白页到第{page_num}页")
        success, message = self.page_editor.insert_blank_page(page_num)
        logger.debug(f"插入空白页结果: success={success}, message={message}")
        if success:
            # 只更新受影响的缩略图，而不是重新加载所有缩略图
            self.update_specific_thumbnails_after_insert(page_num)
            # 发送信号通知主窗口更新内容区域
            self.thumbnail_clicked.emit(page_num + 1)  # 跳转到新插入的页面
            # 通知主窗口更新保存操作状态
            logger.debug("调用_notify_main_window_changes方法")
            self._notify_main_window_changes()
            logger.debug("_notify_main_window_changes方法调用完成")
            # 添加延迟更新，确保按钮状态正确更新
            QTimer.singleShot(100, self._notify_main_window_changes)
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
            success, message = self.page_editor.insert_pdf_page(page_num, file_path)
            if success:
                # 只更新受影响的缩略图，而不是重新加载所有缩略图
                self.update_specific_thumbnails_after_insert(page_num)
                # 发送信号通知主窗口更新内容区域
                self.thumbnail_clicked.emit(page_num + 1)  # 跳转到新插入的页面
                # 通知主窗口更新保存操作状态
                self._notify_main_window_changes()
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
                # 只更新受影响的缩略图，而不是重新加载所有缩略图
                self.update_specific_thumbnails_after_insert(page_num)
                # 发送信号通知主窗口更新内容区域
                self.thumbnail_clicked.emit(page_num + 1)  # 跳转到新插入的页面
                # 通知主窗口更新保存操作状态
                self._notify_main_window_changes()
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
            self.thumbnail_clicked.emit(page_num + 1)
            # 通知主窗口更新保存操作状态
            self._notify_main_window_changes()
        else:
            QMessageBox.critical(self, "错误", message)

    def on_delete_page(self, page_num):
        """删除页面"""
        if not self.page_editor:
            QMessageBox.warning(self, "错误", "页面编辑器未初始化")
            return
        
        # 确认删除
        reply = QMessageBox.question(
            self, "确认删除", f"确定要删除第{page_num}页吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            success, message = self.page_editor.delete_page(page_num)
            if success:
                # 只更新受影响的缩略图，而不是重新加载所有缩略图
                self.update_specific_thumbnails_after_delete(page_num)
                # 通知主窗口更新保存操作状态
                self._notify_main_window_changes()
            else:
                QMessageBox.critical(self, "错误", message)

    def on_rotate_cw(self, page_num):
        """顺时针旋转页面"""
        if not self.page_editor:
            QMessageBox.warning(self, "错误", "页面编辑器未初始化")
            return
        
        success, message = self.page_editor.rotate_page(page_num, 90)
        if success:
            # 只更新受影响的缩略图，而不是重新加载所有缩略图
            self.update_specific_thumbnail(page_num)
            # 通知主窗口更新保存操作状态
            self._notify_main_window_changes()
        else:
            QMessageBox.critical(self, "错误", message)

    def on_rotate_ccw(self, page_num):
        """逆时针旋转页面"""
        if not self.page_editor:
            QMessageBox.warning(self, "错误", "页面编辑器未初始化")
            return
        
        success, message = self.page_editor.rotate_page(page_num, -90)
        if success:
            # 只更新受影响的缩略图，而不是重新加载所有缩略图
            self.update_specific_thumbnail(page_num)
            # 通知主窗口更新保存操作状态
            self._notify_main_window_changes()
        else:
            QMessageBox.critical(self, "错误", message)

    def on_extract_pages(self, page_num):
        """提取页面"""
        if not self.pdf_processor:
            QMessageBox.warning(self, "错误", "PDF处理器未初始化")
            return
        
        # 选择保存位置
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存提取的页面", f"page_{page_num}.pdf", "PDF文件 (*.pdf)")
        
        if file_path:
            # 使用页面编辑器提取页面
            if self.page_editor:
                success, message = self.page_editor.extract_pages([page_num], file_path)
                if success:
                    QMessageBox.information(self, "提取页面", message)
                else:
                    QMessageBox.critical(self, "错误", message)
            else:
                QMessageBox.warning(self, "错误", "页面编辑器未初始化")

    def on_print_page(self, page_num):
        """打印页面"""
        if not self.pdf_processor:
            QMessageBox.warning(self, "错误", "PDF处理器未初始化")
            return
        
        # 创建打印机对象
        printer = QPrinter(QPrinter.HighResolution)
        printer.setPageMargins(10, 10, 10, 10, QPrinter.Millimeter)
        
        # 显示打印对话框
        print_dialog = QPrintDialog(printer, self)
        print_dialog.setWindowTitle(f"打印第{page_num}页")
        
        if print_dialog.exec_() == QPrintDialog.Accepted:
            try:
                # 渲染页面到打印机
                painter = QPainter(printer)
                
                # 获取页面
                page = self.pdf_processor.fitz_document.load_page(page_num - 1)  # 0-based index
                
                # 获取页面尺寸
                rect = page.rect
                dpi = 300  # 打印分辨率
                
                # 计算缩放因子
                scale_x = printer.width() / rect.width
                scale_y = printer.height() / rect.height
                scale = min(scale_x, scale_y) * 0.9  # 留一些边距
                
                # 设置变换矩阵
                mat = fitz.Matrix(scale, scale)
                
                # 渲染页面
                pix = page.get_pixmap(matrix=mat, dpi=dpi)
                
                # 创建QImage
                img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
                
                # 绘制到打印机
                painter.drawImage(0, 0, img)
                painter.end()
                
                QMessageBox.information(self, "打印成功", f"第{page_num}页已发送到打印机")
            except Exception as e:
                QMessageBox.critical(self, "打印失败", f"打印过程中出现错误：{str(e)}")

    def on_ocr_page(self, page_num):
        """OCR识别页面"""
        if not self.pdf_processor:
            QMessageBox.warning(self, "错误", "PDF处理器未初始化")
            return
        
        # 调用OCR功能
        # 这里简化实现，仅提供概念性代码
        QMessageBox.information(self, "OCR识别", f"OCR识别第 {page_num} 页功能开发中...")
        
    def update_specific_thumbnail(self, page_num):
        """更新指定页面的缩略图"""
        if not self.pdf_processor or not self.pdf_processor.fitz_document:
            return
            
        # 异步更新单个缩略图
        self._update_thumbnail_async(page_num - 1)
            
    def update_specific_thumbnails_after_insert(self, insert_page_num):
        """在插入页面后更新缩略图

        Args:
            insert_page_num: 插入位置（1-based，表示新页面插入到第insert_page_num页之后）
        """
        if not self.pdf_processor or not self.pdf_processor.fitz_document:
            return

        try:
            total_pages = self.pdf_processor.get_total_pages()

            # 首先更新插入点之后的所有页面编号
            for i in range(insert_page_num, self.count()):
                item = self.item(i)
                if item:
                    item.setText(f"第 {i + 2} 页")  # 所有后续页面编号+1

            # 然后在插入点位置插入新的缩略图占位符
            if insert_page_num <= total_pages:
                # 创建新的列表项
                item = QListWidgetItem()
                # 使用占位符图标
                placeholder_pixmap = self._create_placeholder()
                item.setIcon(QIcon(placeholder_pixmap))
                item.setText(f"第 {insert_page_num + 1} 页")  # 新页面是第insert_page_num+1页
                item.setData(Qt.UserRole, insert_page_num)  # 新页面的0-based索引是insert_page_num
                item.setTextAlignment(Qt.AlignCenter)

                # 插入到指定位置（insert_page_num是1-based，转换为0-based的列表索引）
                # 新页面插入到第insert_page_num页之后，所以插入到索引insert_page_num的位置
                self.insertItem(insert_page_num, item)

                # 如果是当前页面，设置为选中状态
                current_page = self.pdf_processor.get_current_page()
                if insert_page_num == current_page:
                    item.setSelected(True)
                    self.scrollToItem(item)

                # 异步加载新插入的缩略图
                self._update_thumbnail_async(insert_page_num)
        except Exception as e:
            logger.error(f"插入后更新缩略图失败: {e}")
    
    def update_specific_thumbnails_after_delete(self, delete_page_num):
        """在删除页面后更新缩略图"""
        logger.debug(f"开始更新删除后的缩略图，删除页码: {delete_page_num}")
        if not self.pdf_processor or not self.pdf_processor.fitz_document:
            logger.debug("PDF处理器或文档不存在")
            return
            
        try:
            # 首先删除指定位置的缩略图
            logger.debug(f"当前缩略图数量: {self.count()}")
            if delete_page_num <= self.count():
                logger.debug(f"删除第{delete_page_num}页的缩略图")
                self.takeItem(delete_page_num - 1)
                
            # 然后更新删除点之后的所有页面编号
            logger.debug("更新后续页面编号")
            for i in range(delete_page_num - 1, self.count()):
                item = self.item(i)
                if item:
                    item.setText(f"第 {i + 1} 页")  # 所有后续页面编号恢复正常
                    logger.debug(f"更新第{i+1}页的文本显示")
            logger.debug("删除后缩略图更新完成")
        except Exception as e:
            logger.error(f"删除后更新缩略图失败: {e}")
            
    def _update_thumbnail_async(self, page_num):
        """异步更新单个缩略图"""
        if not self.pdf_processor or not self.pdf_processor.fitz_document:
            return
            
        # 取消之前的加载任务
        if self.async_loader and self.async_loader.isRunning():
            self.async_loader.cancel()
            self.async_loader.wait()
            
        # 创建异步加载器
        self.async_loader = AsyncThumbnailLoader(self.pdf_processor, [page_num])
        
        # 连接信号
        self.async_loader.thumbnail_ready.connect(self._on_thumbnail_ready)
        
        # 开始异步加载
        self.async_loader.start()