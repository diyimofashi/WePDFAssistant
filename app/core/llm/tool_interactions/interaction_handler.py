"""
工具交互处理器
处理工具调用时的用户交互逻辑
"""
from typing import Dict, Any, Tuple, List, Optional
from PyQt5.QtWidgets import QWidget, QMessageBox, QDialog
from PyQt5.QtCore import QObject, pyqtSignal
from app.core.llm.tools.base_tool import BaseTool
from app.core.llm.tools.tool_registry import ToolRegistry
from app.core.llm.tool_interactions.file_chooser import FileChooserWidget
from app.core.llm.tool_interactions.config_dialog import ParameterConfigDialog
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ToolInteractionHandler(QObject):
    """工具交互处理器"""

    tool_execution_completed = pyqtSignal(str, dict)  # 工具执行完成信号 (tool_name, result)
    action_required = pyqtSignal(str, dict)  # 需要用户操作信号 (action_type, params)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._tool_registry = ToolRegistry()
        self._parent_widget = parent
        logger.info("ToolInteractionHandler initialized")

    def set_parent_widget(self, parent: QWidget) -> None:
        """设置父窗口"""
        self._parent_widget = parent

    async def handle_tool_call(
        self,
        tool_name: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        处理工具调用

        Args:
            tool_name: 工具名称
            params: 参数字典

        Returns:
            执行结果
        """
        # 1. 获取工具
        tool = self._tool_registry.get_tool(tool_name)
        if not tool:
            error_msg = f"工具 '{tool_name}' 不存在"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "tool_name": tool_name
            }

        try:
            # 2. 检查工具是否启用
            if not tool.is_enabled():
                error_msg = f"工具 '{tool_name}' 未启用"
                logger.warning(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "tool_name": tool_name
                }

            # 3. 检查参数完整性
            complete, missing_params = tool.check_parameters_complete(params)

            if not complete:
                logger.info(f"Tool '{tool_name}' missing parameters: {missing_params}")
                # 参数缺失，收集参数
                for param_name in missing_params:
                    param_value = await self._collect_parameter(tool, param_name, params)
                    if param_value is None:
                        # 用户取消操作
                        return {
                            "success": False,
                            "error": f"用户取消了操作: {tool.name}",
                            "tool_name": tool_name
                        }
                    params[param_name] = param_value

            # 4. 验证参数
            valid, error_msg = tool.validate_parameters(params)
            if not valid:
                logger.error(f"Parameter validation failed: {error_msg}")
                return {
                    "success": False,
                    "error": f"参数验证失败: {error_msg}",
                    "tool_name": tool_name
                }

            # 5. 执行工具
            logger.info(f"Executing tool: {tool_name} with params: {params}")
            result = await tool.execute(params)

            logger.info(f"Tool execution result: {result.get('success')}")

            # 6. 发送完成信号
            self.tool_execution_completed.emit(tool_name, result)

            return result

        except Exception as e:
            logger.error(f"Error executing tool '{tool_name}': {e}", exc_info=True)
            return {
                "success": False,
                "error": f"执行工具时出错: {str(e)}",
                "tool_name": tool_name
            }

    async def _collect_parameter(
        self,
        tool: BaseTool,
        param_name: str,
        current_params: Dict[str, Any]
    ) -> Optional[Any]:
        """
        收集参数值

        Args:
            tool: 工具实例
            param_name: 参数名称
            current_params: 当前已收集的参数

        Returns:
            参数值或None(用户取消)
        """
        # 特殊处理：如果参数是file_path类型，使用文件选择工具
        if param_name == 'file_path':
            return await self._show_file_chooser_dialog(tool, param_name, current_params)
        
        # 获取参数UI组件
        ui_widget = tool.get_parameter_ui(param_name, self._parent_widget)

        if ui_widget:
            # 使用自定义UI组件
            return await self._show_custom_ui(ui_widget, param_name)
        else:
            # 使用通用对话框
            return await self._show_generic_dialog(tool, param_name, current_params)

    async def _show_custom_ui(self, ui_widget: QWidget, param_name: str) -> Optional[Any]:
        """
        显示自定义UI组件

        Args:
            ui_widget: UI组件
            param_name: 参数名称

        Returns:
            参数值或None
        """
        dialog = ParameterConfigDialog(ui_widget, param_name, self._parent_widget)
        result = dialog.exec_()

        if result == QDialog.Accepted:
            return dialog.get_value()
        return None

    async def _show_file_chooser_dialog(
        self,
        tool: BaseTool,
        param_name: str,
        current_params: Dict[str, Any]
    ) -> Optional[Any]:
        """
        显示文件选择对话框

        Args:
            tool: 工具实例
            param_name: 参数名称
            current_params: 当前已收集的参数

        Returns:
            参数值或None
        """
        # 获取工具参数模式
        schema = tool.get_parameters_schema()
        param_schema = schema.get("properties", {}).get(param_name, {})
        
        description = param_schema.get("description", f"请选择 {param_name}")
        
        # 获取已注册的文件选择工具
        file_chooser_tool = self._tool_registry.get_tool('file_chooser')
        if not file_chooser_tool:
            # 如果工具不存在，创建一个新实例
            from app.core.llm.tools.file_chooser_tool import FileChooserTool
            file_chooser_tool = FileChooserTool(self._parent_widget)
        else:
            # 确保父窗口设置正确
            if hasattr(file_chooser_tool, 'set_parent_widget'):
                file_chooser_tool.set_parent_widget(self._parent_widget)
        
        # 准备文件选择参数
        file_filter = "All Files (*)"
        if 'pdf' in tool.get_name().lower():
            file_filter = "PDF Files (*.pdf)"
        elif 'image' in tool.get_name().lower():
            file_filter = "Image Files (*.png *.jpg *.jpeg *.gif *.bmp)"
        
        file_chooser_params = {
            "purpose": description,
            "file_filter": file_filter
        }
        
        # 执行文件选择工具
        result = await file_chooser_tool.execute(file_chooser_params)
        
        if result.get('success'):
            return result.get('file_path')
        else:
            return None

    async def _show_generic_dialog(
        self,
        tool: BaseTool,
        param_name: str,
        current_params: Dict[str, Any]
    ) -> Optional[Any]:
        """
        显示通用对话框

        Args:
            tool: 工具实例
            param_name: 参数名称
            current_params: 当前已收集的参数

        Returns:
            参数值或None
        """
        # 显示提示信息
        schema = tool.get_parameters_schema()
        param_schema = schema.get("properties", {}).get(param_name, {})

        description = param_schema.get("description", f"请输入 {param_name}")
        param_type = param_schema.get("type", "string")

        dialog = ParameterConfigDialog(
            None,
            param_name,
            self._parent_widget,
            description=description,
            param_type=param_type
        )
        result = dialog.exec_()

        if result == QDialog.Accepted:
            return dialog.get_value()
        return None

    def confirm_tool_execution(
        self,
        tool_name: str,
        params: Dict[str, Any]
    ) -> bool:
        """
        确认工具执行

        Args:
            tool_name: 工具名称
            params: 参数字典

        Returns:
            是否确认执行
        """
        tool = self._tool_registry.get_tool(tool_name)
        if not tool:
            return False

        # 格式化参数信息
        params_text = "\n".join([f"  {k}: {v}" for k, v in params.items()])

        message = f"即将执行工具: {tool_name}\n\n参数:\n{params_text}\n\n确定要执行吗？"

        reply = QMessageBox.question(
            self._parent_widget,
            "确认执行",
            message,
            QMessageBox.Yes | QMessageBox.No
        )

        return reply == QMessageBox.Yes
