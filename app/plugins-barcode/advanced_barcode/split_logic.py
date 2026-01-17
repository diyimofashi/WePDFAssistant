"""
高级条码拆分 - 拆分逻辑实现
支持首页规则、尾页规则、分隔页规则
"""

import os
import fitz
from io import BytesIO
from PIL import Image
import pyzbar.pyzbar as pyzbar
from typing import Dict, List, Any
from app.utils.logger import get_logger

logger = get_logger(__name__)


class BarcodeInfo:
    def __init__(self, data, type, rect, page_num):
        self.data = data
        self.type = type
        self.rect = rect
        self.page_num = page_num


def detect_barcodes_enhanced(doc: fitz.Document, config: Dict[str, Any], progress_callback=None) -> List[BarcodeInfo]:
    """使用增强方法检测文档中的所有条码"""
    try:
        all_barcodes = []
        total_pages = len(doc)
        dpi_values = [300, 200, 150]
        horizontal_only = config.get('horizontal_only', False)
        filter_region = config.get('filter_region', None)
        max_barcode_count = config.get('max_barcode_count', 100)

        for page_num in range(total_pages):
            page = doc[page_num]
            page_barcodes = set()

            # 更新进度
            if progress_callback:
                progress = page_num + 1  # 当前页码（从1开始）
                progress_callback(progress, total_pages, f"正在检测条码: {page_num + 1}/{total_pages} 页")

            # 检测嵌入图片
            image_list = page.get_images()
            for img_index, img in enumerate(image_list):
                try:
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    img_obj = Image.open(BytesIO(image_bytes))
                    if img_obj.mode != 'RGB':
                        img_obj = img_obj.convert('RGB')

                    codes = pyzbar.decode(img_obj)
                    for code in codes:
                        if _passes_filters(code, horizontal_only, filter_region):
                            try:
                                barcode_data_str = code.data.decode('utf-8', errors='replace')
                                key = (barcode_data_str, page_num)
                                if key not in page_barcodes:
                                    barcode = BarcodeInfo(barcode_data_str, code.type, code.rect, page_num)
                                    page_barcodes.add(key)
                                    all_barcodes.append(barcode)
                            except Exception:
                                pass
                except Exception:
                    continue

            # 渲染页面检测
            for dpi in dpi_values:
                mat = fitz.Matrix(dpi / 72, dpi / 72)
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("ppm")
                img = Image.open(BytesIO(img_data))
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                codes = pyzbar.decode(img)
                for code in codes:
                    if _passes_filters(code, horizontal_only, filter_region):
                        try:
                            barcode_data_str = code.data.decode('utf-8', errors='replace')
                            key = (barcode_data_str, page_num)
                            if key not in page_barcodes:
                                barcode = BarcodeInfo(barcode_data_str, code.type, code.rect, page_num)
                                page_barcodes.add(key)
                                all_barcodes.append(barcode)
                        except Exception:
                            pass

                if len([b for b in all_barcodes if b.page_num == page_num]) >= max_barcode_count:
                    break

        return all_barcodes
    except Exception:
        logger.error("条码检测失败", exc_info=True)
        return []


def _passes_filters(code, horizontal_only: bool, filter_region) -> bool:
    """检查条码是否通过方向和区域过滤"""
    if horizontal_only:
        width = code.rect.width
        height = code.rect.height
        if width < height:
            return False

    if filter_region:
        x1, y1, x2, y2 = filter_region
        if (code.rect.left < x1 or code.rect.top < y1 or
            code.rect.right > x2 or code.rect.bottom > y2):
            return False

    return True


def filter_barcodes(barcodes: List[BarcodeInfo], config: Dict[str, Any]) -> List[BarcodeInfo]:
    """根据配置过滤条码"""
    try:
        min_length = int(config.get('min_length', 1))
        max_length = int(config.get('max_length', 1000))
        include_keywords = config.get('include_keywords', [])
        exclude_keywords = config.get('exclude_keywords', [])
        include_regex = config.get('include_regex', '')
        exclude_regex = config.get('exclude_regex', '')
        remove_barcode_pages = config.get('remove_barcode_pages', False)
        split_position_rule = config.get('split_position_rule', 'first_page')
        logger.debug(f"开始过滤条码: min_length={min_length}, max_length={max_length}, "
                    f"include_keywords={include_keywords}, exclude_keywords={exclude_keywords}")

        filtered_barcodes = []
        for barcode in barcodes:
            barcode_data_str = barcode.data

            if not isinstance(barcode_data_str, str):
                try:
                    barcode_data_str = str(barcode_data_str)
                except Exception:
                    continue

            barcode_len = len(barcode_data_str)
            if barcode_len < min_length or barcode_len > max_length:
                continue

            if include_keywords:
                if not any(k.lower() in barcode_data_str.lower() for k in include_keywords):
                    continue

            if exclude_keywords:
                if any(k.lower() in barcode_data_str.lower() for k in exclude_keywords):
                    continue

            if include_regex:
                import re
                try:
                    if not re.search(include_regex, barcode_data_str):
                        continue
                except re.error:
                    pass

            if exclude_regex:
                import re
                try:
                    if re.search(exclude_regex, barcode_data_str):
                        continue
                except re.error:
                    pass

            filtered_barcodes.append(barcode)

        return filtered_barcodes
    except Exception:
        logger.error("条码过滤失败", exc_info=True)
        return []


def split_by_first_page_rule(doc: fitz.Document, barcodes: List[BarcodeInfo],
                              config: Dict[str, Any], output_dir: str,
                              progress_callback=None, clean_filename_func=None) -> List[str]:
    """
    首页规则：遇到条码就开始新文档，条码页当作新文档的第一页。
    """
    try:
        files_created = []
        total_pages = len(doc)

        # 构建页码到条码的映射（每页只取第一个条码）
        page_barcode_map = {}
        for barcode in barcodes:
            if barcode.page_num not in page_barcode_map:
                page_barcode_map[barcode.page_num] = barcode.data

        groups = []
        current_group_pages = []
        current_group_barcode = None
        has_encountered_barcode = False

        for page_num in range(total_pages):
            # 如果当前页有条码，开始新分组
            if page_num in page_barcode_map:
                has_encountered_barcode = True

                # 保存之前的分组（如果有）
                if current_group_pages:
                    groups.append({
                        'pages': current_group_pages.copy(),
                        'barcode': current_group_barcode
                    })
                    current_group_pages = []

                # 以当前条码页开始新分组
                current_group_barcode = page_barcode_map[page_num]
                current_group_pages = [page_num]
            else:
                # 如果已经有分组（即遇到过条码），将无条码页加入当前分组
                if current_group_barcode is not None:
                    current_group_pages.append(page_num)
                # 如果还没遇到过条码，跳过（不创建无条码文档）

        # 保存最后一个分组
        if current_group_pages:
            groups.append({
                'pages': current_group_pages,
                'barcode': current_group_barcode
            })

        # 合并相同条码的分组
        merge_same = config.get('merge_same_barcode', False)
        if merge_same:
            merged_groups = {}
            for group in groups:
                barcode_value = group['barcode']
                if barcode_value not in merged_groups:
                    merged_groups[barcode_value] = {
                        'pages': [],
                        'barcode': barcode_value
                    }
                # 合并页面
                merged_groups[barcode_value]['pages'].extend(group['pages'])
            # 替换分组列表
            groups = list(merged_groups.values())

        # 为每个组创建文件
        barcode_file_counts = {}
        file_index = 0

        for group in groups:
            pages = group['pages']
            if not pages:
                continue

            new_doc = fitz.open()
            for page_num in pages:
                new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)

            barcode_value = group['barcode']
            clean_barcode = clean_filename_func(barcode_value) if barcode_value and clean_filename_func else barcode_value

            if barcode_value:
                # 如果启用了合并相同条码，使用序号；否则使用索引
                if merge_same:
                    if barcode_value not in barcode_file_counts:
                        barcode_file_counts[barcode_value] = 0
                    barcode_file_counts[barcode_value] += 1
                    file_count = barcode_file_counts[barcode_value]
                    filename = f"{clean_barcode}_{file_count:03d}.pdf"
                else:
                    formatted_index = f"{file_index + 1:03d}"
                    filename = f"{clean_barcode}_{formatted_index}.pdf"
            else:
                formatted_index = f"{file_index + 1:03d}"
                filename = f"无条码_{formatted_index}.pdf"

            file_path = os.path.join(output_dir, filename)
            counter = 1
            while os.path.exists(file_path):
                name, ext = os.path.splitext(filename)
                file_path = os.path.join(output_dir, f"{name}_{counter}{ext}")
                counter += 1

            new_doc.save(file_path)
            new_doc.close()
            files_created.append(file_path)
            file_index += 1

            if progress_callback:
                progress = 50 + int((file_index / max(1, len(groups))) * 50)
                progress_callback(progress, 100, f"已创建 {file_index}/{len(groups)} 个文件")

        return files_created
    except Exception:
        logger.error("分隔页规则拆分失败", exc_info=True)
        return []


def split_by_last_page_rule(doc: fitz.Document, barcodes: List[BarcodeInfo],
                             config: Dict[str, Any], output_dir: str,
                             progress_callback=None, clean_filename_func=None) -> List[str]:
    """
    尾页规则：把读到条码的页当成上一文档的结尾，该页及之后的内容归入下一个文档。
    """
    try:
        files_created = []
        total_pages = len(doc)

        page_barcode_map = {}
        for barcode in barcodes:
            if barcode.page_num not in page_barcode_map:
                page_barcode_map[barcode.page_num] = []
            page_barcode_map[barcode.page_num].append(barcode)

        groups = []
        current_group = []
        current_barcode = None

        for page_num in range(total_pages):
            current_group.append(page_num)

            if page_num in page_barcode_map and page_barcode_map[page_num]:
                groups.append({
                    'pages': current_group.copy(),
                    'barcode': current_barcode
                })
                current_group = []
                current_barcode = page_barcode_map[page_num][0].data

        # 添加最后一组
        if current_group:
            groups.append({
                'pages': current_group.copy(),
                'barcode': current_barcode
            })

        # 合并相同条码的分组
        merge_same = config.get('merge_same_barcode', False)
        if merge_same:
            merged_groups = {}
            for group in groups:
                barcode_value = group['barcode']
                if barcode_value not in merged_groups:
                    merged_groups[barcode_value] = {
                        'pages': [],
                        'barcode': barcode_value
                    }
                # 合并页面
                merged_groups[barcode_value]['pages'].extend(group['pages'])
            # 替换分组列表
            groups = list(merged_groups.values())

        # 为每个组创建文件
        barcode_file_counts = {}
        file_index = 0

        for group in groups:
            pages = group['pages']
            if not pages:
                continue

            new_doc = fitz.open()
            for page_num in pages:
                new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)

            barcode_value = group['barcode']
            clean_barcode = clean_filename_func(barcode_value) if barcode_value and clean_filename_func else barcode_value

            if barcode_value:
                # 如果启用了合并相同条码，使用序号；否则使用索引
                if merge_same:
                    if barcode_value not in barcode_file_counts:
                        barcode_file_counts[barcode_value] = 0
                    barcode_file_counts[barcode_value] += 1
                    file_count = barcode_file_counts[barcode_value]
                    filename = f"{clean_barcode}_{file_count:03d}.pdf"
                else:
                    formatted_index = f"{file_index + 1:03d}"
                    filename = f"{clean_barcode}_{formatted_index}.pdf"
            else:
                formatted_index = f"{file_index + 1:03d}"
                filename = f"无条码_{formatted_index}.pdf"

            file_path = os.path.join(output_dir, filename)
            counter = 1
            while os.path.exists(file_path):
                name, ext = os.path.splitext(filename)
                file_path = os.path.join(output_dir, f"{name}_{counter}{ext}")
                counter += 1

            new_doc.save(file_path)
            new_doc.close()
            files_created.append(file_path)
            file_index += 1

            if progress_callback:
                progress = 50 + int((file_index / max(1, len(groups))) * 50)
                progress_callback(progress, 100, f"已创建 {file_index}/{len(groups)} 个文件")

        return files_created
    except Exception:
        logger.error("分隔页规则拆分失败", exc_info=True)
        return []


def split_by_separator_page_rule(doc: fitz.Document, barcodes: List[BarcodeInfo],
                                config: Dict[str, Any], output_dir: str,
                                progress_callback=None, clean_filename_func=None) -> List[str]:
    """
    分隔页规则：遇到包含特定条码的页面时，将该条码作为新组的文件名。
    - remove_barcode_pages=True: 移除包含条码的页面
    - remove_barcode_pages=False: 保留包含条码的页面
    """
    try:
        files_created = []
        total_pages = len(doc)

        page_barcode_map = {}
        for barcode in barcodes:
            if barcode.page_num not in page_barcode_map:
                page_barcode_map[barcode.page_num] = []
            page_barcode_map[barcode.page_num].append(barcode)

        logger.debug(f"条码页码映射: {[(p+1, [b.data for b in bc]) for p, bc in page_barcode_map.items()]}")

        remove_barcode_pages = config.get('remove_barcode_pages', False)

        # 构建分组：分隔页规则
        # remove_barcode_pages=True: 遇到条码页时移除该页，将后续内容作为新组（使用条码作为文件名）
        # remove_barcode_pages=False: 遇到条码页时保留该页，将后续内容作为新组（使用条码作为文件名）
        groups = []
        current_group = []
        current_barcode = None

        for page_num in range(total_pages):
            if page_num in page_barcode_map and page_barcode_map[page_num]:
                # 遇到包含条码的页面
                barcode_list = page_barcode_map[page_num]
                barcode_value = barcode_list[0].data

                # 保存当前组（如果有内容）
                if current_group:
                    groups.append({
                        'pages': current_group.copy(),
                        'barcode': current_barcode
                    })
                    current_group = []

                # 更新当前条码值，作为下一个组的文件名
                current_barcode = barcode_value

                # 如果不移除条码页，则将条码页加入当前组
                if not remove_barcode_pages:
                    current_group.append(page_num)
                # 如果移除条码页，则跳过该页（current_barcode已更新，但页面不加入）
            else:
                # 无条码页面，添加到当前组
                current_group.append(page_num)

        # 处理最后一组
        if current_group:
            groups.append({
                'pages': current_group.copy(),
                'barcode': current_barcode
            })

        # 合并相同条码的分组
        merge_same = config.get('merge_same_barcode', False)
        if merge_same:
            merged_groups = {}
            for group in groups:
                barcode_value = group['barcode']
                if barcode_value not in merged_groups:
                    merged_groups[barcode_value] = {
                        'pages': [],
                        'barcode': barcode_value
                    }
                # 合并页面
                merged_groups[barcode_value]['pages'].extend(group['pages'])
            # 替换分组列表
            groups = list(merged_groups.values())

        file_index = 0

        for group in groups:
            pages = group['pages']
            if not pages:
                continue

            new_doc = fitz.open()
            for page_num in pages:
                new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)

            barcode_value = group['barcode']

            clean_barcode = clean_filename_func(barcode_value) if barcode_value and clean_filename_func else barcode_value

            if barcode_value:
                # 如果启用了合并相同条码，使用序号；否则使用索引
                if merge_same:
                    # 使用合并后的组内计数
                    filename = f"{clean_barcode}.pdf"
                else:
                    formatted_index = f"{file_index + 1:03d}"
                    filename = f"{clean_barcode}_{formatted_index}.pdf"
            else:
                formatted_index = f"{file_index + 1:03d}"
                filename = f"无条码_{formatted_index}.pdf"

            file_path = os.path.join(output_dir, filename)
            counter = 1
            while os.path.exists(file_path):
                name, ext = os.path.splitext(filename)
                file_path = os.path.join(output_dir, f"{name}_{counter}{ext}")
                counter += 1

            new_doc.save(file_path)
            new_doc.close()
            files_created.append(file_path)
            file_index += 1

            if progress_callback:
                progress = 50 + int((file_index / max(1, len(groups))) * 50)
                progress_callback(progress, 100, f"已创建 {file_index}/{len(groups)} 个文件")

        return files_created
    except Exception:
        logger.error("分隔页规则拆分失败", exc_info=True)
        return []


def preview_first_page_rule(total_pages: int, barcodes: List[BarcodeInfo],
                          config: Dict[str, Any], clean_filename_func=None) -> List[Dict[str, Any]]:
    """预览首页规则拆分结果"""
    try:
        page_barcode_map = {}
        for barcode in barcodes:
            if barcode.page_num not in page_barcode_map:
                page_barcode_map[barcode.page_num] = []
            page_barcode_map[barcode.page_num].append(barcode)

        groups = []
        current_group = []
        current_barcode = None

        for page_num in range(total_pages):
            if page_num in page_barcode_map and page_barcode_map[page_num]:
                if current_group:
                    groups.append({
                        'pages': current_group.copy(),
                        'barcode': current_barcode
                    })
                    current_group = []

                barcode_list = page_barcode_map[page_num]
                for barcode in barcode_list:
                    groups.append({
                        'pages': [page_num],
                        'barcode': barcode.data
                    })
                    current_barcode = barcode.data
            else:
                if current_barcode is not None:
                    current_group.append(page_num)

        assigned_pages = set()
        for group in groups:
            assigned_pages.update(group['pages'])

        unassigned_pages = [p for p in range(total_pages) if p not in assigned_pages]
        if unassigned_pages:
            groups.append({
                'pages': unassigned_pages,
                'barcode': None
            })

        preview_groups = []
        file_index = 0

        for group in groups:
            pages = group['pages']
            barcode_value = group['barcode']
            clean_barcode = clean_filename_func(barcode_value) if barcode_value and clean_filename_func else barcode_value

            if barcode_value:
                formatted_index = f"{file_index + 1:03d}"
                filename = f"{clean_barcode}_{formatted_index}.pdf"
            else:
                formatted_index = f"{file_index + 1:03d}"
                filename = f"无条码_{formatted_index}.pdf"

            preview_groups.append({
                "barcode": barcode_value or "",
                "filename": filename,
                "pages": [p + 1 for p in pages],
                "page_count": len(pages)
            })

            file_index += 1

        return preview_groups
    except Exception:
        return []


def preview_last_page_rule(total_pages: int, barcodes: List[BarcodeInfo],
                           config: Dict[str, Any], clean_filename_func=None) -> List[Dict[str, Any]]:
    """预览尾页规则拆分结果"""
    try:
        page_barcode_map = {}
        for barcode in barcodes:
            if barcode.page_num not in page_barcode_map:
                page_barcode_map[barcode.page_num] = []
            page_barcode_map[barcode.page_num].append(barcode)

        groups = []
        current_group = []
        current_barcode = None

        for page_num in range(total_pages):
            current_group.append(page_num)

            if page_num in page_barcode_map and page_barcode_map[page_num]:
                groups.append({
                    'pages': current_group.copy(),
                    'barcode': current_barcode
                })
                current_group = []
                current_barcode = page_barcode_map[page_num][0].data

        if current_group:
            groups.append({
                'pages': current_group.copy(),
                'barcode': current_barcode
            })

        preview_groups = []
        file_index = 0

        for group in groups:
            pages = group['pages']
            barcode_value = group['barcode']
            clean_barcode = clean_filename_func(barcode_value) if barcode_value and clean_filename_func else barcode_value

            if barcode_value:
                formatted_index = f"{file_index + 1:03d}"
                filename = f"{clean_barcode}_{formatted_index}.pdf"
            else:
                formatted_index = f"{file_index + 1:03d}"
                filename = f"无条码_{formatted_index}.pdf"

            preview_groups.append({
                "barcode": barcode_value or "",
                "filename": filename,
                "pages": [p + 1 for p in pages],
                "page_count": len(pages)
            })

            file_index += 1

        return preview_groups
    except Exception:
        return []


def preview_separator_page_rule(total_pages: int, barcodes: List[BarcodeInfo],
                              config: Dict[str, Any], clean_filename_func=None) -> List[Dict[str, Any]]:
    """预览分隔页规则拆分结果"""
    try:
        page_barcode_map = {}
        for barcode in barcodes:
            if barcode.page_num not in page_barcode_map:
                page_barcode_map[barcode.page_num] = []
            page_barcode_map[barcode.page_num].append(barcode)

        logger.debug(f"条码页码映射: {[(p+1, [b.data for b in bc]) for p, bc in page_barcode_map.items()]}")

        remove_barcode_pages = config.get('remove_barcode_pages', False)

        # 构建分组：分隔页规则
        # remove_barcode_pages=True: 遇到条码页时移除该页，将后续内容作为新组（使用条码作为文件名）
        # remove_barcode_pages=False: 遇到条码页时保留该页，将后续内容作为新组（使用条码作为文件名）
        groups = []
        current_group = []
        current_barcode = None

        for page_num in range(total_pages):
            if page_num in page_barcode_map and page_barcode_map[page_num]:
                # 遇到包含条码的页面
                barcode_list = page_barcode_map[page_num]
                barcode_value = barcode_list[0].data

                # 保存当前组（如果有内容）
                if current_group:
                    groups.append({
                        'pages': current_group.copy(),
                        'barcode': current_barcode
                    })
                    current_group = []

                # 更新当前条码值，作为下一个组的文件名
                current_barcode = barcode_value

                # 如果不移除条码页，则将条码页加入当前组
                if not remove_barcode_pages:
                    current_group.append(page_num)
                # 如果移除条码页，则跳过该页（current_barcode已更新，但页面不加入）
            else:
                # 无条码页面，添加到当前组
                current_group.append(page_num)

        # 处理最后一组
        if current_group:
            groups.append({
                'pages': current_group.copy(),
                'barcode': current_barcode
            })

        preview_groups = []
        file_index = 0

        for group in groups:
            pages = group['pages']
            if not pages:
                continue

            barcode_value = group['barcode']

            clean_barcode = clean_filename_func(barcode_value) if barcode_value and clean_filename_func else barcode_value

            if barcode_value:
                formatted_index = f"{file_index + 1:03d}"
                filename = f"{clean_barcode}_{formatted_index}.pdf"
            else:
                formatted_index = f"{file_index + 1:03d}"
                filename = f"无条码_{formatted_index}.pdf"

            preview_groups.append({
                "barcode": barcode_value or "",
                "filename": filename,
                "pages": [p + 1 for p in pages],
                "page_count": len(pages)
            })

            file_index += 1

        return preview_groups
    except Exception:
        return []
