import os
import base64
import traceback
import fitz  # PyMuPDF
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
import json


from app.utils.logger import get_logger

logger = get_logger('ocr_searchable_pdf')


class OCRSearchablePDF:
    def __init__(self, ocr_plugin_manager=None, ocr_config_manager=None):
        self.ocr_plugin_manager = ocr_plugin_manager
        self.ocr_config_manager = ocr_config_manager

    def pdf_to_searchable_pdf(self, pdf_path, output_path, show_text_boxes=False, progress_callback=None):
        """
        将PDF文件进行OCR处理，生成可搜索的PDF

        :param pdf_path: 输入PDF文件路径
        :param output_path: 输出可搜索PDF文件路径
        :param show_text_boxes: 是否显示文本框背景色（用于调试）
        :param progress_callback: 进度回调函数 (percent, message) -> None
        :return: 是否成功
        """
        try:
            if progress_callback:
                progress_callback(5, "正在打开PDF文件...")

            # 打开PDF文档
            doc = fitz.open(pdf_path)
            total_pages = len(doc)

            # 创建新的PDF文档用于输出
            output_doc = fitz.open()

            # 用于存储每页的OCR结果
            ocr_results = {}

            # 改用顺序处理，避免OCR插件并发冲突
            logger.info(f"开始处理 {total_pages} 页PDF，使用顺序OCR处理模式...")

            if progress_callback:
                progress_callback(10, f"准备处理 {total_pages} 页...")

            for page_num in range(total_pages):
                page_percent = 10 + int((page_num / total_pages) * 70)  # 10%-80%
                if progress_callback:
                    progress_callback(page_percent, f"正在处理第 {page_num + 1}/{total_pages} 页...")

                try:
                    # 获取当前页
                    page = doc[page_num]

                    # 将页面渲染为图像（使用较高的DPI以获得更好的OCR效果）
                    matrix = fitz.Matrix(2.0, 2.0)  # 2倍缩放
                    pix = page.get_pixmap(matrix=matrix)

                    # 将图像转换为bytes
                    img_data = pix.tobytes("png")

                    # 转换为base64
                    img_base64 = base64.b64encode(img_data).decode('utf-8')

                    # 进行OCR识别
                    ocr_percent = page_percent + int(10 / total_pages)  # 在页面处理内部增加一点进度
                    if progress_callback:
                        progress_callback(ocr_percent, f"正在对第 {page_num + 1}/{total_pages} 页进行OCR识别...")

                    ocr_result = self.call_ocr_api(img_base64)

                    # 保存结果
                    ocr_results[page_num] = {
                        'ocr_result': ocr_result,
                        'page': page,
                        'img_data': img_data,
                        'pix': pix
                    }

                    if ocr_result:
                        logger.info(f"第 {page_num + 1} 页OCR处理完成")
                    else:
                        logger.warning(f"第 {page_num + 1} 页OCR识别返回空结果")

                except Exception as e:
                    logger.error(f"第 {page_num + 1} 页OCR处理失败: {e}")
                    logger.error(traceback.format_exc())

                    # 即使失败也要保存页面信息，避免后续处理出错
                    if 'page' in locals() and 'img_data' in locals() and 'pix' in locals():
                        ocr_results[page_num] = {
                            'ocr_result': None,
                            'page': page,
                            'img_data': img_data,
                            'pix': pix
                        }
                    else:
                        # 如果连页面信息都没获取到，创建一个空的占位符
                        logger.error(f"第 {page_num + 1} 页基础信息获取失败，跳过此页")
                        continue

            if progress_callback:
                progress_callback(85, "正在生成可搜索PDF...")

            # 按页码顺序处理结果并生成PDF
            for page_num in sorted(ocr_results.keys()):
                write_percent = 85 + int((len(ocr_results) - page_num - 1) / total_pages * 10)  # 85%-95%
                if progress_callback:
                    progress_callback(write_percent, f"正在写入第 {page_num + 1}/{total_pages} 页...")

                result_info = ocr_results[page_num]
                page = result_info['page']
                img_data = result_info['img_data']
                pix = result_info['pix']
                ocr_result = result_info['ocr_result']

                # 创建新页面（保持原始页面尺寸）
                new_page = output_doc.new_page(width=page.rect.width, height=page.rect.height)

                # 将原始图像插入到新页面
                new_page.insert_image(new_page.rect, stream=img_data)

                # 如果OCR成功，添加文本层
                if ocr_result and ocr_result.get("code") == 100:
                    # 计算缩放比例
                    scale_x = new_page.rect.width / pix.width
                    scale_y = new_page.rect.height / pix.height

                    self.add_text_layer(new_page, ocr_result.get("data", []), scale_x, scale_y, show_text_boxes)

            if progress_callback:
                progress_callback(98, "正在保存PDF文件...")

            # 如果输出文件已存在，先删除（避免被占用）
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except Exception as remove_error:
                    logger.warning(f"删除旧文件失败: {remove_error}")

            # 保存输出PDF
            output_doc.save(output_path, garbage=4, deflate=True, clean=True)
            output_doc.close()
            doc.close()

            if progress_callback:
                progress_callback(100, "可搜索PDF创建完成")

            logger.info(f"可搜索PDF已保存到: {output_path}")
            return True

        except Exception as e:
            logger.error(f"生成可搜索PDF失败: {e}")
            return False

    def call_ocr_api(self, image_base64):
        """
        调用OCR插件进行文本识别
        
        :param image_base64: 图像的base64编码
        :return: OCR结果
        """
        if not self.ocr_plugin_manager or not self.ocr_config_manager:
            logger.error("OCR插件管理器或配置管理器未初始化")
            return None
            
        try:
            # 获取当前使用的OCR插件
            current_plugin_name = self.ocr_config_manager.get_current_plugin()
            if not current_plugin_name:
                logger.error("未配置OCR插件")
                return None
            
            # 获取插件实例
            plugin = self.ocr_plugin_manager.get_plugin(current_plugin_name)
            if not plugin:
                logger.error(f"OCR插件 '{current_plugin_name}' 未加载")
                return None
            
            # 初始化插件（如果尚未初始化）- 只初始化一次
            if not plugin.is_initialized:
                logger.info(f"正在初始化OCR插件: {current_plugin_name}")
                plugin_config = self.ocr_config_manager.get_plugin_config(current_plugin_name)
                init_result = self.ocr_plugin_manager.initialize_plugin(current_plugin_name, plugin_config)
                if not init_result.is_success():
                    logger.error(f"OCR插件初始化失败: {init_result.message}")
                    return None
                else:
                    logger.info(f"OCR插件初始化成功: {current_plugin_name}")
            
            # 检查base64数据长度，避免过大数据
            if len(image_base64) > 10 * 1024 * 1024:  # 10MB限制
                logger.warning(f"图像数据过大: {len(image_base64)} 字符，可能影响处理速度")
            
            # 调用插件进行OCR识别
            logger.debug(f"开始OCR识别，图像数据长度: {len(image_base64)}")
            ocr_result = plugin.recognize_from_base64(image_base64)
            logger.debug(f"OCR识别完成，结果类型: {type(ocr_result)}")
            
            # 转换为兼容的格式
            if ocr_result and ocr_result.is_success():
                logger.debug(f"OCR识别成功，数据项数: {len(ocr_result.data) if ocr_result.data else 0}")
                return {
                    "code": 100,
                    "data": ocr_result.data,
                    "message": ocr_result.message
                }
            else:
                error_msg = ocr_result.message if ocr_result else "OCR识别返回空结果"
                error_code = ocr_result.code.value if ocr_result and hasattr(ocr_result.code, 'value') else 1000
                logger.error(f"OCR识别失败: {error_msg}")
                return {
                    "code": error_code,
                    "data": None,
                    "message": error_msg
                }
                
        except Exception as e:
            logger.error(f"OCR插件调用失败: {e}")
            logger.debug(f"详细错误信息: {traceback.format_exc()}")
            return None

    def add_text_layer(self, page, text_blocks, scale_x, scale_y, show_text_boxes=False):
        """
        在页面上添加文本层
        
        :param page: PDF页面对象
        :param text_blocks: OCR识别的文本块列表
        :param scale_x: X轴缩放比例
        :param scale_y: Y轴缩放比例
        :param show_text_boxes: 是否显示文本框背景色（用于调试）
        """
        # 内容流清理、语法更正，减少错误
        page.clean_contents()
        
        # 为支持多语言文本搜索，在页面上插入通用字体
        try:
            # 首先尝试使用用户提供的字体文件
            custom_font_path = os.path.join(os.path.dirname(__file__), "fonts", "msyh.ttf")
            logger.debug(f"正在尝试插入用户字体: {custom_font_path}")
            if os.path.exists(custom_font_path):
                page.insert_font(fontfile=custom_font_path, fontname="UniversalFont")
                logger.debug(f"成功插入用户字体: {custom_font_path}")
            else:
                # 如果用户字体不存在，尝试使用系统字体
                system_font_paths = [
                    r"C:\\Windows\\Fonts\\msyh.ttc",     # 微软雅黑
                    r"C:\\Windows\\Fonts\\simhei.ttf",   # 黑体
                    r"C:\\Windows\\Fonts\\simsun.ttc",   # 宋体
                    r"C:\\Windows\\Fonts\\mingliu.ttc",  # 繁体明体
                ]
                
                font_inserted = False
                for font_path in system_font_paths:
                    if os.path.exists(font_path):
                        try:
                            page.insert_font(fontfile=font_path, fontname="UniversalFont")
                            logger.debug(f"成功插入系统字体: {font_path}")
                            font_inserted = True
                            break
                        except Exception as font_error:
                            logger.warning(f"插入系统字体失败 {font_path}: {font_error}")
                
                if not font_inserted:
                    logger.debug("未找到合适的字体文件，使用默认字体")
        except Exception as e:
            logger.warning(f"插入通用字体失败: {e}")
        
        # 获取页面旋转角度
        protation = page.rotation
        
        # 遍历所有文本块
        logger.debug(f"开始添加OCR文本层，共 {len(text_blocks)} 个文本块")
        valid_text_count = 0
        for block in text_blocks:
            text = block.get("text", "")
            # 兼容不同的OCR插件格式：box或bbox
            box = block.get("box", block.get("bbox", []))
                    
            # 更严格的过滤条件，确保只有有效文本才会被添加
            if not text or len(box) != 4:
                continue
                    
            # 过滤掉纯空白字符
            stripped_text = text.strip()
            if not stripped_text:
                continue
                    
                    
            valid_text_count += 1
            logger.debug(f"处理第 {valid_text_count} 个有效文本块: '{stripped_text}'")
                    
            # 根据缩放比例调整坐标
            scaled_box = []
            for point in box:
                scaled_x = point[0] * scale_x
                scaled_y = point[1] * scale_y
                scaled_box.append([scaled_x, scaled_y])
                
            # 获取文本框坐标
            x0, y0 = scaled_box[0]
            x2, y2 = scaled_box[2]
            
            # 计算合适的字体大小
            width = x2 - x0
            height = y2 - y0
            
            # 根据文本长度和边界框宽度动态调整字体大小
            # 平衡防止文本溢出和保持合适字体大小的需求
            if width > 0 and len(text) > 0:
                # 计算每个字符的平均宽度
                avg_char_width = width / len(text)
                # 基于高度计算字体大小
                fontsize_by_height = height * 0.75
                # 基于宽度计算字体大小（增加系数以保持更大字体）
                fontsize_by_width = avg_char_width * 1.2  # 增加系数以保持更大字体
                # 取较小值以确保文本不会超出边界，但不要太小
                fontsize = min(fontsize_by_height, fontsize_by_width)
                # 如果计算出的字体太小，使用基于高度的字体大小并适当缩小
                if fontsize < fontsize_by_height * 0.6:  # 如果字体小于高度计算的60%
                    fontsize = fontsize_by_height * 0.7  # 使用高度计算的70%
            else:
                fontsize = height * 0.75
            
            # 限制字体大小范围
            fontsize = max(min(fontsize, 25), 6)  # 稍微放宽限制
            
            # 不再按空格拆分文本，而是将整个文本作为一个整体插入
            # 这样可以确保文本在文本框内正确显示和定位
            
            # 如果需要显示文本框背景色（用于调试位置）
            if show_text_boxes:
                # 绘制半透明黄色背景矩形（透明度0.3）
                rect = fitz.Rect(x0, y0, x2, y2)
                page.draw_rect(rect, color=(1, 1, 0), fill=(1, 1, 0), width=0, fill_opacity=0.3, overlay=True)
            
            # 计算文本基线位置，使其在框内垂直居中
            baseline_y = (y0 + y2) / 2 + fontsize / 2  # 垂直居中并考虑字体基线
            point = fitz.Point(x0, baseline_y)
            
            # 如果页面有旋转，需要调整坐标以补偿旋转
            if protation != 0:
                # 计算旋转中心点（页面中心）
                center_x = page.rect.width / 2
                center_y = page.rect.height / 2
                
                # 将点转换到以页面中心为原点的坐标系
                rel_x = point.x - center_x
                rel_y = point.y - center_y
                
                # 根据旋转角度调整坐标
                rad = math.radians(-protation)  # 负号是因为我们需要反向旋转
                cos_val = math.cos(rad)
                sin_val = math.sin(rad)
                
                # 应用旋转变换
                new_rel_x = rel_x * cos_val - rel_y * sin_val
                new_rel_y = rel_x * sin_val + rel_y * cos_val
                
                # 转换回原始坐标系
                point = fitz.Point(new_rel_x + center_x, new_rel_y + center_y)
            
            # 检查坐标是否在页面范围内
            page_rect = page.rect
            if point.x < 0:
                point.x = 0
            if point.y < 0:
                point.y = fontsize
            if point.x > page_rect.width:
                point.x = page_rect.width - width if width < page_rect.width else 0
            if point.y > page_rect.height:
                point.y = page_rect.height - fontsize if fontsize < page_rect.height else page_rect.height
            
            # 插入文本
            try:
                if show_text_boxes:
                    # 带背景色的文本（用于调试）
                    page.insert_text(
                        point,
                        text,
                        fontsize=fontsize,
                        fontname="UniversalFont",  # 使用通用字体
                        color=(0, 0, 0),  # 黑色文本
                        fill_opacity=0.7,  # 半透明填充
                        stroke_opacity=0.7  # 半透明描边
                    )
                else:
                    # 透明文本（生产环境使用）
                    page.insert_text(
                        point,
                        text,
                        fontsize=fontsize,
                        fontname="UniversalFont",  # 使用通用字体
                        fill_opacity=0,  # 透明度为0，完全透明
                        stroke_opacity=0  # 描边透明度为0
                    )
            except Exception as e:
                logger.warning(f"插入文本失败: {text}, 错误: {e}")
                # 尝试使用更小的字体
                try:
                    if show_text_boxes:
                        page.insert_text(
                            point,
                            text,
                            fontsize=max(fontsize/2, 3),
                            fontname="UniversalFont",  # 使用通用字体
                            color=(0, 0, 0),
                            fill_opacity=0.7,
                            stroke_opacity=0.7
                        )
                    else:
                        page.insert_text(
                            point,
                            text,
                            fontsize=max(fontsize/2, 3),
                            fontname="UniversalFont",  # 使用通用字体
                            fill_opacity=0,
                            stroke_opacity=0
                        )
                except Exception as e2:
                    logger.error(f"再次插入文本也失败: {text}, 错误: {e2}")


def create_searchable_pdf(input_pdf_path, output_pdf_path, ocr_plugin_manager=None, ocr_config_manager=None, show_text_boxes=False, progress_callback=None):
    """
    创建可搜索PDF的便捷函数

    :param input_pdf_path: 输入PDF文件路径
    :param output_pdf_path: 输出PDF文件路径
    :param ocr_plugin_manager: OCR插件管理器
    :param ocr_config_manager: OCR配置管理器
    :param show_text_boxes: 是否显示文本框背景色（用于调试）
    :param progress_callback: 进度回调函数 (percent, message) -> None
    :return: 是否成功
    """
    processor = OCRSearchablePDF(ocr_plugin_manager, ocr_config_manager)
    return processor.pdf_to_searchable_pdf(input_pdf_path, output_pdf_path, show_text_boxes, progress_callback)