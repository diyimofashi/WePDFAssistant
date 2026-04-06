import sys
import os
import json
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QFileDialog, QScrollArea, QMenuBar, QMenu, 
    QAction, QSplitter, QListWidget, QListWidgetItem, QInputDialog,
    QLineEdit, QStatusBar, QMessageBox
)
from PyQt5.QtGui import QPixmap, QImage, QIcon
from PyQt5.QtCore import Qt, QSize, pyqtSignal
import fitz  # PyMuPDF

class PDFEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF阅读编辑器")
        self.setGeometry(100, 100, 1200, 800)
        
        # 初始化变量
        self.pdf_document = None
        self.current_page = 0
        self.zoom = 1.0
        self.file_path = ""
        self.bookmarks = []
        self.show_thumbnails = True
        
        # 加载配置
        self.config = self.load_config()
        
        # 创建主部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # 创建主布局
        self.main_layout = QHBoxLayout(self.central_widget)
        
        # 创建左侧面板（缩略图和书签）
        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.left_panel)
        
        # 创建缩略图列表
        self.thumbnail_list = QListWidget()
        self.thumbnail_list.itemClicked.connect(self.on_thumbnail_clicked)
        self.left_layout.addWidget(self.thumbnail_list)
        
        # 创建收缩按钮
        self.toggle_thumbnails_btn = QPushButton("收缩")
        self.toggle_thumbnails_btn.clicked.connect(self.toggle_thumbnails)
        self.left_layout.addWidget(self.toggle_thumbnails_btn)
        
        # 创建右侧面板（PDF显示）
        self.right_panel = QWidget()
        self.right_layout = QVBoxLayout(self.right_panel)
        
        # 创建PDF显示区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.pdf_display = QLabel()
        self.pdf_display.setAlignment(Qt.AlignCenter)
        self.scroll_area.setWidget(self.pdf_display)
        self.right_layout.addWidget(self.scroll_area)
        
        # 创建分割器
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.right_panel)
        self.splitter.setSizes([200, 1000])
        self.main_layout.addWidget(self.splitter)
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.page_info = QLabel("页面: 0/0")
        self.zoom_info = QLabel("缩放: 100%")
        self.status_bar.addWidget(self.page_info)
        self.status_bar.addWidget(self.zoom_info)
        
        # 创建菜单栏
        self.create_menu()
        
        # 创建工具栏
        self.create_toolbar()
        
        # 恢复上次打开的文件
        if "last_file" in self.config:
            last_file = self.config["last_file"]
            if os.path.exists(last_file):
                self.open_pdf(last_file)
                if "last_page" in self.config:
                    self.goto_page(self.config["last_page"])
        
    def create_menu(self):
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        open_action = QAction("打开", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_file_dialog)
        file_menu.addAction(open_action)
        
        save_action = QAction("保存", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)
        
        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 编辑菜单
        edit_menu = menubar.addMenu("编辑")
        
        zoom_in_action = QAction("放大", self)
        zoom_in_action.setShortcut("Ctrl++")
        zoom_in_action.triggered.connect(self.zoom_in)
        edit_menu.addAction(zoom_in_action)
        
        zoom_out_action = QAction("缩小", self)
        zoom_out_action.setShortcut("Ctrl+-")
        zoom_out_action.triggered.connect(self.zoom_out)
        edit_menu.addAction(zoom_out_action)
        
        search_action = QAction("搜索", self)
        search_action.setShortcut("Ctrl+F")
        search_action.triggered.connect(self.search_text)
        edit_menu.addAction(search_action)
        
        # 视图菜单
        view_menu = menubar.addMenu("视图")
        
        prev_page_action = QAction("上一页", self)
        prev_page_action.setShortcut("PgUp")
        prev_page_action.triggered.connect(self.prev_page)
        view_menu.addAction(prev_page_action)
        
        next_page_action = QAction("下一页", self)
        next_page_action.setShortcut("PgDown")
        next_page_action.triggered.connect(self.next_page)
        view_menu.addAction(next_page_action)
        
        bookmarks_action = QAction("书签", self)
        bookmarks_action.triggered.connect(self.toggle_bookmarks)
        view_menu.addAction(bookmarks_action)
        
    def create_toolbar(self):
        toolbar = self.addToolBar("工具栏")
        
        prev_btn = QPushButton("上一页")
        prev_btn.clicked.connect(self.prev_page)
        toolbar.addWidget(prev_btn)
        
        next_btn = QPushButton("下一页")
        next_btn.clicked.connect(self.next_page)
        toolbar.addWidget(next_btn)
        
        zoom_in_btn = QPushButton("放大")
        zoom_in_btn.clicked.connect(self.zoom_in)
        toolbar.addWidget(zoom_in_btn)
        
        zoom_out_btn = QPushButton("缩小")
        zoom_out_btn.clicked.connect(self.zoom_out)
        toolbar.addWidget(zoom_out_btn)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索...")
        self.search_input.returnPressed.connect(self.search_text)
        toolbar.addWidget(self.search_input)
        
        search_btn = QPushButton("搜索")
        search_btn.clicked.connect(self.search_text)
        toolbar.addWidget(search_btn)
        
    def open_file_dialog(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "打开PDF文件", "", "PDF Files (*.pdf);;All Files (*)", options=options)
        if file_path:
            self.open_pdf(file_path)
    
    def open_pdf(self, file_path):
        try:
            self.pdf_document = fitz.open(file_path)
            self.file_path = file_path
            self.current_page = 0
            self.update_page_display()
            self.generate_thumbnails()
            self.update_status_bar()
            
            # 保存到配置
            self.config["last_file"] = file_path
            self.config["last_page"] = 0
            self.save_config()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法打开PDF文件: {str(e)}")
    
    def save_file(self):
        if not self.pdf_document:
            QMessageBox.warning(self, "警告", "没有打开的PDF文件")
            return
        
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(self, "保存PDF文件", "", "PDF Files (*.pdf);;All Files (*)", options=options)
        if file_path:
            try:
                self.pdf_document.save(file_path)
                QMessageBox.information(self, "成功", "PDF文件保存成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法保存PDF文件: {str(e)}")
    
    def update_page_display(self):
        if not self.pdf_document:
            return
        
        page = self.pdf_document[self.current_page]
        pix = page.get_pixmap(matrix=fitz.Matrix(self.zoom, self.zoom))
        img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(img)
        self.pdf_display.setPixmap(pixmap)
    
    def generate_thumbnails(self):
        if not self.pdf_document:
            return
        
        self.thumbnail_list.clear()
        for i in range(len(self.pdf_document)):
            page = self.pdf_document[i]
            pix = page.get_pixmap(matrix=fitz.Matrix(0.1, 0.1))
            img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(img)
            
            item = QListWidgetItem()
            item.setIcon(QIcon(pixmap))
            item.setText(f"页 {i+1}")
            item.setData(Qt.UserRole, i)
            item.setSizeHint(QSize(180, 80))
            self.thumbnail_list.addItem(item)
    
    def on_thumbnail_clicked(self, item):
        page_num = item.data(Qt.UserRole)
        self.goto_page(page_num)
    
    def goto_page(self, page_num):
        if not self.pdf_document:
            return
        
        if 0 <= page_num < len(self.pdf_document):
            self.current_page = page_num
            self.update_page_display()
            self.update_status_bar()
            
            # 更新配置
            self.config["last_page"] = page_num
            self.save_config()
    
    def prev_page(self):
        if self.pdf_document and self.current_page > 0:
            self.goto_page(self.current_page - 1)
    
    def next_page(self):
        if self.pdf_document and self.current_page < len(self.pdf_document) - 1:
            self.goto_page(self.current_page + 1)
    
    def zoom_in(self):
        self.zoom += 0.1
        self.update_page_display()
        self.update_status_bar()
    
    def zoom_out(self):
        if self.zoom > 0.1:
            self.zoom -= 0.1
            self.update_page_display()
            self.update_status_bar()
    
    def search_text(self):
        if not self.pdf_document:
            return
        
        text = self.search_input.text()
        if not text:
            return
        
        found = False
        for i in range(len(self.pdf_document)):
            page = self.pdf_document[i]
            text_instances = page.search_for(text)
            if text_instances:
                self.goto_page(i)
                found = True
                break
        
        if not found:
            QMessageBox.information(self, "搜索结果", f"未找到文本: {text}")
    
    def toggle_thumbnails(self):
        if self.show_thumbnails:
            self.splitter.setSizes([0, 1200])
            self.toggle_thumbnails_btn.setText("展开")
        else:
            self.splitter.setSizes([200, 1000])
            self.toggle_thumbnails_btn.setText("收缩")
        self.show_thumbnails = not self.show_thumbnails
    
    def toggle_bookmarks(self):
        if not self.pdf_document:
            return
        
        bookmark_name, ok = QInputDialog.getText(self, "添加书签", "书签名称:")
        if ok and bookmark_name:
            self.bookmarks.append((self.current_page, bookmark_name))
            QMessageBox.information(self, "成功", f"书签 '{bookmark_name}' 已添加")
    
    def update_status_bar(self):
        if self.pdf_document:
            self.page_info.setText(f"页面: {self.current_page + 1}/{len(self.pdf_document)}")
            self.zoom_info.setText(f"缩放: {int(self.zoom * 100)}%")
        else:
            self.page_info.setText("页面: 0/0")
            self.zoom_info.setText("缩放: 100%")
    
    def load_config(self):
        config_file = "pdf_editor_config.json"
        if os.path.exists(config_file):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    def save_config(self):
        config_file = "pdf_editor_config.json"
        try:
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    
    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            self.zoom_in()
        else:
            self.zoom_out()
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            url = event.mimeData().urls()[0]
            file_path = url.toLocalFile()
            if file_path.lower().endswith(".pdf"):
                self.open_pdf(file_path)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    editor = PDFEditor()
    editor.show()
    sys.exit(app.exec_())
