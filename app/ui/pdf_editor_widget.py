"""PDF编辑器组件，包含完整的UI（菜单栏+工具栏+内容区域）"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout,
                             QMenuBar, QToolBar, QSplitter,
                             QStackedWidget,
                             QLabel, QMessageBox, QAction,
                             QSizePolicy, QFileDialog)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
import os

from app.core.processing.pdf_processor import PDFProcessor
from app.core.processing.thumbnail_manager import ThumbnailManager
from app.ui.virtual_scroll import VirtualScrollArea
from app.ui.menu_manager import MenuManager
from app.ui.context_menu_manager import ContextMenuManager
from app.ui.password_dialog import PasswordDialog
from app.managers.history_manager import HistoryManager
from app.managers.view_controller import ViewController
from app.managers.search_manager import SearchManager
from app.managers.split_manager import SplitManager
from app.managers.merge_manager import MergeManager
from app.ui.welcome_widget import WelcomeWidget
from app.utils.logger import get_logger
from app.config.settings import AppSettings


logger = get_logger('pdf_editor_widget')


class PDFEditorWidget(QWidget):
    """独立的PDF编辑器组件，包含完整的UI"""

    # 信号定义
    file_opened = pyqtSignal(str)  # 文件打开时发出
    file_saved = pyqtSignal(str)  # 文件保存时发出
    tab_title_changed = pyqtSignal(str)  # 标题改变时发出

    def __init__(self, file_path=None, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.tab_index = -1
        self.unsaved_changes = False

        # 初始化PDF处理器
        self.pdf_processor = PDFProcessor()

        # 初始化管理器
        self.view_controller = ViewController(self)
        self.search_manager = SearchManager(self)
        self.split_manager = SplitManager(self)
        self.merge_manager = MergeManager(self)
        self.history_manager = HistoryManager(self)
        self.context_menu_manager = ContextMenuManager(self)

        # 初始化UI
        self.init_ui()

        # 如果有文件路径，打开文件
        if file_path and os.path.exists(file_path):
            self.open_pdf(file_path)

    def init_ui(self):
        """初始化UI"""
        # 主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. 菜单栏
        self.menu_bar = QMenuBar()
        self.menu_manager = MenuManager(self)
        self.menu_manager.create_menubar(self.menu_bar)
        layout.addWidget(self.menu_bar)

        # 2. 工具栏
        self.tool_bar = QToolBar()
        self.tool_bar.setMovable(False)
        # 手动创建工具栏内容
        self._create_toolbar_content()
        layout.addWidget(self.tool_bar)

        # 3. 内容容器（用于切换PDF查看器和欢迎界面）
        self.content_stack = QStackedWidget()
        # 设置大小策略，使其能扩展占满剩余空间
        size_policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.content_stack.setSizePolicy(size_policy)
        layout.addWidget(self.content_stack)

        # 4. 内容区域（分割器）
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.setHandleWidth(1)

        # 左侧缩略图
        self.thumbnail_manager = ThumbnailManager(self)
        self.thumbnail_manager.set_pdf_processor(self.pdf_processor)
        self.thumbnail_panel = self.thumbnail_manager
        # 确保thumbnail_panel初始可见（虽然通过splitter的size设置为0隐藏，但widget本身要可见）
        self.thumbnail_panel.setVisible(True)
        # 连接缩略图点击信号
        self.thumbnail_manager.thumbnail_clicked.connect(self.on_thumbnail_clicked)
        self.thumbnail_manager.thumbnail_right_clicked.connect(self.on_thumbnail_right_clicked)
        self.main_splitter.addWidget(self.thumbnail_panel)

        # 右侧PDF查看器
        self.scroll_area = VirtualScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setMouseTracking(True)
        # 连接页面变更信号，用于更新工具栏页码显示
        self.scroll_area.page_changed.connect(self._on_scroll_page_changed)
        self.main_splitter.addWidget(self.scroll_area)

        # 设置分割器比例
        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 4)
        # 默认隐藏缩略图（宽度为0）
        self.main_splitter.setSizes([0, 1000])

        self.content_stack.addWidget(self.main_splitter)

        # 5. 欢迎界面（历史记录）
        self.welcome_widget = WelcomeWidget(self, self.history_manager)
        self.welcome_widget.file_open_requested.connect(self.open_pdf)
        self.welcome_widget.close_requested.connect(self.show_pdf_viewer)
        self.content_stack.addWidget(self.welcome_widget)

        # 默认显示PDF查看器或欢迎界面
        if self.file_path:
            self.show_pdf_viewer()
        else:
            self.show_welcome()

    def open_pdf(self, file_path):
        """打开指定的PDF文件"""
        try:
            success, message = self.pdf_processor.open_pdf(file_path, async_mode=True)
            if success:
                self.file_path = file_path
                self.unsaved_changes = False
                self.update_tab_title(os.path.basename(file_path))
                self.show_pdf_viewer()
                self.file_opened.emit(file_path)
                logger.info(f"文件打开成功: {file_path}")

                # 异步添加文件到历史记录（不阻塞UI）
                if hasattr(self, 'history_manager') and self.history_manager:
                    try:
                        total_pages = self.pdf_processor.get_total_pages()
                        logger.debug(f"[open_pdf] 准备添加到历史记录: file_path={file_path}, total_pages={total_pages}")
                        # 使用QTimer延迟执行，确保不阻塞渲染
                        QTimer.singleShot(100, lambda: self._async_add_to_history(file_path, total_pages))
                    except Exception as e:
                        logger.error(f"准备添加历史记录失败: {e}")
                        import traceback
                        traceback.print_exc()

                # 更新工具栏的总页数标签
                if hasattr(self, 'toolbar_total_pages_label') and self.pdf_processor:
                    try:
                        total_pages = self.pdf_processor.get_total_pages()
                        self.toolbar_total_pages_label.setText(f"/ {total_pages}")
                    except Exception as e:
                        logger.error(f"更新工具栏总页数显示失败: {e}")
                        if hasattr(self, 'toolbar_total_pages_label'):
                            self.toolbar_total_pages_label.setText("/ 0")

                # 更新虚拟滚动区域内容
                logger.debug(f"[open_pdf] 准备更新虚拟滚动区域")
                logger.debug(f"[open_pdf] hasattr(scroll_area): {hasattr(self, 'scroll_area')}")
                logger.debug(f"[open_pdf] pdf_processor: {self.pdf_processor}")
                logger.debug(f"[open_pdf] fitz_document: {self.pdf_processor.fitz_document if self.pdf_processor else 'N/A'}")
                if hasattr(self, 'scroll_area') and self.pdf_processor.fitz_document:
                    try:
                        # 构建页面数据
                        total_pages = self.pdf_processor.get_total_pages()
                        pages_data = []
                        for page_num in range(total_pages):
                            # 获取页面尺寸（应用自动缩放，但不乘zoom_factor）
                            page_dimensions = self.pdf_processor.get_page_dimensions(page_num, apply_auto_scaling=True)
                            if page_dimensions:
                                # 存储应用了自动缩放后的尺寸，render_page_at会乘以zoom_factor
                                width = int(page_dimensions['width'])
                                height = int(page_dimensions['height'])
                            else:
                                width = 800  # 默认宽度
                                height = 1100  # 默认高度

                            pages_data.append({
                                'page_num': page_num,
                                'width': width,
                                'height': height,
                                'zoom_factor': self.pdf_processor.zoom_factor
                            })

                        self.scroll_area.set_pages_data(pages_data)

                        # 触发虚拟滚动区域更新和渲染
                        self.scroll_area.update_content()

                        # 延迟滚动到第一页
                        QTimer.singleShot(200, lambda: self.scroll_area.scroll_to_page(0) if hasattr(self.scroll_area, 'scroll_to_page') else None)

                        # 根据设置决定是否显示缩略图
                        show_thumbnails = AppSettings.get_show_thumbnails_default()
                        if show_thumbnails:
                            # 显示缩略图面板并加载缩略图
                            logger.debug("显示缩略图面板")
                            # 确保thumbnail_panel可见
                            self.thumbnail_panel.setVisible(True)
                            self.thumbnail_panel.show()
                            self.thumbnail_panel.raise_()
                            # 设置分割器大小，使用更大的值确保缩略图面板有足够宽度
                            self.main_splitter.setSizes([220, 1000])
                            # 延迟再次设置，确保生效
                            QTimer.singleShot(50, lambda: self.main_splitter.setSizes([220, 1000]))
                            sizes = self.main_splitter.sizes()
                            logger.info(f"设置分割器大小: {sizes} (缩略图: {sizes[0]}, 文档: {sizes[1]})")
                            logger.info(f"缩略图面板可见性: {self.thumbnail_panel.isVisible()}")
                            logger.info(f"缩略图面板尺寸: {self.thumbnail_panel.size().width()}x{self.thumbnail_panel.size().height()}")
                            # 强制更新
                            self.main_splitter.updateGeometry()
                            self.main_splitter.update()
                            self.thumbnail_panel.updateGeometry()
                            self.thumbnail_panel.update()
                            # 更新工具栏缩略图按钮为选中状态（不触发信号）
                            if hasattr(self, 'tool_bar'):
                                for action in self.tool_bar.actions():
                                    if action.text().startswith("🖼️ 缩略图"):
                                        action.blockSignals(True)
                                        action.setChecked(True)
                                        action.blockSignals(False)
                                        break
                            logger.debug("开始加载缩略图")
                            self.load_thumbnails()
                            # 延迟检查，确保缩略图已经加载
                            QTimer.singleShot(500, self._check_thumbnail_panel)
                        else:
                            # 不显示缩略图
                            logger.debug("不显示缩略图面板")
                            self.thumbnail_panel.setVisible(False)
                            self.thumbnail_panel.hide()
                            self.main_splitter.setSizes([0, 1000])
                            # 更新工具栏缩略图按钮为未选中状态（不触发信号）
                            if hasattr(self, 'tool_bar'):
                                for action in self.tool_bar.actions():
                                    if action.text().startswith("🖼️ 缩略图"):
                                        action.blockSignals(True)
                                        action.setChecked(False)
                                        action.blockSignals(False)
                                        break
                    except Exception as e:
                        logger.error(f"设置虚拟滚动页面数据失败: {e}")
                        import traceback
                        traceback.print_exc()
            else:
                QMessageBox.warning(self, "打开失败", f"无法打开文件: {file_path}\n{message}")
        except Exception as e:
            logger.error(f"打开文件失败: {e}")
            QMessageBox.critical(self, "错误", f"打开文件时出错: {str(e)}")

    def _async_add_to_history(self, file_path, page_count):
        """异步添加文件到历史记录"""
        try:
            logger.debug(f"[_async_add_to_history] 准备添加到历史记录: file_path={file_path}, page_count={page_count}")
            if hasattr(self, 'history_manager') and self.history_manager:
                self.history_manager.add_file_to_history(file_path, page_count)
                logger.info(f"[_async_add_to_history] 已异步添加到历史记录: {os.path.basename(file_path)}")
                # 如果欢迎界面正在显示，刷新历史记录
                if hasattr(self, 'welcome_widget') and self.welcome_widget:
                    self.welcome_widget.refresh_history()
            else:
                logger.warning("[_async_add_to_history] history_manager 未初始化，无法添加历史记录")
        except Exception as e:
            logger.error(f"异步添加历史记录失败: {e}")

    def _check_thumbnail_panel(self):
        """检查缩略图面板状态（用于调试）"""
        logger.info(f"=== 缩略图面板状态检查 ===")
        logger.info(f"缩略图面板可见性: {self.thumbnail_panel.isVisible()}")
        logger.info(f"缩略图面板尺寸: {self.thumbnail_panel.size().width()}x{self.thumbnail_panel.size().height()}")
        logger.info(f"缩略图面板最小宽度: {self.thumbnail_panel.minimumWidth()}")
        logger.info(f"缩略图面板项目数量: {self.thumbnail_panel.count()}")
        logger.info(f"缩略图面板是否有布局: {self.thumbnail_panel.layout() is not None}")
        if self.thumbnail_panel.count() > 0:
            logger.info(f"第一个项目: {self.thumbnail_panel.item(0).text()}")
            logger.info(f"第一个项目图标: {self.thumbnail_panel.item(0).icon().isNull()}")

    def save_file(self, file_path=None):
        """保存文件"""
        try:
            save_path = file_path or self.file_path
            if not save_path:
                return False

            success, message = self.pdf_processor.save_pdf(save_path)
            if success:
                self.file_path = save_path
                self.unsaved_changes = False
                self.update_tab_title(os.path.basename(save_path))
                self.file_saved.emit(save_path)
                logger.info(f"文件保存成功: {save_path}")
                return True
            else:
                QMessageBox.warning(self, "保存失败", f"无法保存文件: {save_path}\n{message}")
                return False
        except Exception as e:
            logger.error(f"保存文件失败: {e}")
            QMessageBox.critical(self, "错误", f"保存文件时出错: {str(e)}")
            return False

    def show_pdf_viewer(self):
        """显示PDF查看器"""
        if self.content_stack.currentWidget() != self.main_splitter:
            self.content_stack.setCurrentWidget(self.main_splitter)

    def show_welcome(self):
        """显示欢迎界面（历史记录）"""
        if self.content_stack.currentWidget() != self.welcome_widget:
            # 隐藏缩略图面板
            self.main_splitter.setSizes([0, 1000])
            self.content_stack.setCurrentWidget(self.welcome_widget)

    def toggle_history(self):
        """切换历史记录/PDF查看器"""
        if self.content_stack.currentWidget() == self.welcome_widget:
            self.show_pdf_viewer()
        else:
            self.show_welcome()

    def update_tab_title(self, title):
        """更新标签页标题"""
        if self.unsaved_changes:
            title = f"* {title}"
        self.tab_title_changed.emit(title)

    def mark_unsaved(self):
        """标记为未保存"""
        self.unsaved_changes = True
        self.update_tab_title(os.path.basename(self.file_path) if self.file_path else "未命名")

    def has_unsaved_changes(self):
        """是否有未保存的更改"""
        return self.unsaved_changes

    def closeEvent(self, a0):
        """关闭事件处理"""
        self.pdf_processor.cleanup_cache()
        a0.accept()

    # === MenuManager 和 ToolbarManager 需要的方法 ===

    def open_file(self):
        """打开文件（菜单管理器调用）"""
        from PyQt5.QtWidgets import QFileDialog
        last_open_dir = AppSettings.get_last_open_dir()
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "打开PDF文件",
            last_open_dir,
            "PDF文件 (*.pdf);;所有文件 (*.*)"
        )
        if file_path:
            self.open_pdf(file_path)

    def save_as_file(self):
        """另存为（菜单管理器调用）"""
        self._save_as_file_dialog()

    def encrypt_save_file(self):
        """加密保存（直接覆盖源文档）"""
        if not self.file_path:
            QMessageBox.information(self, "提示", "📝 请先打开PDF文件")
            return

        password = PasswordDialog.get_user_password(self, "请输入加密密码")
        if password is None:
            return

        if not password:
            QMessageBox.warning(self, "提示", "密码不能为空")
            return

        success, message = self.pdf_processor.encrypt_pdf(password, self.file_path)
        if success:
            QMessageBox.information(self, "保存成功", "文件已加密保存")
            logger.info(f"文件加密保存成功: {self.file_path}")
        else:
            QMessageBox.critical(self, "加密保存失败", message)

    def encrypt_save_as_file(self):
        """加密另存为（选择新目录存储成新文档）"""
        if not self.file_path:
            QMessageBox.information(self, "提示", "📝 请先打开PDF文件")
            return

        # 获取默认保存路径
        last_save_dir = AppSettings.get_last_save_dir()
        default_path = os.path.join(last_save_dir if last_save_dir else os.path.expanduser("~"),
                                   os.path.basename(self.file_path))

        # 选择保存路径
        file_path, _ = QFileDialog.getSaveFileName(
            self, "加密另存为PDF文件", default_path, "PDF文件 (*.pdf)")

        if not file_path:
            return

        # 输入密码
        password = PasswordDialog.get_user_password(self, "请输入加密密码")
        if password is None:
            return

        if not password:
            QMessageBox.warning(self, "提示", "密码不能为空")
            return

        success, message = self.pdf_processor.encrypt_pdf(password, file_path)
        if success:
            QMessageBox.information(self, "保存成功", message)
            AppSettings.set_last_save_dir(os.path.dirname(file_path))
            logger.info(f"文件加密另存为成功: {file_path}")
        else:
            QMessageBox.critical(self, "加密保存失败", message)

    # === 视图控制方法 ===
    def zoom_in(self):
        """放大"""
        self.view_controller.zoom_in()

    def zoom_out(self):
        """缩小"""
        self.view_controller.zoom_out()

    def fit_to_width(self):
        """适应宽度"""
        # 获取容器宽度
        container_width = None
        if hasattr(self, 'scroll_area') and hasattr(self.scroll_area, 'get_container_size'):
            width, _ = self.scroll_area.get_container_size()
            container_width = width
        self.view_controller.fit_to_width(container_width)

    def fit_to_height(self):
        """适应高度"""
        # 获取容器高度
        container_height = None
        if hasattr(self, 'scroll_area') and hasattr(self.scroll_area, 'get_container_size'):
            _, height = self.scroll_area.get_container_size()
            container_height = height
        self.view_controller.fit_to_height(container_height)

    def set_actual_size(self):
        """原始尺寸"""
        self.view_controller.set_actual_size()

    def toggle_actual_size(self):
        """切换实际大小（A4缩放）"""
        if hasattr(self, 'pdf_processor') and self.pdf_processor:
            current_a4_scaling = self.pdf_processor.get_use_a4_scaling()
            new_a4_scaling = not current_a4_scaling
            self.pdf_processor.set_use_a4_scaling(new_a4_scaling)

            if hasattr(self, 'actual_size_action'):
                self.actual_size_action.setChecked(not new_a4_scaling)

            # 重新渲染
            if hasattr(self.scroll_area, 'update_content'):
                self.scroll_area.update_content()
            logger.info(f"切换页面缩放模式: {'使用A4缩放' if new_a4_scaling else '使用实际大小'}")

    def set_zoom_level(self, level):
        """设置缩放级别"""
        self.view_controller.set_zoom_level(level)

    def on_zoom_combo_changed(self, text):
        """缩放下拉框变化"""
        if '%' in text:
            level = float(text.rstrip('%'))
            self.set_zoom_level(level)

    def _update_zoom_combo_display(self):
        """更新工具栏缩放比例显示"""
        if hasattr(self, 'zoom_combo') and hasattr(self.pdf_processor, 'get_zoom'):
            try:
                # 获取当前缩放比例
                current_zoom = self.pdf_processor.get_zoom()
                zoom_percent = int(current_zoom * 100)
                # 阻止信号，避免循环触发
                self.zoom_combo.blockSignals(True)

                # 检查是否在预设值列表中
                zoom_text = f"{zoom_percent}%"
                index = self.zoom_combo.findText(zoom_text)

                if index >= 0:
                    # 如果在预设值中，选择该项
                    self.zoom_combo.setCurrentIndex(index)
                else:
                    # 如果不在预设值中，查找最接近的预设值
                    closest_zoom = self._find_closest_zoom_level(zoom_percent)
                    if closest_zoom is not None:
                        self.zoom_combo.setCurrentText(f"{closest_zoom}%")
                    else:
                        # 如果找不到合适的预设值，直接设置文本
                        self.zoom_combo.setCurrentText(zoom_text)

                self.zoom_combo.blockSignals(False)
            except Exception as e:
                logger.error(f"更新工具栏缩放显示失败: {e}")

    def _find_closest_zoom_level(self, target_percent):
        """查找最接近目标缩放比例的预设值"""
        if not hasattr(self, 'zoom_combo'):
            return None

        # 获取所有预设的缩放比例
        preset_zooms = []
        for i in range(self.zoom_combo.count()):
            text = self.zoom_combo.itemText(i)
            if '%' in text:
                preset_zooms.append(int(text.rstrip('%')))

        if not preset_zooms:
            return None

        # 找到最接近的预设值
        closest = min(preset_zooms, key=lambda x: abs(x - target_percent))
        return closest

    def previous_page(self):
        """上一页"""
        self.view_controller.previous_page()

    def next_page(self):
        """下一页"""
        self.view_controller.next_page()

    def go_to_page(self, page_number=None):
        """跳转页码"""
        self.view_controller.go_to_page(page_number)

    def _on_page_spinbox_changed(self, value):
        """页码框变化"""
        self.view_controller.on_page_spinbox_changed(value)

    def _on_scroll_page_changed(self, page_num):
        """滚动时页面变更"""
        """更新工具栏页码显示"""
        if hasattr(self, 'page_spinbox'):
            # 阻止信号，避免循环触发
            self.page_spinbox.blockSignals(True)
            self.page_spinbox.setValue(page_num)
            self.page_spinbox.blockSignals(False)

        # 更新缩略图选中状态
        if hasattr(self, 'thumbnail_manager'):
            self.thumbnail_manager.update_thumbnail_selection(page_num)

    def toggle_thumbnails(self, checked):
        """切换缩略图显示/隐藏"""
        logger.info(f"toggle_thumbnails 被调用，checked={checked}")
        # 获取分割器中所有widget的索引
        thumbnail_index = self.main_splitter.indexOf(self.thumbnail_panel)
        if thumbnail_index >= 0:
            sizes_before = self.main_splitter.sizes()
            logger.info(f"toggle_thumbnails - 当前sizes: {sizes_before}")
            if checked:
                # 显示缩略图：恢复到220px（与打开文件时一致）
                self.main_splitter.setSizes([220, 1000])
                self.thumbnail_panel.setVisible(True)
                self.thumbnail_panel.show()
                logger.info("显示缩略图面板")
                # 检查是否需要加载缩略图
                if self.thumbnail_panel.count() == 0 and self.pdf_processor and self.pdf_processor.fitz_document:
                    logger.info("缩略图列表为空，开始加载缩略图")
                    self.load_thumbnails()
                else:
                    logger.info(f"缩略图已存在，数量: {self.thumbnail_panel.count()}")
            else:
                # 隐藏缩略图：设置为0
                self.main_splitter.setSizes([0, 1000])
                self.thumbnail_panel.hide()
                logger.info("隐藏缩略图面板")
            sizes_after = self.main_splitter.sizes()
            logger.info(f"toggle_thumbnails - 设置后sizes: {sizes_after}")

    def load_thumbnails(self):
        """加载缩略图"""
        logger.info(f"[load_thumbnails] 开始执行")
        logger.info(f"[load_thumbnails] pdf_processor存在: {self.pdf_processor is not None}")
        logger.info(f"[load_thumbnails] pdf_processor类型: {type(self.pdf_processor)}")
        fitz_doc = self.pdf_processor.fitz_document if self.pdf_processor else None
        logger.info(f"[load_thumbnails] fitz_document存在: {fitz_doc is not None}")
        logger.info(f"[load_thumbnails] fitz_document值: {fitz_doc}")
        logger.info(f"[load_thumbnails] fitz_document布尔值: {bool(fitz_doc)}")
        logger.info(f"[load_thumbnails] thumbnail_manager存在: {self.thumbnail_manager is not None}")
        logger.info(f"[load_thumbnails] thumbnail_manager布尔值: {bool(self.thumbnail_manager)}")
        # 修改条件判断，使用 is not None 而不是依赖布尔值
        if self.pdf_processor is not None and fitz_doc is not None and self.thumbnail_manager is not None:
            logger.info("[load_thumbnails] 开始调用thumbnail_manager.load_thumbnails()")
            self.thumbnail_manager.load_thumbnails()
            logger.info("[load_thumbnails] thumbnail_manager.load_thumbnails()调用完成")
        else:
            logger.warning(f"[load_thumbnails] 无法加载缩略图")
            logger.warning(f"[load_thumbnails] pdf_processor: {self.pdf_processor is not None}")
            logger.warning(f"[load_thumbnails] fitz_document: {fitz_doc is not None}")
            logger.warning(f"[load_thumbnails] thumbnail_manager: {self.thumbnail_manager is not None}")

    def on_thumbnail_clicked(self, page_num):
        """缩略图点击"""
        self.view_controller.on_thumbnail_clicked(page_num)

    def on_thumbnail_right_clicked(self, page_num):
        """缩略图右键点击"""
        self.view_controller.on_thumbnail_right_clicked(page_num)

    def update_thumbnail_selection(self, current_page):
        """更新缩略图选择"""
        self.view_controller.update_thumbnail_selection(current_page)

    # === 工具菜单方法 ===
    def import_images(self):
        """导入图片"""
        logger.warning("导入图片功能暂未实现")
        QMessageBox.information(self, "提示", "导入图片功能暂未实现")

    def convert_pdf_to_images(self):
        """转为图片"""
        logger.warning("转为图片功能暂未实现")
        QMessageBox.information(self, "提示", "转为图片功能暂未实现")

    def split_pdf(self):
        """分割PDF"""
        self.split_manager.show_split_dialog()

    def merge_pdf(self):
        """合并PDF"""
        self.merge_manager.show_merge_dialog()

    def show_ocr_settings(self):
        """OCR设置"""
        logger.warning("OCR设置功能暂未实现")
        QMessageBox.information(self, "提示", "OCR设置功能暂未实现")

    def start_screenshot_ocr_mode(self):
        """截图OCR"""
        logger.warning("截图OCR功能暂未实现")
        QMessageBox.information(self, "提示", "截图OCR功能暂未实现")

    def perform_ocr_on_current_page(self):
        """对当前页执行OCR"""
        logger.warning("对当前页执行OCR功能暂未实现")
        QMessageBox.information(self, "提示", "对当前页执行OCR功能暂未实现")

    def perform_ocr_on_all_pages(self):
        """对全部页面执行OCR"""
        logger.warning("对全部页面执行OCR功能暂未实现")
        QMessageBox.information(self, "提示", "对全部页面执行OCR功能暂未实现")

    def create_searchable_pdf(self):
        """创建可搜索PDF"""
        logger.warning("创建可搜索PDF功能暂未实现")
        QMessageBox.information(self, "提示", "创建可搜索PDF功能暂未实现")

    def toggle_ocr_debug_mode(self):
        """OCR文本层高亮模式"""
        from app.config.settings import AppSettings
        current = AppSettings.get_ocr_highlight_mode()
        AppSettings.set_ocr_highlight_mode(not current)
        if hasattr(self.scroll_area, 'update_content'):
            self.scroll_area.update_content()
        logger.info(f"OCR高亮模式: {'开启' if not current else '关闭'}")

    def show_storage_settings(self):
        """云存储插件设置"""
        logger.warning("云存储插件设置功能暂未实现")
        QMessageBox.information(self, "提示", "云存储插件设置功能暂未实现")

    def show_barcode_settings(self):
        """条码拆分"""
        logger.warning("条码拆分功能暂未实现")
        QMessageBox.information(self, "提示", "条码拆分功能暂未实现")

    def show_batch_crypto_dialog(self):
        """批量加解密"""
        logger.warning("批量加解密功能暂未实现")
        QMessageBox.information(self, "提示", "批量加解密功能暂未实现")

    def show_search_panel(self):
        """搜索"""
        self.search_manager.show_search_panel()

    # === 设置菜单方法 ===
    def show_ui_settings(self):
        """界面设置"""
        logger.warning("界面设置功能暂未实现")
        QMessageBox.information(self, "提示", "界面设置功能暂未实现")

    def show_shortcut_settings(self):
        """快捷键设置"""
        logger.warning("快捷键设置功能暂未实现")
        QMessageBox.information(self, "提示", "快捷键设置功能暂未实现")

    # === 帮助菜单方法 ===
    def show_about(self):
        """关于"""
        QMessageBox.about(self, "关于 PDFAssistant",
                         "PDFAssistant - PDF编辑助手\n\n"
                         "版本: 1.0\n"
                         "多标签页模式")

    def _create_toolbar_content(self):
        """创建工具栏内容"""
        from PyQt5.QtCore import QSize

        self.tool_bar.setIconSize(QSize(32, 32))

        # 文件操作
        open_btn = QAction("📂 打开", self)
        open_btn.setToolTip("打开PDF文件 (Ctrl+O)")
        open_btn.triggered.connect(self.open_file)
        self.tool_bar.addAction(open_btn)

        save_btn = QAction("💾 保存", self)
        save_btn.setToolTip("保存PDF文件 (Ctrl+S)")
        save_btn.triggered.connect(self._save_file)
        self.tool_bar.addAction(save_btn)

        save_as_btn = QAction("💾 另存为", self)
        save_as_btn.setToolTip("另存为PDF文件 (Ctrl+Shift+S)")
        save_as_btn.triggered.connect(self.save_as_file)
        self.tool_bar.addAction(save_as_btn)

        self.tool_bar.addSeparator()

        # 视图控制
        thumbnail_btn = QAction("🖼️ 缩略图", self)
        thumbnail_btn.setToolTip("显示/隐藏缩略图")
        thumbnail_btn.setCheckable(True)
        thumbnail_btn.setChecked(False)
        thumbnail_btn.toggled.connect(self.toggle_thumbnails)
        self.tool_bar.addAction(thumbnail_btn)

        zoom_in_btn = QAction("➕ 放大", self)
        zoom_in_btn.setToolTip("放大页面 (Ctrl++)")
        zoom_in_btn.triggered.connect(self.zoom_in)
        self.tool_bar.addAction(zoom_in_btn)

        zoom_out_btn = QAction("➖ 缩小", self)
        zoom_out_btn.setToolTip("缩小页面 (Ctrl+-)")
        zoom_out_btn.triggered.connect(self.zoom_out)
        self.tool_bar.addAction(zoom_out_btn)

        fit_width_btn = QAction("↔️ 适应宽度", self)
        fit_width_btn.setToolTip("适应页面宽度")
        fit_width_btn.triggered.connect(self.fit_to_width)
        self.tool_bar.addAction(fit_width_btn)

        # 缩放下拉框
        from PyQt5.QtWidgets import QComboBox
        self.zoom_combo = QComboBox()
        self.zoom_combo.setEditable(True)
        self.zoom_combo.setFixedWidth(100)
        self.zoom_combo.setToolTip("选择缩放比例")
        zoom_levels = ["8%", "12.5%", "25%", "50%", "75%", "100%", "125%", "150%", "200%", "300%", "400%", "600%", "800%"]
        self.zoom_combo.addItems(zoom_levels)
        self.zoom_combo.setCurrentText("100%")
        self.zoom_combo.currentTextChanged.connect(self.on_zoom_combo_changed)
        self.tool_bar.addWidget(QLabel(" 缩放:"))
        self.tool_bar.addWidget(self.zoom_combo)

        self.tool_bar.addSeparator()

        # 导航
        prev_page_btn = QAction("⬅️ 上一页", self)
        prev_page_btn.setToolTip("上一页 (PgUp)")
        prev_page_btn.setShortcut("PgUp")
        prev_page_btn.triggered.connect(self.previous_page)
        self.tool_bar.addAction(prev_page_btn)

        next_page_btn = QAction("➡️ 下一页", self)
        next_page_btn.setToolTip("下一页 (PgDown)")
        next_page_btn.setShortcut("PgDown")
        next_page_btn.triggered.connect(self.next_page)
        self.tool_bar.addAction(next_page_btn)

        # 页码输入框
        from PyQt5.QtWidgets import QSpinBox
        self.page_spinbox = QSpinBox()
        self.page_spinbox.setFixedWidth(60)
        self.page_spinbox.setAlignment(Qt.AlignCenter)
        self.page_spinbox.setMinimum(1)
        self.page_spinbox.setValue(1)
        self.page_spinbox.setToolTip("当前页码")
        self.page_spinbox.valueChanged.connect(self._on_page_spinbox_changed)
        self.page_spinbox.editingFinished.connect(self.go_to_page)
        self.tool_bar.addWidget(self.page_spinbox)

        self.toolbar_total_pages_label = QLabel("/ 0")
        self.toolbar_total_pages_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 12px;
                padding: 0px 2px;
            }
        """)
        self.tool_bar.addWidget(self.toolbar_total_pages_label)

        self.tool_bar.addSeparator()

        # 工具
        search_btn = QAction("🔍 搜索", self)
        search_btn.setToolTip("搜索 (Ctrl+F)")
        search_btn.triggered.connect(self.show_search_panel)
        self.tool_bar.addAction(search_btn)

    # === 其他辅助方法 ===
    def _open_file_dialog(self):
        """打开文件对话框"""
        self.open_file()

    def _save_file(self):
        """保存文件"""
        if self.file_path:
            self.save_file(self.file_path)
        else:
            self._save_as_file_dialog()

    def _save_as_file_dialog(self):
        """另存为对话框"""
        from PyQt5.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存PDF文件",
            self.file_path or "",
            "PDF文件 (*.pdf);;所有文件 (*.*)"
        )
        if file_path:
            self.save_file(file_path)

    def _close_tab(self):
        """关闭标签页"""
        self.close()

    def _set_zoom_level(self, level):
        """设置缩放级别"""
        self.set_zoom_level(level)

    def show_message(self, message):
        """显示消息到状态栏（如果有）"""
        logger.info(message)

    def _open_file_dialog(self):
        """打开文件对话框"""
        from PyQt5.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "打开PDF文件",
            "",
            "PDF文件 (*.pdf);;所有文件 (*.*)"
        )
        if file_path:
            self.open_file(file_path)

    def _save_file(self):
        """保存文件"""
        if self.file_path:
            self.save_file(self.file_path)
        else:
            self._save_as_file_dialog()

    def _save_as_file_dialog(self):
        """另存为对话框"""
        from PyQt5.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存PDF文件",
            self.file_path or "",
            "PDF文件 (*.pdf);;所有文件 (*.*)"
        )
        if file_path:
            self.save_file(file_path)

    def _close_tab(self):
        """关闭标签页"""
        # 这个信号会被 TabbedMainWindow 捕获并处理
        self.close()

    def _set_zoom_level(self, level):
        """设置缩放级别"""
        if self.view_controller:
            self.view_controller.set_zoom_level(level / 100.0)
