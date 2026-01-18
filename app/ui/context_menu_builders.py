"""右键菜单构建器"""
import tempfile
import uuid
import os
import traceback
from PyQt5.QtWidgets import QMenu, QAction
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QFileDialog, QMessageBox
from PyQt5.QtCore import QTimer
from app.utils.logger import get_logger
from app.core.editing.page_editor import PageEditor
import fitz
from app.core.ocr.ocr_plugin_interface import OCRResult
from app.core.ocr.ocr_plugin_interface import OCRErrorCode
from base64 import b64encode
from app.ui.screenshot_result_dialog import ScreenshotOCRResultDialog

logger = get_logger(__name__)


class ContextType:
    """上下文类型枚举"""
    GENERAL = "general"
    TEXT = "text"
    PAGE = "page"
    THUMBNAIL = "thumbnail"


class ContextMenuBuilder:
    """右键菜单构建器基类"""

    def __init__(self, main_window):
        self.main_window = main_window

    def _get_page_editor(self):
        """获取页面编辑器"""
        logger.debug("尝试获取page_editor")
        
        # 首先尝试从thumbnail_manager获取page_editor，这是最可靠的位置
        if (hasattr(self.main_window, 'thumbnail_list') and 
            self.main_window.thumbnail_list and 
            hasattr(self.main_window.thumbnail_list, 'page_editor') and 
            self.main_window.thumbnail_list.page_editor):
            logger.debug(f"从thumbnail_list获取到page_editor: {self.main_window.thumbnail_list.page_editor}")
            # 确保同步到pdf_processor
            if hasattr(self.main_window, 'pdf_processor') and self.main_window.pdf_processor:
                self.main_window.pdf_processor.page_editor = self.main_window.thumbnail_list.page_editor
            return self.main_window.thumbnail_list.page_editor
        else:
            logger.debug("thumbnail_list没有page_editor或其值为None")
        
        # 尝试从pdf_processor获取page_editor
        if (hasattr(self.main_window, 'pdf_processor') and 
            hasattr(self.main_window.pdf_processor, 'page_editor') and 
            self.main_window.pdf_processor.page_editor):
            logger.debug(f"从pdf_processor获取到page_editor: {self.main_window.pdf_processor.page_editor}")
            # 确保同步到thumbnail_list
            if hasattr(self.main_window, 'thumbnail_list') and self.main_window.thumbnail_list:
                self.main_window.thumbnail_list.page_editor = self.main_window.pdf_processor.page_editor
            return self.main_window.pdf_processor.page_editor
        else:
            logger.debug("pdf_processor没有page_editor属性或其值为None")
        
        # 尝试从main_window直接获取page_editor（如果存在）
        if hasattr(self.main_window, 'page_editor') and self.main_window.page_editor:
            logger.debug(f"从main_window获取到page_editor: {self.main_window.page_editor}")
            # 确保同步到pdf_processor和thumbnail_list
            if hasattr(self.main_window, 'pdf_processor') and self.main_window.pdf_processor:
                self.main_window.pdf_processor.page_editor = self.main_window.page_editor
            if hasattr(self.main_window, 'thumbnail_list') and self.main_window.thumbnail_list:
                self.main_window.thumbnail_list.page_editor = self.main_window.page_editor
            return self.main_window.page_editor

        # 如果以上都没有找到page_editor，则创建一个新的实例
        logger.debug("所有位置都没有找到page_editor，尝试创建新的PageEditor实例")
        if hasattr(self.main_window, 'pdf_processor'):
            logger.debug("使用pdf_processor创建新的PageEditor实例")
            new_page_editor = PageEditor(self.main_window.pdf_processor)
            # 同时设置到pdf_processor和thumbnail_list，以便后续使用
            self.main_window.pdf_processor.page_editor = new_page_editor
            if hasattr(self.main_window, 'thumbnail_list') and self.main_window.thumbnail_list:
                self.main_window.thumbnail_list.page_editor = new_page_editor
                logger.debug(f"将page_editor也设置到thumbnail_list: {new_page_editor}")
            logger.debug(f"创建新的PageEditor实例: {new_page_editor}")
            return new_page_editor

        logger.warning("无法获取page_editor")
        return None
    
    def build_menu(self, context_type, **kwargs):
        """构建菜单"""
        if context_type == ContextType.TEXT:
            return self.build_text_menu(**kwargs)
        elif context_type == ContextType.PAGE:
            return self.build_page_menu(**kwargs)
        elif context_type == ContextType.THUMBNAIL:
            return self.build_thumbnail_menu(**kwargs)
        else:
            return self.build_general_menu(**kwargs)
    
    def build_text_menu(self, selected_text=None, **kwargs):
        """构建文本选中菜单"""
        menu = QMenu(self.main_window)
        menu.setObjectName("text_context_menu")
        
        if not selected_text:
            return self.build_general_menu(**kwargs)
        
        # 文本操作子菜单
        text_actions = self._create_text_actions(selected_text)
        for action in text_actions:
            if action is None:
                menu.addSeparator()
            else:
                menu.addAction(action)
        
        return menu
    
    def build_page_menu(self, page_num=None, **kwargs):
        """构建页面操作菜单"""
        menu = QMenu(self.main_window)
        menu.setObjectName("page_context_menu")
        
        # 页面操作
        page_actions = self._create_page_actions(page_num)
        for action in page_actions:
            if action is None:
                menu.addSeparator()
            else:
                menu.addAction(action)
        
        return menu
    
    def build_thumbnail_menu(self, page_num=None, **kwargs):
        """构建缩略图操作菜单"""
        menu = QMenu(self.main_window)
        menu.setObjectName("thumbnail_context_menu")
        
        # 缩略图操作
        thumbnail_actions = self._create_thumbnail_actions(page_num)
        for action in thumbnail_actions:
            if action is None:
                menu.addSeparator()
            else:
                menu.addAction(action)
        
        return menu
    
    def build_general_menu(self, **kwargs):
        """构建通用菜单"""
        menu = QMenu(self.main_window)
        menu.setObjectName("general_context_menu")
        
        # 文件操作
        file_actions = self._create_file_actions()
        for action in file_actions:
            if action is None:
                menu.addSeparator()
            else:
                menu.addAction(action)
        
        # 快速访问
        quick_actions = self._create_quick_access_actions()
        if quick_actions:
            menu.addSeparator()
            for action in quick_actions:
                menu.addAction(action)
        
        # 常用工具
        tool_actions = self._create_tool_actions()
        if tool_actions:
            menu.addSeparator()
            for action in tool_actions:
                menu.addAction(action)
        
        return menu
    
    def _create_text_actions(self, selected_text):
        """创建文本操作动作"""
        actions = []
        
        # 复制文本
        copy_action = QAction("复制文本", self.main_window)
        copy_action.triggered.connect(lambda: self._copy_text(selected_text))
        actions.append(copy_action)
        
        # 搜索文本
        search_action = QAction("搜索文本", self.main_window)
        search_action.triggered.connect(lambda: self._search_text(selected_text))
        actions.append(search_action)
        
        actions.append(None)
        
        # OCR识别
        ocr_action = QAction("OCR识别", self.main_window)
        ocr_action.triggered.connect(lambda: self._ocr_text(selected_text))
        actions.append(ocr_action)
        
        return actions
    
    
    def _create_page_actions(self, page_num):
        """创建页面操作动作"""
        actions = []

        # 插入子菜单
        insert_menu = QMenu("插入", self.main_window)

        # 插入空白页
        insert_blank_action = QAction("插入空白页", self.main_window)
        insert_blank_action.triggered.connect(lambda: self._insert_blank_page(page_num))
        insert_menu.addAction(insert_blank_action)

        # 插入PDF
        insert_pdf_action = QAction("插入PDF文件", self.main_window)
        insert_pdf_action.triggered.connect(lambda: self._insert_pdf_page(page_num))
        insert_menu.addAction(insert_pdf_action)

        # 插入图片
        insert_image_action = QAction("插入图片", self.main_window)
        insert_image_action.triggered.connect(lambda: self._insert_image_page(page_num))
        insert_menu.addAction(insert_image_action)

        actions.append(insert_menu.menuAction())

        actions.append(None)

        # 旋转页面子菜单
        rotate_menu = QMenu("旋转页面", self.main_window)

        rotate_90 = QAction("90°", self.main_window)
        rotate_90.triggered.connect(lambda: self._rotate_page(page_num, 90))
        rotate_menu.addAction(rotate_90)

        rotate_180 = QAction("180°", self.main_window)
        rotate_180.triggered.connect(lambda: self._rotate_page(page_num, 180))
        rotate_menu.addAction(rotate_180)

        rotate_270 = QAction("270°", self.main_window)
        rotate_270.triggered.connect(lambda: self._rotate_page(page_num, 270))
        rotate_menu.addAction(rotate_270)

        actions.append(rotate_menu.menuAction())

        actions.append(None)

        # 删除当前页
        delete_action = QAction("删除当前页", self.main_window)
        delete_action.triggered.connect(lambda: self._delete_page(page_num))
        actions.append(delete_action)

        actions.append(None)

        # 导出当前页为图片
        export_action = QAction("导出为图片", self.main_window)
        export_action.triggered.connect(lambda: self._export_page_as_image(page_num))
        actions.append(export_action)

        # 提取页面文本
        extract_action = QAction("提取文本", self.main_window)
        extract_action.triggered.connect(lambda: self._extract_page_text(page_num))
        actions.append(extract_action)

        return actions
    
    def _create_thumbnail_actions(self, page_num):
        """创建缩略图操作动作"""
        actions = []

        # 跳转到页面
        goto_action = QAction("跳转到页面", self.main_window)
        goto_action.triggered.connect(lambda: self._goto_page(page_num))
        actions.append(goto_action)

        actions.append(None)

        # 插入子菜单
        insert_menu = QMenu("插入", self.main_window)

        # 插入空白页
        insert_blank_action = QAction("插入空白页", self.main_window)
        insert_blank_action.triggered.connect(lambda: self._insert_blank_page(page_num))
        insert_menu.addAction(insert_blank_action)

        # 插入PDF
        insert_pdf_action = QAction("插入PDF文件", self.main_window)
        insert_pdf_action.triggered.connect(lambda: self._insert_pdf_page(page_num))
        insert_menu.addAction(insert_pdf_action)

        # 插入图片
        insert_image_action = QAction("插入图片", self.main_window)
        insert_image_action.triggered.connect(lambda: self._insert_image_page(page_num))
        insert_menu.addAction(insert_image_action)

        actions.append(insert_menu.menuAction())

        # 旋转页面子菜单
        rotate_menu = QMenu("旋转页面", self.main_window)

        rotate_90 = QAction("90°", self.main_window)
        rotate_90.triggered.connect(lambda: self._rotate_page(page_num, 90))
        rotate_menu.addAction(rotate_90)

        rotate_180 = QAction("180°", self.main_window)
        rotate_180.triggered.connect(lambda: self._rotate_page(page_num, 180))
        rotate_menu.addAction(rotate_180)

        rotate_270 = QAction("270°", self.main_window)
        rotate_270.triggered.connect(lambda: self._rotate_page(page_num, 270))
        rotate_menu.addAction(rotate_270)

        actions.append(rotate_menu.menuAction())

        actions.append(None)

        # 删除当前页
        delete_action = QAction("删除当前页", self.main_window)
        delete_action.triggered.connect(lambda: self._delete_page(page_num))
        actions.append(delete_action)

        actions.append(None)

        # 导出为图片
        export_action = QAction("导出为图片", self.main_window)
        export_action.triggered.connect(lambda: self._export_page_as_image(page_num))
        actions.append(export_action)

        # 提取文本
        extract_action = QAction("提取文本", self.main_window)
        extract_action.triggered.connect(lambda: self._extract_page_text(page_num))
        actions.append(extract_action)

        return actions
    
    def _create_file_actions(self):
        """创建文件操作动作"""
        actions = []

        # 打开文件
        open_action = QAction("📂 打开文件", self.main_window)
        open_action.triggered.connect(self.main_window.open_file)
        actions.append(open_action)

        # 保存文件
        save_action = QAction("💾 保存文件", self.main_window)
        save_action.triggered.connect(self.main_window.save_file)
        actions.append(save_action)

        # 另存为
        save_as_action = QAction("💾 另存为", self.main_window)
        save_as_action.triggered.connect(self.main_window.save_as_file)
        actions.append(save_as_action)
        
        return actions
    
    def _create_quick_access_actions(self):
        """创建快速访问动作"""
        actions = []
        
        # 显示/隐藏缩略图
        thumbnail_action = QAction("🖼️ 缩略图", self.main_window)
        thumbnail_action.setCheckable(True)
        thumbnail_action.setChecked(self.main_window.show_thumbnails)
        thumbnail_action.triggered.connect(self.main_window.toggle_thumbnails)
        actions.append(thumbnail_action)
        
        # 显示/隐藏AI助手
        if hasattr(self.main_window, 'llm_sidebar_dock'):
            llm_action = QAction("🤖 AI助手", self.main_window)
            llm_action.setCheckable(True)
            llm_action.setChecked(self.main_window.llm_sidebar_dock.isVisible())
            llm_action.triggered.connect(self.main_window._toggle_llm_sidebar)
            actions.append(llm_action)
        
        return actions
    
    def _create_tool_actions(self):
        """创建工具动作"""
        actions = []
        
        # OCR工具
        ocr_action = QAction("🔍 OCR识别", self.main_window)
        ocr_action.triggered.connect(self.main_window.ocr_plugin_manager.show_ocr_dialog)
        actions.append(ocr_action)
        
        # 条码拆分
        barcode_action = QAction("📊 条码拆分", self.main_window)
        if hasattr(self.main_window, 'split_manager'):
            barcode_action.triggered.connect(self.main_window.split_manager.show_barcode_split_dialog)
        else:
            barcode_action.setEnabled(False)
        actions.append(barcode_action)
        
        # 搜索
        search_action = QAction("🔎 搜索", self.main_window)
        search_action.triggered.connect(self.main_window.search_manager.show_search_dialog)
        actions.append(search_action)
        
        return actions
    
    def _copy_text(self, text):
        """复制文本到剪贴板"""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        self.main_window.show_message("✅ 文本已复制到剪贴板")
        logger.debug(f"复制文本: {text[:50]}...")
    
    def _search_text(self, text):
        """搜索文本"""
        self.main_window.search_manager.set_search_text(text)
        self.main_window.search_manager.show_search_dialog()
        logger.debug(f"搜索文本: {text}")
    
    def _ocr_text(self, text):
        """OCR识别文本"""
        self.main_window.show_message("🔍 OCR识别功能触发")
        logger.debug("OCR识别功能")
    
    def _rotate_page(self, page_num, angle):
        """旋转页面"""
        if hasattr(self.main_window, 'pdf_processor') and self.main_window.pdf_processor.fitz_document:
            page_editor = self._get_page_editor()
            if page_editor:
                success, message = page_editor.rotate_page(page_num + 1, angle)
                if success:
                    self.main_window.show_message(message)
                    self.main_window.update_preview()
                else:
                    self.main_window.show_message(f"❌ {message}")
            else:
                self.main_window.show_message("❌ 页面编辑器未初始化")
        else:
            self.main_window.show_message("❌ 未打开PDF文档")
        logger.debug(f"旋转页面: {page_num + 1}, 角度: {angle}")
    
    def _export_page_as_image(self, page_num):
        """导出页面为图片"""
        if hasattr(self.main_window, 'pdf_processor') and self.main_window.pdf_processor.fitz_document:
            try:
                default_name = f"page_{page_num + 1}.png"
                file_path, _ = QFileDialog.getSaveFileName(
                    self.main_window,
                    "保存图片",
                    default_name,
                    "PNG图片 (*.png);;JPEG图片 (*.jpg);;所有文件 (*.*)"
                )

                if file_path:
                    page = self.main_window.pdf_processor.fitz_document.load_page(page_num)
                    pix = page.get_pixmap()
                    if file_path.lower().endswith('.jpg') or file_path.lower().endswith('.jpeg'):
                        pix.save(file_path, "JPEG")
                    else:
                        pix.save(file_path, "PNG")

                    self.main_window.show_message(f"✅ 第{page_num + 1}页已导出为图片")
                    logger.debug(f"导出页面{page_num}为图片成功: {file_path}")
            except Exception as e:
                logger.error(f"导出页面{page_num}为图片失败: {e}")
                self.main_window.show_message(f"❌ 导出图片失败: {str(e)}")
        else:
            self.main_window.show_message("❌ 未打开PDF文档")
    
    def _extract_page_text(self, page_num):
        """提取页面文本（使用OCR识别整页）"""
        if hasattr(self.main_window, 'pdf_processor') and self.main_window.pdf_processor.fitz_document:
            try:
                # 获取当前使用的OCR插件
                current_plugin_name = self.main_window.ocr_config_manager.get_current_plugin()
                if not current_plugin_name:
                    self.main_window.show_message("❌ 请先在OCR设置中选择一个OCR插件")
                    return

                # 获取插件实例
                plugin = self.main_window.ocr_plugin_manager.plugins.get(current_plugin_name)
                if not plugin:
                    self.main_window.show_message(f"❌ OCR插件 '{current_plugin_name}' 未加载")
                    return

                # 初始化插件（如果尚未初始化）
                if not plugin.is_initialized:
                    plugin_config = self.main_window.ocr_config_manager.get_plugin_config(current_plugin_name)
                    init_result = self.main_window.ocr_plugin_manager.initialize_plugin(current_plugin_name, plugin_config)
                    if not init_result.is_success():
                        self.main_window.show_message(f"❌ OCR插件初始化失败: {init_result.message}")
                        return

                # 获取整个页面的图像数据
                page = self.main_window.pdf_processor.fitz_document.load_page(page_num)
                zoom_factor = self.main_window.pdf_processor.zoom_factor

                # 渲染整个页面为图像
                pix = page.get_pixmap(matrix=fitz.Matrix(zoom_factor, zoom_factor))
                image_data = pix.tobytes("png")

                # 在状态栏显示加载信息
                self.main_window.show_message("正在进行OCR识别...")
                QApplication.processEvents()

                try:
                    # 方法1: 直接使用字节数据
                    ocr_result = plugin.recognize_from_bytes(image_data)

                    # 如果方法1失败，尝试方法2: 转换为Base64字符串
                    if not ocr_result.is_success():
                        image_base64 = b64encode(image_data).decode('utf-8')
                        if image_base64.startswith('data:image'):
                            image_base64 = image_base64.split(',')[1] if ',' in image_base64 else image_base64
                        ocr_result = plugin.recognize_from_base64(image_base64)

                    # 如果方法2也失败，尝试方法3: 保存为临时文件
                    if not ocr_result.is_success():
                        temp_dir = os.path.realpath(tempfile.gettempdir())
                        temp_filename = f"page_ocr_{uuid.uuid4().hex}.png"
                        tmp_file_path = os.path.join(temp_dir, temp_filename)

                        try:
                            with open(tmp_file_path, 'wb') as tmp_file:
                                tmp_file.write(image_data)

                            if os.path.exists(tmp_file_path):
                                ocr_result = plugin.recognize_from_file(tmp_file_path)
                            else:
                                logger.error(f"临时文件创建失败: {tmp_file_path}")
                                ocr_result = OCRResult(
                                    code=OCRErrorCode.FILE_NOT_FOUND,
                                    message=f"临时文件创建失败: {tmp_file_path}",
                                    plugin_name=plugin.plugin_name
                                )
                        except Exception as file_error:
                            logger.error(f"创建或写入临时文件时出错: {file_error}")
                            ocr_result = OCRResult(
                                code=OCRErrorCode.UNKNOWN_ERROR,
                                message=f"创建临时文件失败: {str(file_error)}",
                                plugin_name=plugin.plugin_name
                            )
                        finally:
                            try:
                                if os.path.exists(tmp_file_path):
                                    os.unlink(tmp_file_path)
                            except Exception as cleanup_error:
                                logger.warning(f"清理临时文件时出错: {cleanup_error}")

                    # 显示OCR结果
                    dialog = ScreenshotOCRResultDialog(ocr_result, self.main_window)
                    dialog.setWindowTitle(f"第{page_num + 1}页 - OCR识别结果")
                    dialog.exec_()

                    if ocr_result.is_success():
                        self.main_window.show_message("✅ OCR识别完成")
                    else:
                        self.main_window.show_message(f"⚠️ OCR识别失败: {ocr_result.message}")

                finally:
                    self.main_window.show_message("")

            except Exception as e:
                logger.error(f"提取页面{page_num}文本失败: {e}")
                logger.error(traceback.format_exc())
                self.main_window.show_message(f"❌ 提取文本失败: {str(e)}")
        else:
            self.main_window.show_message("❌ 未打开PDF文档")
    
    def _goto_page(self, page_num):
        """跳转到页面"""
        if hasattr(self.main_window, 'go_to_page'):
            self.main_window.go_to_page(page_num + 1)
            self.main_window.show_message(f"跳转到第{page_num + 1}页")
            logger.debug(f"跳转到页面: {page_num + 1}")

    def _insert_blank_page(self, page_num):
        """插入空白页"""
        if hasattr(self.main_window, 'pdf_processor') and self.main_window.pdf_processor.fitz_document:
            page_editor = self._get_page_editor()
            if page_editor:
                success, message = page_editor.insert_blank_page(page_num + 1)
                if success:
                    self.main_window.show_message(message)
                    self.main_window.update_preview()
                else:
                    self.main_window.show_message(f"❌ {message}")
            else:
                self.main_window.show_message("❌ 页面编辑器未初始化")
        else:
            self.main_window.show_message("❌ 未打开PDF文档")
        logger.debug(f"插入空白页到页面 {page_num + 1} 后")

    def _insert_pdf_page(self, page_num):
        """插入PDF文件"""
        if not (hasattr(self.main_window, 'pdf_processor') and self.main_window.pdf_processor.fitz_document):
            self.main_window.show_message("❌ 未打开PDF文档")
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self.main_window,
            "选择要插入的PDF文件",
            "",
            "PDF文件 (*.pdf)"
        )

        if file_path:
            page_editor = self._get_page_editor()
            if page_editor:
                success, message = page_editor.insert_pdf_page(page_num + 1, file_path)
                if success:
                    self.main_window.show_message(message)
                    self.main_window.update_preview()
                    self.main_window.load_thumbnails()
                    # 清除虚拟滚动缓存
                    if hasattr(self.main_window, 'virtual_scroll') and self.main_window.virtual_scroll:
                        self.main_window.virtual_scroll.clear_cache()
                else:
                    self.main_window.show_message(f"❌ {message}")
            else:
                self.main_window.show_message("❌ 页面编辑器未初始化")
        logger.debug(f"插入PDF文件到页面 {page_num + 1} 后")

    def _insert_image_page(self, page_num):
        """插入图片"""
        logger.debug(f"开始插入图片，page_num={page_num}")

        # 检查是否打开了PDF文档或图片
        if not (hasattr(self.main_window, 'pdf_processor') and self.main_window.pdf_processor.fitz_document):
            self.main_window.show_message("❌ 未打开文档")
            logger.warning("未打开文档，无法插入图片")
            return

        # 统一使用文件选择对话框让用户选择要插入的图片
        file_path, _ = QFileDialog.getOpenFileName(
            self.main_window,
            "选择要插入的图片",
            "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.tif *.webp)"
        )

        logger.debug(f"用户选择的图片路径: {file_path}")

        if not file_path:
            logger.debug("用户未选择图片文件")
            return

        # 尝试使用page_editor插入图片
        page_editor = self._get_page_editor()
        if page_editor:
            logger.debug(f"准备调用page_editor.insert_image_page，page_num={page_num + 1}")
            success, message = page_editor.insert_image_page(page_num + 1, file_path)
            logger.debug(f"插入图片结果: success={success}, message={message}")
            if success:
                self.main_window.show_message(message)
                self.main_window.update_preview()
                self.main_window.load_thumbnails()
                # 清除虚拟滚动缓存
                if hasattr(self.main_window, 'virtual_scroll') and self.main_window.virtual_scroll:
                    self.main_window.virtual_scroll.clear_cache()
            else:
                self.main_window.show_message(f"❌ {message}")
        else:
            # 单张图片模式，使用pdf_processor的import_images功能
            logger.debug("单张图片模式，使用pdf_processor.import_images功能")
            if hasattr(self.main_window.pdf_processor, 'import_images'):
                success, message = self.main_window.pdf_processor.import_images([file_path], page_num)
                logger.debug(f"插入图片结果: success={success}, message={message}")
                if success:
                    self.main_window.show_message(message)
                    self.main_window.update_preview()
                    self.main_window.load_thumbnails()
                    # 清除虚拟滚动缓存
                    if hasattr(self.main_window, 'virtual_scroll') and self.main_window.virtual_scroll:
                        self.main_window.virtual_scroll.clear_cache()
                else:
                    self.main_window.show_message(f"❌ {message}")
            else:
                logger.error("pdf_processor没有import_images方法")
                self.main_window.show_message("❌ 无法插入图片")

        logger.debug(f"插入图片操作完成，page_num={page_num + 1}")

    def _delete_page(self, page_num):
        """删除页面"""
        if not (hasattr(self.main_window, 'pdf_processor') and self.main_window.pdf_processor.fitz_document):
            self.main_window.show_message("❌ 未打开PDF文档")
            return

        # 验证页码是否有效
        if hasattr(self.main_window, 'pdf_processor') and self.main_window.pdf_processor.fitz_document:
            total_pages = self.main_window.pdf_processor.get_total_pages()
            if page_num < 0 or page_num >= total_pages:
                logger.error(f"[删除页面] 页码无效: {page_num}, 总页数: {total_pages}")
                self.main_window.show_message(f"❌ 页码无效: {page_num}")
                return

        reply = QMessageBox.question(
            self.main_window,
            "确认删除",
            f"确定要删除第{page_num + 1}页吗？",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            page_editor = self._get_page_editor()
            if page_editor:
                page_num_1based = page_num + 1
                success, message = page_editor.delete_page(page_num_1based)
                if success:
                    # 获取删除后应该跳转到的页面（0-based）
                    total_pages_after = self.main_window.pdf_processor.get_total_pages()
                    # 计算目标页面：如果删除的不是最后一页，就到当前页；如果是最后一页，就到新的最后一页
                    if page_num_1based == total_pages_after + 1:
                        target_page = max(0, total_pages_after - 1)
                    else:
                        target_page = min(page_num, total_pages_after - 1)
                    
                    self.main_window.show_message(message)
                    # 删除页面后需要清除虚拟滚动的缓存
                    if hasattr(self.main_window, 'virtual_scroll') and self.main_window.virtual_scroll:
                        self.main_window.virtual_scroll.clear_cache()
                    # 更新预览和缩略图
                    self.main_window.update_preview()
                    self.main_window.load_thumbnails()
                    # 延迟一段时间，确保所有UI更新完成，然后滚动到目标页面
                    QTimer.singleShot(500, lambda: self._force_scroll_to_page(target_page))
                else:
                    self.main_window.show_message(f"❌ {message}")
            else:
                self.main_window.show_message("❌ 页面编辑器未初始化")
        logger.debug(f"删除页面 {page_num + 1}")

    def _force_scroll_to_page(self, target_page):
        """强制滚动到指定页面"""
        if not hasattr(self.main_window, 'pdf_processor'):
            return

        if hasattr(self.main_window, 'virtual_scroll') and self.main_window.virtual_scroll:
            virtual_scroll = self.main_window.virtual_scroll
            # 根据页面索引计算滚动位置
            if hasattr(virtual_scroll, 'page_positions') and len(virtual_scroll.page_positions) > target_page:
                target_scroll_pos = virtual_scroll.page_positions[target_page]
                logger.debug(f"强制滚动到页面 {target_page}，位置: {target_scroll_pos}")
                virtual_scroll.verticalScrollBar().setValue(target_scroll_pos)
            else:
                logger.warning(f"无法滚动到页面 {target_page}，page_positions长度: {len(virtual_scroll.page_positions) if hasattr(virtual_scroll, 'page_positions') else 0}")
