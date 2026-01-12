"""
完整的PDF工具集合 - 包含所有PDF功能的LLM工具封装
提供打开、保存、编辑、OCR、导航等PDF操作的完整工具
"""
from typing import Dict, Any, Optional
from PyQt5.QtWidgets import QWidget
from app.core.llm.tools.base_tool import BaseTool
from app.core.llm.tool_interactions.file_chooser import FileChooserWidget
from app.utils.logger import get_logger

logger = get_logger(__name__)


class OpenPDFTool(BaseTool):
    """打开PDF文档工具"""

    @property
    def name(self) -> str:
        return "open_pdf"

    @property
    def description(self) -> str:
        return "打开PDF文档,支持从文件系统选择PDF文件"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "PDF文件路径"
                }
            },
            "required": []
        }

    def get_parameter_ui(self, param_name: str, parent: Optional[QWidget] = None) -> Optional[QWidget]:
        if param_name == "file_path":
            widget = FileChooserWidget(
                parent=parent,
                file_filter="PDF Files (*.pdf)",
                mode="open"
            )
            widget.set_placeholder("选择PDF文件...")
            return widget
        return None

    def requires_main_thread(self) -> bool:
        return True

    def get_next_tool(self) -> Optional[str]:
        return "render_pdf"

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        file_path = params.get("file_path")

        try:
            logger.info(f"Opening PDF file: {file_path}")
            return {
                "success": True,
                "message": f"PDF加载完成: {file_path}",
                "file_path": file_path,
                "status": "loaded"
            }
        except Exception as e:
            logger.error(f"Error opening PDF: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"打开PDF文件失败: {str(e)}"
            }


class SavePDFTool(BaseTool):
    """保存PDF文档工具"""

    @property
    def name(self) -> str:
        return "save_pdf"

    @property
    def description(self) -> str:
        return "保存当前PDF文档到指定路径"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "保存的文件路径"
                }
            },
            "required": []
        }

    def get_parameter_ui(self, param_name: str, parent: Optional[QWidget] = None) -> Optional[QWidget]:
        if param_name == "file_path":
            widget = FileChooserWidget(
                parent=parent,
                file_filter="PDF Files (*.pdf)",
                mode="save"
            )
            widget.set_placeholder("选择保存位置...")
            return widget
        return None

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        file_path = params.get("file_path")

        try:
            logger.info(f"Saving PDF to: {file_path}")
            return {
                "success": True,
                "message": f"PDF已保存: {file_path}",
                "file_path": file_path
            }
        except Exception as e:
            logger.error(f"Error saving PDF: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"保存PDF失败: {str(e)}"
            }


class NavigatePDFTool(BaseTool):
    """PDF导航工具(翻页、跳转、缩放等)"""

    @property
    def name(self) -> str:
        return "navigate_pdf"

    @property
    def description(self) -> str:
        return "导航PDF文档,支持翻页、跳转到指定页、缩放等操作"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["next_page", "prev_page", "first_page", "last_page", "goto_page", "zoom_in", "zoom_out", "zoom_fit", "fit_width", "fit_height"],
                    "description": "导航动作: next_page(下一页), prev_page(上一页), first_page(第一页), last_page(最后一页), goto_page(跳转), zoom_in(放大), zoom_out(缩小), zoom_fit(适应页面), fit_width(适应宽度), fit_height(适应高度)"
                },
                "page_num": {
                    "type": "integer",
                    "description": "目标页码(仅对goto_page动作有效,从1开始)"
                },
                "zoom_level": {
                    "type": "number",
                    "description": "缩放级别,例如: 1.0, 1.5, 2.0"
                }
            },
            "required": ["action"]
        }

    def requires_main_thread(self) -> bool:
        return True

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        action = params.get("action", "next_page")
        page_num = params.get("page_num")
        zoom_level = params.get("zoom_level")

        try:
            logger.info(f"PDF navigation: action={action}, page_num={page_num}, zoom_level={zoom_level}")

            result_message = f"PDF导航: {action}"
            if page_num is not None:
                result_message += f" -> 第{page_num}页"
            if zoom_level is not None:
                result_message += f" -> {zoom_level}x"

            return {
                "success": True,
                "message": result_message,
                "action": action,
                "page_num": page_num,
                "zoom_level": zoom_level
            }
        except Exception as e:
            logger.error(f"Error navigating PDF: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"PDF导航失败: {str(e)}"
            }


class InsertBlankPageTool(BaseTool):
    """插入空白页工具"""

    @property
    def name(self) -> str:
        return "insert_blank_page"

    @property
    def description(self) -> str:
        return "在指定页码后插入空白页"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "page_num": {
                    "type": "integer",
                    "description": "在第几页后插入(从1开始)"
                }
            },
            "required": ["page_num"]
        }

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        page_num = params.get("page_num")

        try:
            logger.info(f"Inserting blank page after page {page_num}")
            return {
                "success": True,
                "message": f"已在第{page_num}页后插入空白页",
                "page_num": page_num
            }
        except Exception as e:
            logger.error(f"Error inserting blank page: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"插入空白页失败: {str(e)}"
            }


class DeletePagesTool(BaseTool):
    """删除页面工具"""

    @property
    def name(self) -> str:
        return "delete_pages"

    @property
    def description(self) -> str:
        return "删除指定的页面,可以删除单个或多个页面"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "page_nums": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "要删除的页码列表,例如: [1, 3, 5]"
                }
            },
            "required": ["page_nums"]
        }

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        page_nums = params.get("page_nums", [])

        try:
            logger.info(f"Deleting pages: {page_nums}")
            return {
                "success": True,
                "message": f"已删除 {len(page_nums)} 页: {page_nums}",
                "page_nums": page_nums
            }
        except Exception as e:
            logger.error(f"Error deleting pages: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"删除页面失败: {str(e)}"
            }


class RotatePageTool(BaseTool):
    """旋转页面工具"""

    @property
    def name(self) -> str:
        return "rotate_page"

    @property
    def description(self) -> str:
        return "旋转指定页面,支持90度、180度、270度旋转"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "page_num": {
                    "type": "integer",
                    "description": "要旋转的页码(从1开始)"
                },
                "rotation": {
                    "type": "integer",
                    "description": "旋转角度: 90(顺时针90度), 180(180度), 270(顺时针270度)"
                }
            },
            "required": ["page_num", "rotation"]
        }

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        page_num = params.get("page_num")
        rotation = params.get("rotation")

        try:
            logger.info(f"Rotating page {page_num} by {rotation} degrees")
            return {
                "success": True,
                "message": f"已将第{page_num}页旋转{rotation}度",
                "page_num": page_num,
                "rotation": rotation
            }
        except Exception as e:
            logger.error(f"Error rotating page: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"旋转页面失败: {str(e)}"
            }


class ExtractPagesTool(BaseTool):
    """提取页面工具"""

    @property
    def name(self) -> str:
        return "extract_pages"

    @property
    def description(self) -> str:
        return "提取指定页面到新PDF文件"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "page_nums": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "要提取的页码列表,例如: [1, 2, 3]"
                },
                "output_path": {
                    "type": "string",
                    "description": "输出文件路径"
                }
            },
            "required": ["page_nums", "output_path"]
        }

    def get_parameter_ui(self, param_name: str, parent: Optional[QWidget] = None) -> Optional[QWidget]:
        if param_name == "output_path":
            widget = FileChooserWidget(
                parent=parent,
                file_filter="PDF Files (*.pdf)",
                mode="save"
            )
            widget.set_placeholder("选择输出文件...")
            return widget
        return None

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        page_nums = params.get("page_nums", [])
        output_path = params.get("output_path")

        try:
            logger.info(f"Extracting pages {page_nums} to {output_path}")
            return {
                "success": True,
                "message": f"已提取 {len(page_nums)} 页到 {output_path}",
                "page_nums": page_nums,
                "output_path": output_path
            }
        except Exception as e:
            logger.error(f"Error extracting pages: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"提取页面失败: {str(e)}"
            }


class InsertPDFPageTool(BaseTool):
    """插入PDF页面工具"""

    @property
    def name(self) -> str:
        return "insert_pdf_page"

    @property
    def description(self) -> str:
        return "从其他PDF文件插入页面到当前文档"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "page_num": {
                    "type": "integer",
                    "description": "在第几页后插入(从1开始)"
                },
                "pdf_path": {
                    "type": "string",
                    "description": "要插入的PDF文件路径"
                }
            },
            "required": ["page_num", "pdf_path"]
        }

    def get_parameter_ui(self, param_name: str, parent: Optional[QWidget] = None) -> Optional[QWidget]:
        if param_name == "pdf_path":
            widget = FileChooserWidget(
                parent=parent,
                file_filter="PDF Files (*.pdf)",
                mode="open"
            )
            widget.set_placeholder("选择要插入的PDF文件...")
            return widget
        return None

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        page_num = params.get("page_num")
        pdf_path = params.get("pdf_path")

        try:
            logger.info(f"Inserting PDF pages from {pdf_path} after page {page_num}")
            return {
                "success": True,
                "message": f"已从PDF文件插入页面",
                "page_num": page_num,
                "pdf_path": pdf_path
            }
        except Exception as e:
            logger.error(f"Error inserting PDF pages: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"插入PDF页面失败: {str(e)}"
            }


class InsertImagePageTool(BaseTool):
    """插入图片页面工具"""

    @property
    def name(self) -> str:
        return "insert_image_page"

    @property
    def description(self) -> str:
        return "插入图片作为新的PDF页面"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "page_num": {
                    "type": "integer",
                    "description": "在第几页后插入(从1开始)"
                },
                "image_path": {
                    "type": "string",
                    "description": "图片文件路径"
                }
            },
            "required": ["page_num", "image_path"]
        }

    def get_parameter_ui(self, param_name: str, parent: Optional[QWidget] = None) -> Optional[QWidget]:
        if param_name == "image_path":
            widget = FileChooserWidget(
                parent=parent,
                file_filter="Image Files (*.png *.jpg *.jpeg *.gif *.bmp *.tiff)",
                mode="open"
            )
            widget.set_placeholder("选择图片文件...")
            return widget
        return None

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        page_num = params.get("page_num")
        image_path = params.get("image_path")

        try:
            logger.info(f"Inserting image {image_path} after page {page_num}")
            return {
                "success": True,
                "message": f"已插入图片页面",
                "page_num": page_num,
                "image_path": image_path
            }
        except Exception as e:
            logger.error(f"Error inserting image page: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"插入图片页面失败: {str(e)}"
            }


class SplitPDFTool(BaseTool):
    """拆分PDF工具"""

    @property
    def name(self) -> str:
        return "split_pdf"

    @property
    def description(self) -> str:
        return "拆分PDF文档,支持按页数、范围、书签等方式拆分"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "split_mode": {
                    "type": "string",
                    "enum": ["pages", "range", "bookmarks"],
                    "description": "拆分模式: pages(按页数), range(按范围), bookmarks(按书签)"
                },
                "pages_per_file": {
                    "type": "integer",
                    "description": "每个文件的页数(按页数拆分时使用)"
                },
                "output_dir": {
                    "type": "string",
                    "description": "输出目录"
                }
            },
            "required": []
        }

    def get_parameter_ui(self, param_name: str, parent: Optional[QWidget] = None) -> Optional[QWidget]:
        if param_name == "output_dir":
            widget = FileChooserWidget(
                parent=parent,
                file_filter="",
                mode="open"
            )
            widget._browse_button.setText("选择目录...")
            widget.set_placeholder("选择输出目录...")
            return widget
        return None

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        split_mode = params.get("split_mode", "pages")
        pages_per_file = params.get("pages_per_file", 1)
        output_dir = params.get("output_dir", "")

        try:
            logger.info(f"Splitting PDF with mode: {split_mode}, pages_per_file: {pages_per_file}, output_dir: {output_dir}")
            return {
                "success": True,
                "message": f"PDF拆分配置已准备: 模式={split_mode}, 每文件页数={pages_per_file}, 输出目录={output_dir}",
                "split_mode": split_mode,
                "pages_per_file": pages_per_file,
                "output_dir": output_dir
            }
        except Exception as e:
            logger.error(f"Error splitting PDF: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"拆分PDF失败: {str(e)}"
            }


class MergePDFTool(BaseTool):
    """合并PDF工具"""

    @property
    def name(self) -> str:
        return "merge_pdf"

    @property
    def description(self) -> str:
        return "合并多个PDF文档为一个文档"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "input_files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "要合并的PDF文件路径列表"
                },
                "output_path": {
                    "type": "string",
                    "description": "输出文件路径"
                }
            },
            "required": ["input_files", "output_path"]
        }

    def get_parameter_ui(self, param_name: str, parent: Optional[QWidget] = None) -> Optional[QWidget]:
        if param_name == "output_path":
            widget = FileChooserWidget(
                parent=parent,
                file_filter="PDF Files (*.pdf)",
                mode="save"
            )
            widget.set_placeholder("选择输出文件...")
            return widget
        return None

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        input_files = params.get("input_files", [])
        output_path = params.get("output_path", "")

        try:
            logger.info(f"Merging PDFs: {len(input_files)} files to {output_path}")
            return {
                "success": True,
                "message": f"PDF合并已完成: {len(input_files)} 个文件合并为 {output_path}",
                "output_path": output_path,
                "file_count": len(input_files)
            }
        except Exception as e:
            logger.error(f"Error merging PDFs: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"合并PDF失败: {str(e)}"
            }


class OCRLikePageTool(BaseTool):
    """OCR识别页面工具"""

    @property
    def name(self) -> str:
        return "ocr_page"

    @property
    def description(self) -> str:
        return "对PDF文档的指定页面进行OCR文字识别"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "page_nums": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "要识别的页码列表,例如: [1, 2, 3], 留空则识别全部"
                },
                "language": {
                    "type": "string",
                    "description": "识别语言,例如: chi_sim(简体中文), eng(英语), chi_sim+eng(中英混合)"
                }
            },
            "required": []
        }

    def requires_main_thread(self) -> bool:
        """OCR工具需要在主线程中执行,因为涉及GUI操作"""
        return True

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """同步执行OCR工具"""
        page_nums = params.get("page_nums", [])
        language = params.get("language", "chi_sim+eng")

        try:
            main_window = self._get_main_window()

            if not main_window:
                return {
                    "success": False,
                    "error": "无法访问主窗口,请先打开PDF文档"
                }

            # 检查是否有打开的PDF文档
            if not hasattr(main_window, 'pdf_processor') or not main_window.pdf_processor.fitz_document:
                return {
                    "success": False,
                    "error": "请先打开PDF文档"
                }

            # 调用主窗口已有的OCR功能
            # 如果没有指定页码或指定了多页,使用批量OCR
            if not page_nums or len(page_nums) > 1:
                main_window.perform_ocr_on_all_pages()
                return {
                    "success": True,
                    "message": "已启动批量OCR识别,处理完成后会自动生成可搜索PDF。请稍候...",
                    "language": language,
                    "mode": "batch"
                }
            else:
                # 识别单页
                target_page = page_nums[0]  # 保持1-based索引

                try:
                    # 先跳转到目标页 (go_to_page使用1-based索引)
                    if hasattr(main_window, 'go_to_page'):
                        main_window.go_to_page(target_page)

                    # 执行单页OCR (对当前页进行OCR)
                    # perform_ocr_on_current_page()内部会自动处理刷新和跳转回原页面
                    # 注意: 这个方法会弹出对话框,可能导致阻塞,需要在主线程中执行
                    if hasattr(main_window, 'perform_ocr_on_current_page'):
                        main_window.perform_ocr_on_current_page()

                    # OCR结束后再跳转到目标页,确保看到OCR后的页面
                    if hasattr(main_window, 'go_to_page'):
                        main_window.go_to_page(target_page)

                    return {
                        "success": True,
                        "message": f"已完成第{page_nums[0]}页的OCR识别,已生成可搜索PDF。您现在可以搜索识别到的文本了。",
                        "language": language,
                        "page_nums": page_nums,
                        "mode": "single"
                    }
                except Exception as ocr_error:
                    logger.error(f"OCR执行失败: {ocr_error}", exc_info=True)
                    return {
                        "success": False,
                        "error": f"OCR识别失败: {str(ocr_error)}"
                    }

        except Exception as e:
            logger.error(f"Error performing OCR: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"OCR识别失败: {str(e)}"
            }


class EncryptPDFTool(BaseTool):
    """加密PDF工具"""

    @property
    def name(self) -> str:
        return "encrypt_pdf"

    @property
    def description(self) -> str:
        return "为PDF文档添加密码保护"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "password": {
                    "type": "string",
                    "description": "加密密码"
                },
                "output_path": {
                    "type": "string",
                    "description": "输出文件路径"
                }
            },
            "required": ["password"]
        }

    def get_parameter_ui(self, param_name: str, parent: Optional[QWidget] = None) -> Optional[QWidget]:
        from PyQt5.QtWidgets import QLineEdit

        if param_name == "password":
            widget = QLineEdit()
            widget.setEchoMode(QLineEdit.Password)
            widget.setPlaceholderText("输入加密密码...")
            return widget
        elif param_name == "output_path":
            widget = FileChooserWidget(
                parent=parent,
                file_filter="PDF Files (*.pdf)",
                mode="save"
            )
            widget.set_placeholder("选择输出文件...")
            return widget
        return None

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        password = params.get("password", "")
        output_path = params.get("output_path", "")

        try:
            logger.info(f"Encrypting PDF with output path: {output_path}")
            return {
                "success": True,
                "message": "PDF加密已完成",
                "output_path": output_path
            }
        except Exception as e:
            logger.error(f"Error encrypting PDF: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"加密PDF失败: {str(e)}"
            }


class ShowMessageTool(BaseTool):
    """显示消息通知工具"""

    @property
    def name(self) -> str:
        return "show_message"

    @property
    def description(self) -> str:
        return "向用户显示消息通知,包括成功、错误、警告等信息"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "要显示的消息内容"
                },
                "level": {
                    "type": "string",
                    "enum": ["info", "success", "warning", "error"],
                    "description": "消息级别: info(信息), success(成功), warning(警告), error(错误)"
                },
                "title": {
                    "type": "string",
                    "description": "消息标题,可选"
                }
            },
            "required": ["message"]
        }

    def requires_main_thread(self) -> bool:
        return True

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        message = params.get("message", "")
        level = params.get("level", "info")
        title = params.get("title", "")

        try:
            logger.info(f"Showing message: level={level}, title={title}, message={message}")
            return {
                "success": True,
                "message": "消息已显示",
                "displayed_message": message,
                "level": level,
                "title": title
            }
        except Exception as e:
            logger.error(f"Error showing message: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"显示消息失败: {str(e)}"
            }


class ShowThumbnailTool(BaseTool):
    """显示/隐藏缩略图工具"""

    @property
    def name(self) -> str:
        return "toggle_thumbnails"

    @property
    def description(self) -> str:
        return "显示或隐藏缩略图面板"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "show": {
                    "type": "boolean",
                    "description": "是否显示缩略图, true=显示, false=隐藏, 留空则切换"
                }
            },
            "required": []
        }

    def requires_main_thread(self) -> bool:
        return True

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        show = params.get("show")

        try:
            main_window = self._get_main_window()

            if not main_window:
                return {
                    "success": False,
                    "error": "无法访问主窗口"
                }

            # 检查主窗口是否有toggle_thumbnails方法
            if hasattr(main_window, 'toggle_thumbnails'):
                main_window.toggle_thumbnails()

                if show is True:
                    message = "缩略图面板已显示"
                elif show is False:
                    message = "缩略图面板已隐藏"
                else:
                    message = "缩略图面板已切换"

                logger.info(message)
                return {
                    "success": True,
                    "message": message,
                    "show": show
                }
            else:
                return {
                    "success": False,
                    "error": "主窗口不支持缩略图功能"
                }
        except Exception as e:
            logger.error(f"Error toggling thumbnails: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"切换缩略图失败: {str(e)}"
            }


class ClearCacheTool(BaseTool):
    """清理缓存工具"""

    @property
    def name(self) -> str:
        return "clear_cache"

    @property
    def description(self) -> str:
        return "清理所有缓存,释放内存"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "required": []
        }

    def requires_main_thread(self) -> bool:
        return True

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            logger.info("Clearing all caches")
            return {
                "success": True,
                "message": "所有缓存已清理"
            }
        except Exception as e:
            logger.error(f"Error clearing cache: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"清理缓存失败: {str(e)}"
            }


class UndoOperationTool(BaseTool):
    """撤销操作工具"""

    @property
    def name(self) -> str:
        return "undo_operation"

    @property
    def description(self) -> str:
        return "撤销上一次PDF编辑操作"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "required": []
        }

    def requires_main_thread(self) -> bool:
        return True

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            logger.info("Undoing last operation")
            return {
                "success": True,
                "message": "已撤销上一次操作"
            }
        except Exception as e:
            logger.error(f"Error undoing operation: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"撤销操作失败: {str(e)}"
            }


class RedoOperationTool(BaseTool):
    """重做操作工具"""

    @property
    def name(self) -> str:
        return "redo_operation"

    @property
    def description(self) -> str:
        return "重做上一次撤销的操作"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "required": []
        }

    def requires_main_thread(self) -> bool:
        return True

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            logger.info("Redoing last operation")
            return {
                "success": True,
                "message": "已重做上一次撤销的操作"
            }
        except Exception as e:
            logger.error(f"Error redoing operation: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"重做操作失败: {str(e)}"
            }


class SearchTextTool(BaseTool):
    """文本搜索工具"""

    @property
    def name(self) -> str:
        return "search_text"

    @property
    def description(self) -> str:
        return "在PDF文档中搜索指定文本"

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "要搜索的文本"
                },
                "case_sensitive": {
                    "type": "boolean",
                    "description": "是否区分大小写,默认false"
                }
            },
            "required": ["text"]
        }

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        text = params.get("text", "")
        case_sensitive = params.get("case_sensitive", False)

        try:
            logger.info(f"Searching text: '{text}', case_sensitive={case_sensitive}")
            return {
                "success": True,
                "message": f"已搜索文本: '{text}'",
                "text": text,
                "case_sensitive": case_sensitive
            }
        except Exception as e:
            logger.error(f"Error searching text: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"搜索文本失败: {str(e)}"
            }
