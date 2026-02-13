"""OCR批量处理线程"""

from PyQt5.QtCore import QThread, pyqtSignal
from app.utils.logger import get_logger

logger = get_logger('ocr_batch_thread')


class OCRBatchThread(QThread):
    """OCR批量处理后台线程"""

    # 信号定义
    progress_update = pyqtSignal(int, int, str)  # (当前页, 总页数, 消息)
    page_completed = pyqtSignal(int, dict)  # (页码, OCR结果)
    batch_finished = pyqtSignal(dict)  # (汇总结果)
    error_occurred = pyqtSignal(str)  # (错误消息)

    def __init__(self, pdf_processor, ocr_plugin_manager, ocr_config_manager):
        """初始化OCR批量处理线程

        Args:
            pdf_processor: PDF处理器
            ocr_plugin_manager: OCR插件管理器
            ocr_config_manager: OCR配置管理器
        """
        super().__init__()
        self.pdf_processor = pdf_processor
        self.ocr_plugin_manager = ocr_plugin_manager
        self.ocr_config_manager = ocr_config_manager
        self._is_running = True
        self._is_paused = False
        self._should_cancel = False

    def run(self):
        """执行批量OCR处理"""
        try:
            # 获取当前使用的OCR插件
            current_plugin_name = self.ocr_config_manager.get_current_plugin()
            if not current_plugin_name:
                self.error_occurred.emit("请先在OCR设置中选择一个OCR插件")
                return

            # 检查插件是否已加载
            if current_plugin_name not in self.ocr_plugin_manager.plugins:
                self.error_occurred.emit(f"OCR插件 '{current_plugin_name}' 未加载")
                return

            # 获取插件实例
            plugin = self.ocr_plugin_manager.plugins[current_plugin_name]

            # 初始化插件（如果尚未初始化）
            if not plugin.is_initialized:
                plugin_config = self.ocr_config_manager.get_plugin_config(current_plugin_name)
                init_result = self.ocr_plugin_manager.initialize_plugin(current_plugin_name, plugin_config)
                if not init_result.is_success():
                    self.error_occurred.emit(f"插件初始化失败: {init_result.message}")
                    return

            # 获取总页数
            total_pages = self.pdf_processor.get_total_pages()
            if total_pages == 0:
                self.error_occurred.emit("文档为空，没有可识别的页面")
                return

            # 汇总结果
            batch_result = {
                'total_pages': total_pages,
                'success_pages': 0,
                'failed_pages': 0,
                'results': {},  # {页码: OCR结果}
                'errors': {}  # {页码: 错误消息}
            }

            # 遍历所有页面
            for page_num in range(total_pages):
                # 检查是否被取消
                if self._should_cancel:
                    logger.info("OCR批量处理被用户取消")
                    break

                # 检查是否暂停
                while self._is_paused:
                    self.msleep(100)  # 暂停时每100ms检查一次
                    if self._should_cancel:
                        logger.info("OCR批量处理在暂停时被用户取消")
                        break

                # 更新进度
                self.progress_update.emit(page_num, total_pages, f"正在识别第 {page_num + 1} 页...")

                try:
                    # 获取页面图像数据
                    page_image_data = self.pdf_processor.get_page_image_data(page_num)
                    if not page_image_data:
                        error_msg = f"无法获取第 {page_num + 1} 页的图像数据"
                        logger.error(error_msg)
                        batch_result['errors'][page_num] = error_msg
                        batch_result['failed_pages'] += 1
                        continue

                    # 执行OCR识别
                    # 方法1: 直接使用字节数据
                    ocr_result = plugin.recognize_from_bytes(page_image_data)

                    # 如果方法1失败，尝试方法2: 转换为Base64字符串
                    if not ocr_result.is_success():
                        from base64 import b64encode
                        image_base64 = b64encode(page_image_data).decode('utf-8')
                        if image_base64.startswith('data:image'):
                            image_base64 = image_base64.split(',')[1] if ',' in image_base64 else image_base64
                        ocr_result = plugin.recognize_from_base64(image_base64)

                    # 如果方法2也失败，尝试方法3: 保存为临时文件
                    if not ocr_result.is_success():
                        import os
                        import tempfile
                        import uuid
                        temp_dir = os.path.realpath(tempfile.gettempdir())
                        temp_filename = f"ocr_temp_{uuid.uuid4().hex}.png"
                        tmp_file_path = os.path.join(temp_dir, temp_filename)

                        try:
                            with open(tmp_file_path, 'wb') as tmp_file:
                                tmp_file.write(page_image_data)

                            if os.path.exists(tmp_file_path):
                                ocr_result = plugin.recognize_from_file(tmp_file_path)
                            else:
                                logger.error(f"临时文件创建失败: {tmp_file_path}")
                                raise Exception("临时文件创建失败")
                        except Exception as file_error:
                            logger.error(f"创建临时文件时出错: {file_error}")
                            raise file_error
                        finally:
                            try:
                                if os.path.exists(tmp_file_path):
                                    os.unlink(tmp_file_path)
                            except Exception:
                                pass

                    # 处理识别结果
                    if ocr_result.is_success():
                        # 提取文本和数据
                        text_list = []
                        bboxes = []
                        confidence_list = []

                        logger.debug(f"第 {page_num + 1} 页OCR返回数据类型: {type(ocr_result.data)}")

                        if isinstance(ocr_result.data, list):
                            logger.debug(f"第 {page_num + 1} 页OCR返回列表长度: {len(ocr_result.data)}")
                            for item in ocr_result.data:
                                if isinstance(item, dict):
                                    text = item.get('text', '')
                                    text_list.append(text)
                                    if 'bbox' in item:
                                        bboxes.append(item['bbox'])
                                    if 'confidence' in item:
                                        confidence_list.append(item['confidence'])
                                    logger.debug(f"提取文本: '{text}', bbox: {item.get('bbox')}, confidence: {item.get('confidence')}")
                        elif isinstance(ocr_result.data, str):
                            # 如果data是字符串，直接使用
                            text_list = [ocr_result.data]
                            logger.debug(f"第 {page_num + 1} 页OCR返回字符串: '{ocr_result.data[:100]}...'")
                        else:
                            logger.warning(f"第 {page_num + 1} 页OCR返回未知数据类型: {type(ocr_result.data)}")

                        full_text = '\n'.join(text_list)
                        logger.info(f"第 {page_num + 1} 页OCR完成，识别文本长度: {len(full_text)}")

                        batch_result['results'][page_num] = {
                            'text': full_text,
                            'bboxes': bboxes if bboxes else None,
                            'confidence': confidence_list if confidence_list else None
                        }
                        batch_result['success_pages'] += 1

                        # 发送页面完成信号
                        self.page_completed.emit(page_num, batch_result['results'][page_num])
                    else:
                        error_msg = f"OCR识别失败: {ocr_result.message}"
                        logger.error(f"第 {page_num + 1} 页{error_msg}")
                        batch_result['errors'][page_num] = error_msg
                        batch_result['failed_pages'] += 1

                except Exception as e:
                    error_msg = f"处理第 {page_num + 1} 页时发生异常: {str(e)}"
                    logger.error(error_msg)
                    import traceback
                    logger.error(traceback.format_exc())
                    batch_result['errors'][page_num] = error_msg
                    batch_result['failed_pages'] += 1

            # 发送完成信号
            self.batch_finished.emit(batch_result)
            logger.info(f"OCR批量处理完成: 成功 {batch_result['success_pages']} 页，失败 {batch_result['failed_pages']} 页")

        except Exception as e:
            error_msg = f"OCR批量处理线程异常: {str(e)}"
            logger.error(error_msg)
            import traceback
            logger.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def pause(self):
        """暂停批量处理"""
        self._is_paused = True
        logger.info("请求暂停OCR批量处理")

    def resume(self):
        """继续批量处理"""
        self._is_paused = False
        logger.info("请求继续OCR批量处理")

    def cancel(self):
        """取消批量处理"""
        self._should_cancel = True
        self._is_paused = False  # 取消时也要解除暂停
        logger.info("请求取消OCR批量处理")
