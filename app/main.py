"""PDF文档处理与状态管理规范
一、多入口调用一致性：
- 当存在多个UI入口（菜单栏、右键菜单、快捷键等）调用相同功能时，修复必须覆盖所有路径
- 通过代码搜索识别所有调用点，优先在共享底层方法中实现逻辑修复
- 所有入口使用统一的UI更新方式，复杂组件（如虚拟滚动）应使用`update_preview`完全重建UI，避免局部刷新

二、虚拟滚动与UI刷新：
- 文档结构变更（插入/删除页面、导入图片）后，仅刷新UI不足以保证正确显示
- 必须彻底重建虚拟滚动区域的数据源并清除内部缓存
- 触发完整的预览重建流程，验证相邻和后续页面显示正确性

三、页面索引处理：
- PageEditor接口方法必须使用1基索引（1-based）
- UI层在调用前需将0基索引转换为1基索引
- LLM插件禁止自行减1，应直接传递原始页码
- 跨组件调用时验证索引基值类型，保持一致性
- 内部使用0基索引，用户显示使用1基索引，转换需明确标记

四、组件状态同步：
- `page_editor`的`temp_file`和`original_file`必须与`pdf_processor`的`current_file`保持一致
- 文档内容变更后验证并更新相关组件路径状态
- 非标准方式创建文档（如图片导入）时，确保临时文档创建伴随完整状态关联流程
- 删除、保存等操作前检查路径信息是否已正确初始化

五、多文档状态隔离：
- 切换或打开新文档前，彻底关闭当前文档编辑会话
- 删除当前文档的所有临时文件和缓存数据
- 将`page_editor`等共享组件重置为初始状态（如None）
- 确保新文档从干净环境开始，不继承操作历史
- 执行完整资源清理流程，包括内存对象和磁盘文件
- 验证新文档初始状态纯净性，防止"幽灵操作"

六、删除与编辑状态管理：
- 删除操作前确保`page_editor`和`pdf_processor`已初始化
- 图片导入生成的PDF必须使用完整文档重建流程，禁用增量保存以避免错误
- 删除后验证`get_total_pages()`返回值，若不一致需检查`open_pdf`是否导致状态重置
- 确保`history_manager`等关键组件处于可用状态
- 非标准PDF（如图片转换而来）应先迁移至标准结构再编辑
- 操作完成后验证UI预览与实际页数一致
- 删除唯一页面时不应尝试保存零页文档，应立即重置PDF处理器状态：
- 清除`fitz_document`、临时文件和相关路径信息
- 创建新的空PDF实例或设置为None状态
- 确保`page_editor`和`pdf_processor`的状态一致性
- 更新UI显示为空文档状态，避免残留预览
- 记录操作历史并允许撤销

七、前置验证规范：
- 执行任何PDF修改操作前必须检查`pdf_processor.fitz_document`是否为None
- 验证文档页数大于0且目标页码在有效范围内
- 确认`page_editor`已正确关联当前文档实例
- 若任一检查失败应返回明确错误信息而非继续执行
- 所有结构变更操作均需包含此验证流程

八、PDF加密处理：
- 使用PyMuPDF加密时必须使用`encryption`参数传入`fitz.DocumentEncryption`对象，禁止使用`encrypt=password`
- 对PyMuPDF加载的文档进行加密时，应通过PyPDF2完成：
1. PyMuPDF保存至临时文件
2. PyPDF2读取并复制页面
3. 保留原始元数据
4. 使用PyPDF2.encrypt加密
5. 保存到目标路径

九、通用保障措施：
- 上下文状态从事件源获取并验证有效性，禁止默认使用当前视图
- 操作前后记录状态对比日志，关键操作验证执行结果
- 结构变更后显式恢复UI状态，不能依赖组件默认行为
- 方法调用前验证目标方法存在性，信号连接需正确定义和实现

十、虚拟滚动区域内容清除与UI重置：
- 禁止调用不存在的方法如`clear_content`
- 应通过重新设置内部widget的方式实现内容清除：
1. 创建新的QWidget实例作为虚拟容器
2. 使用`setWidget`方法替换原有内容
3. 确保布局和信号连接正确重建
- 所有UI重置操作必须确保依赖的Qt组件（如QWidget、QVBoxLayout）已正确定义和导入
- 在执行UI更新前应验证主窗口组件（如page_spinbox）的存在性，避免属性访问错误
- 完整的UI重置应包括数据源清理、组件重建和信号重新连接三步流程

十一、零页文档状态下的UI重置：
当PDF文档页数变为0时，必须执行完整的UI状态重置：
1. 虚拟滚动区域应通过创建新的QWidget容器并使用setWidget替换的方式彻底清空内容
2. 缩略图列表必须清空所有缩略图项
3. 页面计数器控件（如page_spinbox）需更新为0
4. 窗口标题应恢复为"未打开文档"状态
5. 所有操作按钮（删除、导出等）应根据空文档状态禁用或启用
6. 在执行重置前必须验证相关UI组件的存在性，避免属性访问错误

十二、图片转PDF处理规范：
- 优先使用PIL/Pillow等图像库进行文件特征探测（如获取尺寸等元信息），避免直接使用PyMuPDF的`fitz.open()`打开原始图片文件，防止"not a PDF"类错误
- 当PIL探测确认为图片后，优先使用主库（如PyMuPDF）进行处理，同时准备备用方案（如PIL/Pillow）
- 实施主备双方案处理机制：
1. 主方案：通过文件路径直接插入图片
2. 备用方案：使用PIL预处理并转换为Pixmap对象插入
- 当主库处理失败时，自动降级使用备用库处理
- 及时清理Pixmap等内存对象，确保资源释放
- 实现统一的错误捕获和处理流程，提升系统鲁棒性

十三、页面布局与视觉规范：
- 使用标准PDF页面尺寸（如A4，595×842点）创建页面，而非图片原始尺寸
- 保持图片原始宽高比，防止拉伸变形
- 对图片尺寸进行适配计算：过大则等比缩放至页面边界内，过小则保留原尺寸居中显示
- 图片应在页面中实现水平和垂直双居中对齐
- 居中位置通过 `(page_width - img_width) / 2` 和 `(page_height - img_height) / 2` 计算得出
- 确保所有图片插入操作统一应用此布局逻辑，保证文档风格一致

十四、文档兼容性与编辑安全：
- 注意：直接用PyMuPDF打开的图片文件虽表现为单页文档，但其底层仍为图片格式，不支持`new_page()`等PDF编辑操作
- 在执行页面插入等操作前，应检测文档是否为原始图片格式
- 若目标文档由图片直接加载而来，应先创建新的标准PDF文档，将原内容迁移至新文档，再进行后续编辑操作
- 此转换过程应透明处理，对用户保持行为一致性
- 该模式可作为通用兼容层，用于桥接图像与PDF之间的格式差异
"""

import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app.core.main.main_window_base import MainWindowBase
from app.core.main.pdf_manager_mixin import PDFManagerMixin
from app.core.main.view_manager_mixin import ViewManagerMixin
from app.core.main.thumbnail_manager_mixin import ThumbnailManagerMixin
from app.core.main.search_manager_mixin import SearchManagerMixin
from app.core.main.ocr_manager_mixin import OCRManagerMixin
from app.core.main.upload_manager_mixin import UploadManagerMixin
from app.core.main.download_manager_mixin import DownloadManagerMixin
from app.core.main.operation_manager_mixin import OperationManagerMixin
from app.core.main.llm_manager_mixin import LLMManagerMixin


class AuroraPDF(MainWindowBase, PDFManagerMixin, ViewManagerMixin, ThumbnailManagerMixin,
                  SearchManagerMixin, OCRManagerMixin, UploadManagerMixin,
                  DownloadManagerMixin, OperationManagerMixin, LLMManagerMixin):
    """极灵PDF主窗口 - 重构版本"""
    def zoom_in(self):
        """放大：跳转到下一个更大的缩放级别"""
        current_zoom = self.pdf_processor.get_zoom()
        # 获取下一个更大的缩放级别
        next_zoom = self._get_next_zoom_level(current_zoom, direction=1)
        
        if next_zoom is not None:
            success, message = self.pdf_processor.set_zoom(next_zoom)
            if success:
                self.update_preview()
            self.show_message(message)
    
    def zoom_out(self):
        """缩小：跳转到下一个更小的缩放级别"""
        current_zoom = self.pdf_processor.get_zoom()
        # 获取下一个更小的缩放级别
        next_zoom = self._get_next_zoom_level(current_zoom, direction=-1)
        
        if next_zoom is not None:
            success, message = self.pdf_processor.set_zoom(next_zoom)
            if success:
                self.update_preview()
            self.show_message(message)
        
    def _get_next_zoom_level(self, current_zoom, direction):
        """获取下一个缩放级别"""
        # 预定义的缩放级别列表
        zoom_levels = [0.08, 0.125, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0, 12.0, 16.0, 24.0, 32.0, 48.0, 64.0]
        
        if direction == 1:  # 放大
            for level in zoom_levels:
                if level > current_zoom:
                    return level
            # 如果当前缩放已经最大，返回最大值
            return zoom_levels[-1]
        else:  # 缩小
            # 从大到小遍历，找到第一个小于当前缩放的级别
            for level in reversed(zoom_levels):
                if level < current_zoom:
                    return level
            # 如果当前缩放已经最小，返回最小值
            return zoom_levels[0]
        
    def fit_to_width(self):
        # 获取虚拟滚动区域的实际容器宽度
        container_width = self.virtual_scroll.width() - 40  # 减去一些边距
        return self.view_controller.fit_to_width(container_width)
        
    def fit_to_height(self):
        # 获取虚拟滚动区域的实际容器高度
        container_height = self.virtual_scroll.height() - 40  # 减去一些边距
        return self.view_controller.fit_to_height(container_height)
        
    def fit_to_container(self):
        # 获取虚拟滚动区域的实际容器尺寸
        container_width = self.virtual_scroll.width() - 40  # 减去一些边距
        container_height = self.virtual_scroll.height() - 40  # 减去一些边距
        return self.view_controller.fit_to_container(container_width, container_height)

    def set_actual_size(self):
        return self.view_controller.set_actual_size()
        
    def on_zoom_combo_changed(self, text):
        """处理缩放比例下拉列表的变化"""
        try:
            # 从文本中提取数值（例如从"100%"提取100）
            zoom_value = int(float(text.replace('%', '')))
            # 将百分比转换为小数（例如100% -> 1.0）
            zoom_factor = zoom_value / 100.0
            
            # 调用PDF处理器设置缩放
            success, message = self.pdf_processor.set_zoom(zoom_factor)
            if success:
                # 更新预览
                self.update_preview()
                
                # 更新缩放标签显示（已移除）
                # if hasattr(self, 'zoom_label'):
                #     self.zoom_label.setText(f"{zoom_value}%")
                    
                # 更新下拉列表显示，以防输入了无效值
                self.zoom_combo.setCurrentText(f"{zoom_value}%")
                
            self.show_message(message)
        except ValueError:
            # 如果转换失败，保持当前缩放
            current_zoom = int(self.pdf_processor.get_zoom() * 100)
            self.zoom_combo.setCurrentText(f"{current_zoom}%")
            self.show_message(f"无效的缩放值: {text}")
        except Exception as e:
            logger.error(f"设置缩放比例失败: {e}")
            self.show_message(f"设置缩放比例失败: {str(e)}")

    def update_zoom_label(self):
        """更新缩放显示 - 已移除缩放显示功能"""
        # 此方法保留以兼容调用，但不执行任何操作
        pass
    
    def _find_closest_zoom_level(self, current_zoom):
        """查找最接近的预定义缩放级别"""
        zoom_levels = [0.08, 0.125, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0, 12.0, 16.0, 24.0, 32.0, 48.0, 64.0]
        
        # 找到最接近当前缩放级别的预定义级别
        closest_level = min(zoom_levels, key=lambda x: abs(x - current_zoom))
        return closest_level

def get_app_icon():
    """获取应用程序图标，优先使用外部图标文件，否则使用内置生成的图标"""
    import os
    from PyQt5.QtGui import QIcon
    
    # 尝试加载外部图标文件
    icon_paths = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app', 'assets', 'app_icon.ico'),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app', 'assets', 'app_icon.png'),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'app_icon.ico'),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'app_icon.png')
    ]
    
    for icon_path in icon_paths:
        if os.path.exists(icon_path):
            return QIcon(icon_path)
    
    # 如果外部图标文件不存在，则生成内置图标
    return create_builtin_icon()


def create_builtin_icon():
    """创建内置应用程序图标"""
    from PyQt5.QtGui import QPixmap, QPainter, QColor, QPen, QFont
    # 创建一个128x128像素的图标
    pixmap = QPixmap(128, 128)
    pixmap.fill(QColor(255, 255, 255))  # 白色背景
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    
    # 绘制蓝色矩形代表PDF文档
    painter.setBrush(QColor(0, 100, 200))  # 深蓝色填充
    painter.setPen(QPen(QColor(0, 80, 160), 4))  # 蓝色边框
    painter.drawRect(20, 20, 88, 88)  # 主体矩形
    
    # 绘制PDF文字
    font = QFont()
    font.setPointSize(20)
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(QColor(255, 255, 255))  # 白色文字
    painter.drawText(35, 70, "PDF")
    
    # 绘制一个简单的'A'字母代表Aurora
    font.setPointSize(16)
    painter.setFont(font)
    painter.drawText(45, 95, "A")
    
    painter.end()
    
    from PyQt5.QtGui import QIcon
    return QIcon(pixmap)


def main():
    """主函数"""
    from PyQt5.QtWidgets import QApplication
    from app.config.settings import AppSettings
    
    app = QApplication(sys.argv)
    
    app.setApplicationName(AppSettings.APP_NAME)
    app.setApplicationVersion(AppSettings.APP_VERSION)
    app.setOrganizationName(AppSettings.ORGANIZATION)
    
    # 设置应用程序图标
    app_icon = get_app_icon()
    app.setWindowIcon(app_icon)
    
    viewer = AuroraPDF()
    # 为窗口也设置图标
    viewer.setWindowIcon(app_icon)
    viewer.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()