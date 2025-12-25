"""
下载远程文件对话框
允许用户输入URL并选择下载插件来下载文件
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QLabel, QLineEdit, QComboBox, QPushButton, 
                             QProgressBar, QMessageBox, QWidget, QApplication)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from app.managers.download_plugin_manager import download_plugin_manager
from app.config.download_plugin_config import download_config_manager
from app.utils.logger import get_logger
import os
import tempfile


logger = get_logger('download_file_dialog')


class DownloadWorker(QThread):
    """下载工作线程"""
    progress_updated = pyqtSignal(int)
    download_finished = pyqtSignal(object)  # DownloadResult
    
    def __init__(self, plugin_manager, plugin_name, config, url, local_path):
        super().__init__()
        self.plugin_manager = plugin_manager
        self.plugin_name = plugin_name
        self.config = config
        self.url = url
        self.local_path = local_path
    
    def run(self):
        """执行下载任务"""
        try:
            # 初始化插件
            init_result = self.plugin_manager.initialize_plugin(self.plugin_name, self.config)
            if not init_result.is_success():
                self.download_finished.emit(init_result)
                return
            
            # 定义进度回调函数
            def progress_callback(progress):
                self.progress_updated.emit(progress)
            
            # 执行下载
            result = self.plugin_manager.download_with_plugin(
                self.plugin_name, 
                self.url, 
                self.local_path,
                progress_callback=progress_callback
            )
            
            self.download_finished.emit(result)
            
        except Exception as e:
            from app.core.download.download_plugin_interface import DownloadResult, DownloadErrorCode
            error_result = DownloadResult(
                code=DownloadErrorCode.DOWNLOAD_FAILED,
                message=f"下载线程异常: {str(e)}",
                plugin_name=self.plugin_name
            )
            self.download_finished.emit(error_result)


class DownloadFileDialog(QDialog):
    """下载远程文件对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("下载远程文件")
        self.setGeometry(300, 300, 500, 250)
        
        # 初始化插件管理器和配置管理器
        self.download_plugin_manager = download_plugin_manager
        self.download_config_manager = download_config_manager
        
        # 加载插件
        self.loaded_plugins = self.download_plugin_manager.load_plugins()
        
        self.worker = None
        self.temp_file_path = None
        
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        
        # 表单布局
        form_layout = QFormLayout()
        
        # URL输入
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("请输入文件的URL地址")
        form_layout.addRow("文件URL:", self.url_input)
        
        # 显示当前插件
        current_plugin = self.download_config_manager.get_current_plugin()
        plugin_label = QLabel(f"当前插件: {current_plugin if current_plugin else '未选择'}")
        form_layout.addRow("", plugin_label)
        
        layout.addLayout(form_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.download_button = QPushButton("下载")
        self.download_button.clicked.connect(self.download_file)
        button_layout.addWidget(self.download_button)
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.cancel_download)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def download_file(self):
        """下载文件"""
        # 使用当前配置的插件
        plugin_name = self.download_config_manager.get_current_plugin()
        url = self.url_input.text().strip()
        
        if not plugin_name:
            QMessageBox.warning(self, "警告", "请先在下载设置中选择一个下载插件")
            return
        
        if not url:
            QMessageBox.warning(self, "警告", "请输入文件URL")
            return
        
        # 获取插件配置
        config = self.download_config_manager.get_plugin_config(plugin_name)
        if not config:
            QMessageBox.warning(self, "警告", f"插件 {plugin_name} 未配置，请先进行配置")
            return
        
        # 创建临时文件路径
        try:
            _, file_extension = os.path.splitext(url)
            if not file_extension:
                file_extension = '.pdf'  # 默认为PDF文件
            
            self.temp_file_path = os.path.join(
                tempfile.gettempdir(),
                f"downloaded_file_{os.getpid()}_{hash(url) % 10000}{file_extension}"
            )
        except Exception as e:
            QMessageBox.critical(self, "错误", f"创建临时文件路径失败: {str(e)}")
            return
        
        # 禁用下载按钮，启用进度条
        self.download_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # 创建并启动下载线程
        self.worker = DownloadWorker(
            self.download_plugin_manager,
            plugin_name,
            config,
            url,
            self.temp_file_path
        )
        self.worker.progress_updated.connect(self.progress_bar.setValue)
        self.worker.download_finished.connect(self.on_download_finished)
        self.worker.start()
    
    def on_download_finished(self, result):
        """下载完成回调"""
        self.download_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if result.is_success():
            # 保存临时文件路径，以便外部获取
            self.downloaded_file_path = self.temp_file_path
            QMessageBox.information(self, "成功", f"文件下载成功!\n已保存到: {self.temp_file_path}")
            self.accept()  # 关闭对话框
        else:
            # 清理失败的临时文件
            if self.temp_file_path and os.path.exists(self.temp_file_path):
                try:
                    os.remove(self.temp_file_path)
                except:
                    pass
            
            QMessageBox.critical(self, "下载失败", f"下载失败:\n{result.message}")
            self.temp_file_path = None
    
    def cancel_download(self):
        """取消下载"""
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
        
        # 清理临时文件
        if self.temp_file_path and os.path.exists(self.temp_file_path):
            try:
                os.remove(self.temp_file_path)
            except:
                pass
        
        self.close()
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        self.cancel_download()
        event.accept()


def show_download_file_dialog(parent=None):
    """显示下载文件对话框的便捷函数"""
    dialog = DownloadFileDialog(parent)
    if dialog.exec_() == QDialog.Accepted and hasattr(dialog, 'downloaded_file_path'):
        return dialog.downloaded_file_path
    return None