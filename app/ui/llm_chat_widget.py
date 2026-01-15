"""
新的LLM聊天窗口组件 - 重构版本
提供美观的聊天界面和自然语言交互功能
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFrame, QComboBox,
    QPushButton, QLabel, QSizePolicy, QProgressDialog, QMenu, QAction
)
from PyQt5.QtCore import Qt, QMutex, QWaitCondition, pyqtSignal, QObject
from typing import List, Dict, Optional, Any
import json
import asyncio

from app.core.llm.llm_plugin_interface import LLMMessage
from app.core.llm.llm_integration import LLMIntegration
from app.config.llm_plugin_config import LLMPluginConfigManager
from app.managers.llm_tool_manager import LLMToolManager
from app.core.llm.tool_interactions.interaction_handler import ToolInteractionHandler
from app.core.llm.session_manager import SessionManager, ChatSession
from app.utils.logger import get_logger

# 导入组件
from app.ui.chat_components.message_bubble import MessageBubble
from app.ui.chat_components.action_bubble import ActionBubble
from app.ui.chat_components.input_component import InputTextEdit
from app.ui.chat_components.chat_thread import LLMChatThread

logger = get_logger(__name__)


class NewLLMChatWidget(QWidget):
    """新的LLM聊天窗口组件 - 重构版本"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._llm_integration: LLMIntegration | None = None
        self._config_manager: LLMPluginConfigManager | None = None
        self._tool_manager: LLMToolManager | None = None
        self._interaction_handler: ToolInteractionHandler | None = None
        self._messages: List[LLMMessage] = []
        self._current_plugin: str | None = None
        self._chat_thread: LLMChatThread | None = None
        self._is_generating = False
        self._pending_actions: Dict[str, ActionBubble] = {}

        # 待处理的工具列表（用于需要用户交互的工具）
        self._pending_tool_calls: List[Dict[str, Any]] = []

        # 会话管理
        self._session_manager: SessionManager | None = None
        self._current_session: ChatSession | None = None

        # 进度对话框相关
        self._progress_dialog = None
        self._tool_start_time = None

        self._init_ui()
        self._get_llm_integration()
        self._load_tools()
        self._load_plugins()
        self._init_session_manager()

    def _get_llm_integration(self):
        """获取主窗口的LLM集成实例"""
        parent_window = self.parent()
        while parent_window:
            if hasattr(parent_window, '_llm_integration'):
                self._llm_integration = parent_window._llm_integration
                break
            parent_window = parent_window.parent()

        if not self._llm_integration:
            self._llm_integration = LLMIntegration()
            logger.warning("Creating new LLM integration instance")

        # 创建配置管理器
        self._config_manager = LLMPluginConfigManager()

    def _load_tools(self):
        """加载工具系统"""
        # 尝试从主窗口获取工具管理器
        parent_window = self.parent()
        while parent_window:
            if hasattr(parent_window, '_llm_tool_manager'):
                self._tool_manager = parent_window._llm_tool_manager
                break
            parent_window = parent_window.parent()

        if not self._tool_manager:
            self._tool_manager = LLMToolManager()
            logger.warning("Creating new LLM tool manager instance")

        # 初始化工具交互处理器，使用self作为父对象（NewLLMChatWidget继承自QWidget）
        self._interaction_handler = ToolInteractionHandler(self)
        self._interaction_handler.tool_execution_completed.connect(self._on_tool_execution_completed)
        self._interaction_handler.action_required.connect(self._on_action_required)

        # 将交互处理器设置到工具管理器
        self._tool_manager.set_interaction_handler(self._interaction_handler)

    def _on_tool_execution_completed(self, tool_name: str, result: dict):
        """工具执行完成回调"""
        logger.info(f"Tool execution completed: {tool_name}, success: {result.get('success')}")

    def _on_action_required(self, action_type: str, params: Dict[str, Any]):
        """工具需要用户操作"""
        bubble = self._add_action_bubble(action_type, params)
        self._pending_actions[action_type] = bubble

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 顶部工具栏
        toolbar = QWidget()
        toolbar.setObjectName("llmToolbar")
        toolbar.setStyleSheet("""
            #llmToolbar {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
                border-bottom: 1px solid #5e35b1;
            }
            QLabel {
                color: white;
                font-weight: bold;
                font-size: 14px;
            }
            QComboBox {
                background: white;
                border: 1px solid #b39ddb;
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 150px;
            }
        """)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(10, 8, 10, 8)
        toolbar_layout.setSpacing(10)

        # 标题
        title_label = QLabel("🤖 AI助手")
        title_label.setStyleSheet("color: white; font-weight: bold; font-size: 16px;")
        toolbar_layout.addWidget(title_label)

        toolbar_layout.addStretch()

        # 新建会话按钮
        new_chat_button = QPushButton("+")
        new_chat_button.setMaximumWidth(40)
        new_chat_button.setMinimumHeight(32)
        new_chat_button.setToolTip("新建会话")
        new_chat_button.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255, 0.2);
                border: 1px solid rgba(255,255,255, 0.3);
                border-radius: 4px;
                color: white;
                font-weight: bold;
                font-size: 18px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.3);
            }
        """)
        new_chat_button.clicked.connect(self._create_new_session)
        toolbar_layout.addWidget(new_chat_button)

        # 会话选择器
        self._session_combo = QComboBox()
        self._session_combo.setMinimumWidth(200)
        self._session_combo.setMinimumHeight(32)
        self._session_combo.setStyleSheet("""
            QComboBox {
                background: white;
                border: 1px solid #b39ddb;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 13px;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 20px;
            }
            QComboBox::down-arrow {
                image: none;
            }
        """)
        self._session_combo.currentIndexChanged.connect(self._on_session_changed)
        toolbar_layout.addWidget(self._session_combo)

        # 删除会话按钮
        delete_session_button = QPushButton("🗑️ 删除")
        delete_session_button.setMinimumHeight(32)
        delete_session_button.setToolTip("删除当前会话")
        delete_session_button.setStyleSheet("""
            QPushButton {
                background: #ffcdd2;
                color: #c62828;
                border: 1px solid #ef9a9a;
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #ef9a9a;
            }
            QPushButton:disabled {
                background: #e0e0e0;
                color: #9e9e9e;
                border: 1px solid #bdbdbd;
            }
        """)
        delete_session_button.clicked.connect(self._delete_current_session)
        toolbar_layout.addWidget(delete_session_button)

        # 关闭按钮
        close_button = QPushButton("✕")
        close_button.setMaximumWidth(40)
        close_button.setMinimumHeight(32)
        close_button.setToolTip("关闭对话")
        close_button.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255, 0.2);
                border: 1px solid rgba(255,255,255, 0.3);
                border-radius: 4px;
                color: white;
                font-weight: bold;
                font-size: 18px;
            }
            QPushButton:hover {
                background: rgba(255, 100, 100, 0.3);
            }
        """)
        close_button.clicked.connect(self._close_sidebar)
        toolbar_layout.addWidget(close_button)

        layout.addWidget(toolbar)

        # 消息显示区域
        message_area = QScrollArea()
        message_area.setWidgetResizable(True)
        message_area.setStyleSheet("""
            QScrollArea {
                background: #fafafa;
                border: none;
            }
            QScrollBar:vertical {
                background: #e0e0e0;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #b0bec5;
                border-radius: 6px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: #90a4ae;
            }
        """)

        self._message_container = QWidget()
        self._message_container.setStyleSheet("background: #fafafa;")
        self._message_layout = QVBoxLayout(self._message_container)
        self._message_layout.setAlignment(Qt.AlignTop)
        self._message_layout.setSpacing(12)
        self._message_layout.setContentsMargins(10, 10, 10, 10)
        message_area.setWidget(self._message_container)
        layout.addWidget(message_area)
        layout.setStretchFactor(message_area, 1)  # 设置消息区域拉伸因子为1，占据可用空间

        # 输入区域 - 现在位于底部
        input_container = QWidget()
        input_container.setStyleSheet("""
            QWidget {
                background: white;
                border-top: 1px solid #e0e0e0;
            }
        """)
        input_layout = QVBoxLayout(input_container)
        input_layout.setContentsMargins(10, 2, 10, 2)
        input_layout.setSpacing(1)

        # 输入框
        self._input_edit = InputTextEdit()
        self._input_edit.setMaximumHeight(80)
        self._input_edit.setPlaceholderText("💬 输入您的问题... (Enter发送)")
        self._input_edit.setStyleSheet("""
            QTextEdit {
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                padding: 4px;
                background: #fafafa;
                font-size: 14px;
            }
            QTextEdit:focus {
                border: 2px solid #667eea;
                background: white;
            }
        """)
        self._input_edit.send_signal.connect(self._send_message)
        input_layout.addWidget(self._input_edit)

        # 插件选择和发送按钮行 - 紧贴输入框下方
        plugin_send_layout = QHBoxLayout()
        
        # 插件选择 - 在左侧
        self._plugin_combo = QComboBox()
        self._plugin_combo.setMinimumWidth(150)
        self._plugin_combo.setMinimumHeight(30)
        plugin_send_layout.addWidget(self._plugin_combo)
        
        plugin_send_layout.addStretch()  # 添加弹性空间，使按钮靠右
        
        # 发送按钮 - 在右侧
        self._send_button = QPushButton("🚀 发送")
        self._send_button.setMinimumHeight(30)
        self._send_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
                color: white;
                border: none;
                border-radius: 15px;
                padding: 5px 15px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #7986cb, stop:1 #8e6ab5);
            }
            QPushButton:pressed {
                background: #5e35b1;
            }
            QPushButton:disabled {
                background: #b0bec5;
                color: #78909c;
            }
        """)
        self._send_button.clicked.connect(self._send_message)
        self._send_button.setEnabled(False)
        plugin_send_layout.addWidget(self._send_button)
        
        input_layout.addLayout(plugin_send_layout)

        layout.addWidget(input_container)

    def _load_plugins(self):
        """加载插件列表"""
        if self._llm_integration is None or self._config_manager is None:
            logger.error("LLM integration or config manager not available")
            return

        # 获取所有可用插件
        all_plugins = self._llm_integration.get_available_plugins()

        # 只添加已启用的插件
        enabled_plugins = []
        for plugin_name in all_plugins:
            if self._config_manager.is_plugin_enabled(plugin_name):
                enabled_plugins.append(plugin_name)

        self._plugin_combo.clear()
        self._plugin_combo.addItems(enabled_plugins)

        # 优先使用上次选择的插件
        last_selected = self._config_manager.get_last_selected_plugin()
        if last_selected and last_selected in enabled_plugins:
            self._current_plugin = last_selected
            index = self._plugin_combo.findText(last_selected)
            if index >= 0:
                self._plugin_combo.setCurrentIndex(index)
        elif enabled_plugins:
            self._current_plugin = enabled_plugins[0]
            self._plugin_combo.setCurrentIndex(0)

        # 连接信号
        self._input_edit.textChanged.connect(self._on_input_changed)
        self._plugin_combo.currentTextChanged.connect(self._on_plugin_changed)

    def _init_session_manager(self):
        """初始化会话管理器"""
        self._session_manager = SessionManager()

        # 获取当前会话
        current_session = self._session_manager.get_current_session()

        # 如果没有会话,创建一个新会话
        if not current_session:
            current_session = self._session_manager.create_session("新对话", self._current_plugin)

        self._current_session = current_session

        # 加载会话历史
        self._load_session_history(current_session)

        # 刷新会话列表
        self._refresh_session_list()

        logger.info(f"Initialized session manager, current session: {current_session.session_id}")

    def _load_session_history(self, session: ChatSession):
        """加载会话历史到界面"""
        # 清空当前消息
        while self._message_layout.count():
            child = self._message_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self._messages = []

        # 加载历史消息
        for msg_data in session.messages:
            msg = LLMMessage(
                role=msg_data["role"],
                content=msg_data["content"],
                timestamp=msg_data.get("timestamp", "")
            )
            self._messages.append(msg)
            self._add_message_bubble(msg.role, msg.content)

        logger.info(f"Loaded {len(session.messages)} messages from session")

    def _refresh_session_list(self):
        """刷新会话列表"""
        sessions = self._session_manager.get_all_sessions()

        # 保存当前选择的会话
        current_session_id = self._current_session.session_id if self._current_session else None

        # 清空下拉框
        self._session_combo.clear()

        # 添加所有会话
        for session in sessions:
            # 显示格式: 标题 (时间)
            from datetime import datetime
            try:
                updated_time = datetime.fromisoformat(session.updated_at)
                time_str = updated_time.strftime("%m-%d %H:%M")
            except:
                time_str = session.updated_at[:16] if session.updated_at else ""

            display_text = f"{session.title} ({time_str})"
            self._session_combo.addItem(display_text, session.session_id)

        # 恢复当前选择的会话
        if current_session_id:
            index = self._session_combo.findData(current_session_id)
            if index >= 0:
                self._session_combo.setCurrentIndex(index)

    def _on_input_changed(self):
        """输入改变时更新发送按钮状态"""
        text = self._input_edit.toPlainText().strip()
        self._send_button.setEnabled(bool(text) and not self._is_generating)

    def _on_plugin_changed(self, plugin_name: str):
        """插件改变"""
        self._current_plugin = plugin_name if plugin_name else None

        # 保存选择的插件
        if self._current_plugin and self._config_manager:
            self._config_manager.set_last_selected_plugin(self._current_plugin)
            logger.debug(f"Saved selected plugin: {self._current_plugin}")

    def _add_message_bubble(self, role: str, content: str):
        """添加消息气泡"""
        bubble = MessageBubble(role, content)
        self._message_layout.addWidget(bubble)

        # 滚动到底部
        message_area = self._message_container.parent()
        if isinstance(message_area, QScrollArea):
            message_area.verticalScrollBar().setValue(
                message_area.verticalScrollBar().maximum()
            )

    def _add_action_bubble(self, action_type: str, params: Dict[str, Any]) -> ActionBubble:
        """添加用户操作气泡"""
        bubble = ActionBubble(action_type, params)
        bubble.action_completed.connect(self._on_action_completed)
        self._message_layout.addWidget(bubble)

        # 直接同步滚动到底部，不使用QTimer
        # QTimer.singleShot(0, self._scroll_to_bottom)
        self._scroll_to_bottom()

        return bubble

    def _scroll_to_bottom(self):
        """滚动到底部的辅助方法"""
        try:
            message_area = self._message_container.parent()
            if isinstance(message_area, QScrollArea):
                message_area.verticalScrollBar().setValue(
                    message_area.verticalScrollBar().maximum()
                )
            else:
                logger.warning("Step: message_area is not QScrollArea")
        except Exception as e:
            logger.error(f"Error scrolling to bottom: {e}", exc_info=True)

    def _on_action_completed(self, action_type: str, result: Dict[str, Any]):
        """操作完成回调"""

        # 对于文件选择操作,只在成功且有文件路径时才继续
        if action_type == "file_chooser":
            file_path = result.get('file_path', '')
            if not file_path:
                # 用户取消了文件选择,不继续执行
                logger.info("User cancelled file selection")
                return

            # 无论是否保存模式,都需要添加消息显示操作结果
            result_content = json.dumps(result, ensure_ascii=False)
            self._messages.append(LLMMessage(
                role="user",
                content=f"用户操作 {action_type} 完成: {result_content}"
            ))

            # 不显示用户操作结果消息，直接继续对话
            # 让LLM基于操作结果继续执行工具
            self._continue_after_action(action_type, result)
            return

        # 对于非必需参数的补充,不显示消息,直接继续
        # 只在真正执行工具失败或用户主动取消时才显示消息
        if result.get('success', True) and not result.get('error'):
            # 成功完成参数补充,不显示消息
            self._continue_after_action(action_type, result)
            return

        # 将操作结果添加到消息历史(只在错误时)
        result_content = json.dumps(result, ensure_ascii=False)
        self._messages.append(LLMMessage(
            role="user",
            content=f"用户操作 {action_type} 完成: {result_content}"
        ))

        # 不显示用户操作结果消息，直接继续对话
        # 继续对话，让LLM基于操作结果继续执行工具
        self._continue_after_action(action_type, result)

    def _continue_after_action(self, action_type: str, result: Dict[str, Any]):
        """
        用户操作完成后继续执行工具链

        Args:
            action_type: 操作类型
            result: 操作结果
        """
        import asyncio

        try:
            # 根据操作类型继续执行后续工具
            if action_type == "file_chooser" and result.get('file_path'):
                file_path = result['file_path']

                # 检查是否是保存模式（加密另存为）
                save_mode = result.get('save_mode', False)

                if save_mode:
                    # 如果是保存模式，记录保存路径，然后询问密码
                    self._pending_encrypt_output_path = file_path

                    # 添加密码输入气泡
                    self._add_action_bubble("password", {
                        "message": "请输入加密密码",
                        "placeholder": "请输入密码"
                    })
                    return

                # 将文件路径添加到第一个待处理工具的参数中
                if self._pending_tool_calls:
                    first_tool_call = self._pending_tool_calls[0]
                    # 更新参数
                    arguments_str = first_tool_call.get("arguments", "{}")
                    try:
                        arguments = json.loads(arguments_str)
                        arguments["file_path"] = file_path
                        first_tool_call["arguments"] = json.dumps(arguments, ensure_ascii=False)
                        logger.info(f"Updated tool parameters with file_path: {file_path}")
                    except Exception as e:
                        logger.error(f"Error updating tool parameters: {e}", exc_info=True)

                # 继续执行待处理的工具列表
                self._execute_pending_tool_calls()
                return

            elif action_type == "password" and result.get('value'):
                password = result['value']

                # 检查是否有待处理的加密操作
                if hasattr(self, '_pending_encrypt_output_path') and self._pending_encrypt_output_path:
                    output_path = self._pending_encrypt_output_path
                    delattr(self, '_pending_encrypt_output_path')

                    # 执行加密操作
                    loop = asyncio.get_event_loop()
                    try:
                        if loop.is_running():
                            encrypt_result = asyncio.run_coroutine_threadsafe(
                                self._encrypt_pdf_file({"password": password, "output_path": output_path}), loop
                            ).result(timeout=30)
                        else:
                            encrypt_result = loop.run_until_complete(
                                self._encrypt_pdf_file({"password": password, "output_path": output_path})
                            )
                    except RuntimeError:
                        encrypt_result = asyncio.run(
                            self._encrypt_pdf_file({"password": password, "output_path": output_path})
                        )

                    # 显示加密结果
                    encrypt_msg = f"\n✅ 加密PDF\n"
                    if encrypt_result.get('success'):
                        encrypt_msg += f"成功: {encrypt_result.get('message', '加密完成')}\n"
                    else:
                        encrypt_msg += f"失败: {encrypt_result.get('error', '未知错误')}\n"
                    self._add_message_bubble("assistant", encrypt_msg)

                    # 将加密结果添加到消息历史（作为用户消息，告诉 LLM 工具已完成）
                    self._messages.append(LLMMessage(
                        role="user",
                        content=f"工具 encrypt_pdf 执行结果: {json.dumps(encrypt_result, ensure_ascii=False)}"
                    ))
                    # 添加 assistant 消息表示工具已完成，避免 LLM 再次调用工具
                    self._messages.append(LLMMessage(
                        role="assistant",
                        content=f"PDF加密操作已完成。{encrypt_result.get('message', '') if encrypt_result.get('success') else '加密失败: ' + encrypt_result.get('error', '')}"
                    ))
                    # 继续对话，让 LLM 基于工具结果生成回复
                    self._start_generation()
                else:
                    # 如果没有待处理的加密操作，直接继续对话
                    self._messages.append(LLMMessage(
                        role="user",
                        content=f"用户输入密码: {password}"
                    ))
                    self._start_generation()

            else:
                # 其他操作类型，直接继续对话
                self._start_generation()

        except Exception as e:
            logger.error(f"Error continuing after action {action_type}: {e}", exc_info=True)
            error_msg = f"\n❌ 继续执行失败: {str(e)}\n"

            # 保存错误消息到会话
            error_message = LLMMessage(role="assistant", content=error_msg)
            self._save_current_message(error_message)

            self._add_message_bubble("assistant", error_msg)
            self._start_generation()

    def _execute_pending_tool_calls(self):
        """
        执行待处理的工具列表
        将用户补充参数后的工具继续执行完
        """
        if not self._pending_tool_calls:
            logger.warning("No pending tool calls to execute")
            self._start_generation()
            return

        tool_results = []

        # 执行所有待处理的工具
        for tool_call in self._pending_tool_calls:
            logger.debug(f"Executing pending tool_call: {tool_call}")

            # 获取工具名称和参数
            try:
                tool_name = tool_call.get("name")
                arguments_str = tool_call.get("arguments", "{}")
            except Exception as e:
                logger.error(f"Error getting tool attributes: {e}", exc_info=True)
                continue

            if not tool_name:
                logger.warning("Tool call has empty name, skipping")
                continue

            # 解析参数
            try:
                arguments = json.loads(arguments_str)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse arguments: {arguments_str}, error: {e}")
                arguments = {}

            # 检查参数是否完整，如果仍然不完整，则需要再次等待用户输入
            if self._tool_manager and self._tool_manager.get_tool_registry():
                tool = self._tool_manager.get_tool_registry().get_tool(tool_name)
                if tool:
                    complete, missing_params = tool.check_parameters_complete(arguments)
                    if not complete:
                        logger.info(f"Tool {tool_name} still missing parameters: {missing_params}")
                        # 需要继续等待用户输入，不要执行
                        return

            # 执行工具
            try:
                loop = asyncio.get_event_loop()
                try:
                    if loop.is_running():
                        result = asyncio.run_coroutine_threadsafe(
                            self._execute_tool(tool_name, arguments), loop
                        ).result(timeout=120)
                    else:
                        result = loop.run_until_complete(self._execute_tool(tool_name, arguments))
                except RuntimeError:
                    result = asyncio.run(self._execute_tool(tool_name, arguments))
            except Exception as e:
                logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
                result = {"success": False, "error": str(e)}

            # 收集结果
            tool_results.append({
                "name": tool_name,
                "result": result
            })

            # 执行完成后清理
            self._cleanup_after_tool_execution(tool_name)

        # 所有工具执行完成，将结果统一反馈给大模型
        self._send_tool_results_to_llm(tool_results)

        # 清空待处理的工具列表
        self._pending_tool_calls = []

    def _send_tool_results_to_llm(self, tool_results: List[Dict[str, Any]]):
        """
        将工具执行结果发送给大模型

        Args:
            tool_results: 工具执行结果列表
        """
        # 将所有工具执行结果添加到消息历史
        for tool_result in tool_results:
            tool_name = tool_result["name"]
            result = tool_result["result"]

            result_content = json.dumps(result, ensure_ascii=False)
            self._messages.append(LLMMessage(
                role="user",
                content=f"工具 {tool_name} 执行结果: {result_content}"
            ))

            # 只在错误时显示错误信息
            if not result.get('success'):
                result_msg = result.get('error', '未知错误')
                if result_msg and result_msg.strip():
                    self._add_message_bubble("assistant", result_msg)

        # 继续对话，让 LLM 基于工具结果生成回复
        self._start_generation()

    def _send_message(self):
        """发送消息"""
        if not self._current_plugin:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "警告", "请先选择LLM插件")
            return

        user_text = self._input_edit.toPlainText().strip()
        if not user_text:
            return

        if self._is_generating:
            return

        # 创建用户消息
        user_message = LLMMessage(role="user", content=user_text)

        # 添加用户消息到界面
        self._add_message_bubble("user", user_text)
        self._messages.append(user_message)

        # 保存消息到会话
        self._save_current_message(user_message)

        # 清空输入框
        self._input_edit.clear()

        # 开始生成回复
        self._start_generation()

    def _start_generation(self):
        """开始生成回复"""
        if self._llm_integration is None:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", "LLM集成未初始化")
            return

        self._is_generating = True
        self._send_button.setEnabled(False)
        self._send_button.setText("⏳ 生成中...")

        # 不预先创建空的 assistant bubble，等到有内容时再创建
        self._current_assistant_bubble = None

        # 创建并启动对话线程
        tools = self._tool_manager.get_tools_for_llm() if self._tool_manager else None

        # 如果有工具,添加system prompt强制使用工具
        messages_to_send = self._messages.copy()
        
        # 添加当前文档状态信息到系统提示中
        if tools and len(tools) > 0:
            # 获取当前文档状态信息
            doc_context = self._get_document_context()
            
            # 构建system prompt,包含文档上下文信息
            system_prompt = (
                "你是一个PDF文档助手。当用户要求对PDF文档进行任何操作时,"
                "包括但不限于打开、保存、拆分、合并、OCR识别、加密、插入图片、插入PDF页面、"
                "删除页面、旋转页面、提取页面、创建可搜索PDF、条形码分割等,"
                "你必须使用相应的工具来完成操作。"
                "不要询问参数,如果参数缺失,工具会提示用户输入。"
                "仔细分析用户的请求,使用最合适的工具完成任务。"
                "\n\n注意："
                "1. 用户可能会复制粘贴错误日志或调试信息，这种情况下不要调用任何工具，"
                "   应该直接分析用户的意图或提示用户提供清晰的问题描述。"
                "2. 只有在用户明确提出PDF操作需求时才使用工具，其他情况直接对话回复。"
                "3. 不要盲目执行工具，先理解用户的真实需求再决定。"
            )
            
            # 添加文档上下文信息
            if doc_context:
                system_prompt += f"\n\n当前文档状态:\n{doc_context}"
            
            system_prompt += f"\n\n可用工具: " + ", ".join([t["function"]["name"] for t in tools])
            
            # 移除所有旧的system message
            messages_to_send = [m for m in messages_to_send if m.role != "system"]
            
            # 在开头插入新的system message
            messages_to_send.insert(0, LLMMessage(role="system", content=system_prompt))


        self._chat_thread = LLMChatThread(self._llm_integration, self._current_plugin, messages_to_send, tools)
        self._chat_thread.response_signal.connect(self._on_response)
        self._chat_thread.start()

    def _on_response(self, content: str, is_error: bool, error_msg: str, is_complete: bool, metadata: dict):
        """处理LLM响应"""
        try:
            # 检查是否为工具调用
            metadata_has_tool_calls = metadata and "tool_calls" in metadata

            logger.debug(f"_on_response called: is_error={is_error}, content_len={len(content) if content else 0}, metadata_has_tool_calls={metadata_has_tool_calls}, metadata={metadata}")

            if is_error:
                # 显示错误信息
                error_msg = f"❌ {error_msg}"

                # 保存错误消息到会话
                error_message = LLMMessage(role="assistant", content=error_msg)
                self._save_current_message(error_message)

                self._add_message_bubble("assistant", error_msg)
                logger.error(f"LLM error: {error_msg}")
            elif content and content.strip():  # 只处理非空内容
                # 检查内容是否包含以$开头的特殊标记
                special_content_handled = self._handle_special_content(content)

                if not special_content_handled:
                    # 如果没有特殊标记被处理，按正常流程添加内容
                    logger.debug(f"Updating content with {len(content)} characters")

                    # 如果还没有创建 bubble，现在创建
                    if self._current_assistant_bubble is None:
                        self._current_assistant_bubble = MessageBubble("assistant", "")
                        self._message_layout.addWidget(self._current_assistant_bubble)

                    current_text = self._current_assistant_bubble._text_edit.toPlainText()
                    self._current_assistant_bubble.update_content(current_text + content)

                # 滚动到底部
                message_area = self._message_container.parent()
                if isinstance(message_area, QScrollArea):
                    message_area.verticalScrollBar().setValue(
                        message_area.verticalScrollBar().maximum()
                    )
            elif metadata_has_tool_calls:
                # 处理工具调用
                # 安全地将工具调用转换为普通数据结构，防止特殊对象引发阻塞
                raw_tool_calls = metadata.get("tool_calls") if metadata else None

                tool_calls = []

                # 直接使用类型和长度检查,避免bool()调用
                raw_is_list = isinstance(raw_tool_calls, list)

                if raw_is_list:
                    raw_len = 0
                    try:
                        raw_len = len(raw_tool_calls)
                    except Exception as e:
                        logger.error(f"Error getting len: {e}", exc_info=True)

                    if raw_len > 0:
                        # 将可能的特殊对象转换为普通字典
                        for idx in range(raw_len):  # 使用索引迭代,避免直接迭代
                            call = raw_tool_calls[idx]
                            try:
                                if isinstance(call, dict):
                                    # 如果已经是字典，显式构建新字典，避免调用dict()可能触发的特殊方法
                                    new_call = {}
                                    for key, value in call.items():
                                        new_call[key] = value
                                    tool_calls.append(new_call)
                                elif hasattr(call, '__dict__'):
                                    # 如果是对象，尝试转换为字典
                                    call_dict = {}
                                    for key, value in vars(call).items():
                                        # 递归处理嵌套对象
                                        if isinstance(value, (dict, list, str, int, float, bool, type(None))):
                                            call_dict[key] = value
                                        else:
                                            # 对于其他类型，尝试转换为字符串
                                            call_dict[key] = str(value)
                                    tool_calls.append(call_dict)
                                else:
                                    # 其他情况，尝试转换为字典
                                    new_call = {}
                                    for key in dir(call):
                                        if not key.startswith('_'):
                                            try:
                                                value = getattr(call, key)
                                                if not callable(value):
                                                    new_call[key] = value
                                            except Exception:
                                                pass
                                    tool_calls.append(new_call)
                            except Exception as e:
                                logger.error(f"Error converting tool call to dict: {e}")

                if tool_calls:
                    self._handle_tool_calls(tool_calls)

            if is_complete:
                # 对话完成
                self._is_generating = False
                self._send_button.setEnabled(True)
                self._send_button.setText("🚀 发送")

                # 将完整回复添加到消息历史(只有创建了bubble且有内容才添加)
                if self._current_assistant_bubble is not None:
                    final_content = self._current_assistant_bubble._text_edit.toPlainText()
                    if final_content.strip():
                        assistant_message = LLMMessage(role="assistant", content=final_content)
                        self._messages.append(assistant_message)
                        # 保存助手回复到会话
                        self._save_current_message(assistant_message)
                    else:
                        # 如果没有内容,删除空白气泡
                        self._message_layout.removeWidget(self._current_assistant_bubble)
                        self._current_assistant_bubble.deleteLater()
                        self._current_assistant_bubble = None
                        logger.debug("Removed empty assistant bubble")
                else:
                    logger.debug("No assistant bubble created (LLM only returned tool calls)")
                
        except Exception as e:
            logger.error(f"Error in _on_response: {e}", exc_info=True)
            error_msg = f"❌ 处理响应时出错: {str(e)}"

            # 保存错误消息到会话
            error_message = LLMMessage(role="assistant", content=error_msg)
            self._save_current_message(error_message)

            self._add_message_bubble("assistant", error_msg)

            # 确保即使出错也能恢复状态
            self._is_generating = False
            self._send_button.setEnabled(True)
            self._send_button.setText("🚀 发送")

    def _handle_tool_calls(self, tool_calls: List[Dict[str, Any]]):
        """
        处理工具调用
        """
        try:
            tool_calls_len = 0
            if tool_calls is not None:
                try:
                    tool_calls_len = len(tool_calls)
                except Exception as e:
                    logger.error(f"Error getting len of tool_calls: {e}", exc_info=True)
                    tool_calls_len = 0

            tool_manager_available = self._tool_manager is not None

            tool_calls_len_for_check = 0
            if tool_calls is not None and isinstance(tool_calls, list):
                try:
                    tool_calls_len_for_check = len(tool_calls)
                except Exception as e:
                    logger.error(f"Error getting len for check: {e}", exc_info=True)

            tool_calls_available = tool_calls is not None and isinstance(tool_calls, list) and tool_calls_len_for_check > 0

            if not tool_calls_available or not tool_manager_available:
                logger.warning(f"Skipping tool calls: tool_calls={tool_calls_available}, tool_manager={tool_manager_available}")
                return

            # 安全地获取并输出首个工具调用名称日志，满足用户要求
            first_tool_name = 'N/A'
            tool_calls_len_for_check2 = 0
            if tool_calls is not None and isinstance(tool_calls, list):
                try:
                    tool_calls_len_for_check2 = len(tool_calls)
                except Exception as e:
                    logger.error(f"Error getting len for first tool check: {e}", exc_info=True)

            if tool_calls and tool_calls_len_for_check2 > 0:
                try:
                    first_tool_call = tool_calls[0]
                    if hasattr(first_tool_call, 'get'):
                        first_tool_name = first_tool_call.get('name', 'N/A')
                    elif isinstance(first_tool_call, dict):
                        first_tool_name = first_tool_call.get('name', 'N/A')
                    else:
                        first_tool_name = getattr(first_tool_call, 'name', 'N/A')
                except Exception as e:
                    logger.error(f"Error getting first tool call name: {e}", exc_info=True)
                    first_tool_name = 'Error'

            # 注意:工具调用已经在 _on_response 中添加到消息历史,这里不需要再次添加

            # 保存待处理的工具列表（用于需要用户交互的场景）
            self._pending_tool_calls = tool_calls.copy()

            # 收集所有工具执行结果
            tool_results = []

            # 执行每个工具调用
            for tool_call in tool_calls:
                logger.debug(f"Processing tool_call: {tool_call}")
                # 安全地获取工具名称和参数
                try:
                    if hasattr(tool_call, 'get'):
                        tool_name = tool_call.get("name")
                        arguments_str = tool_call.get("arguments", "{}")
                    elif isinstance(tool_call, dict):
                        tool_name = tool_call.get("name")
                        arguments_str = tool_call.get("arguments", "{}")
                    else:
                        # 如果是其他类型，尝试直接访问属性
                        tool_name = getattr(tool_call, 'name', None)
                        arguments_str = getattr(tool_call, 'arguments', "{}")
                except Exception as e:
                    logger.error(f"Error getting tool attributes: {e}", exc_info=True)
                    continue  # 跳过这个工具调用

                logger.debug(f"Tool name: {tool_name}, Arguments string: {arguments_str}")

                # 验证工具名称是否为空,如果为空则跳过处理
                if not tool_name:
                    logger.warning(f"Tool call has empty name, skipping. Arguments: {arguments_str}")
                    continue

                try:
                    # 安全解析参数
                    try:
                        arguments = json.loads(arguments_str)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse arguments: {arguments_str}, error: {e}")
                        arguments = {}

                    # 检查参数是否完整,如果不完整则通过action bubble收集
                    if self._tool_manager and self._tool_manager.get_tool_registry():
                        tool = self._tool_manager.get_tool_registry().get_tool(tool_name)
                        if tool:
                            complete, missing_params = tool.check_parameters_complete(arguments)
                            if not complete:
                                logger.info(f"Tool {tool_name} missing parameters: {missing_params}")
                                # 为缺失的参数创建action bubble
                                if missing_params:
                                    # 对于文件路径类型的参数,使用file_chooser
                                    for param_name in missing_params:
                                        if 'path' in param_name or 'file' in param_name:
                                            # 使用文件选择器
                                            self._add_action_bubble("file_chooser", {
                                                "purpose": f"选择{tool.description}",
                                                "file_filter": self._get_file_filter_for_tool(tool_name),
                                                "save_mode": "output" in param_name or "save" in param_name
                                            })
                                            break  # 一次只处理一个参数
                                    # 如果不是文件参数,使用通用输入
                                    else:
                                        param_schema = tool.get_parameters_schema().get("properties", {}).get(missing_params[0], {})
                                        self._add_action_bubble("input", {
                                            "placeholder": param_schema.get("description", f"请输入{missing_params[0]}")
                                        })
                                # 停止处理工具调用,等待用户操作
                                return

                    # 特殊处理file_chooser工具 - 在对话中显示文件选择UI
                    if tool_name == "file_chooser":
                        try:
                            bubble = self._add_action_bubble("file_chooser", arguments)
                        except Exception as e:
                            logger.error(f"Error adding file_chooser bubble: {e}", exc_info=True)
                            error_msg = f"\n❌ 无法显示文件选择界面: {str(e)}\n"

                            # 保存错误消息到会话
                            error_message = LLMMessage(role="assistant", content=error_msg)
                            self._save_current_message(error_message)

                            self._add_message_bubble("assistant", error_msg)
                        return  # 等待用户选择文件

                    # 特殊处理confirm工具 - 在对话中显示确认UI
                    if tool_name == "confirm":
                        try:
                            self._add_action_bubble("confirm", arguments)
                        except Exception as e:
                            logger.error(f"Error adding confirm bubble: {e}", exc_info=True)
                            error_msg = f"\n❌ 无法显示确认界面: {str(e)}\n"

                            # 保存错误消息到会话
                            error_message = LLMMessage(role="assistant", content=error_msg)
                            self._save_current_message(error_message)

                            self._add_message_bubble("assistant", error_msg)
                        return  # 等待用户确认

                    # 特殊处理input工具 - 在对话中显示输入UI
                    if tool_name == "user_input":
                        try:
                            self._add_action_bubble("input", arguments)
                        except Exception as e:
                            logger.error(f"Error adding input bubble: {e}", exc_info=True)
                            error_msg = f"\n❌ 无法显示输入界面: {str(e)}\n"

                            # 保存错误消息到会话
                            error_message = LLMMessage(role="assistant", content=error_msg)
                            self._save_current_message(error_message)

                            self._add_message_bubble("assistant", error_msg)
                        return  # 等待用户输入

                    # 特殊处理password工具 - 在对话中显示密码输入UI
                    if tool_name == "password":
                        try:
                            self._add_action_bubble("password", arguments)
                        except Exception as e:
                            logger.error(f"Error adding password bubble: {e}", exc_info=True)
                            error_msg = f"\n❌ 无法显示密码输入界面: {str(e)}\n"

                            # 保存错误消息到会话
                            error_message = LLMMessage(role="assistant", content=error_msg)
                            self._save_current_message(error_message)

                            self._add_message_bubble("assistant", error_msg)
                        return  # 等待用户输入密码

                    # 特殊处理open_pdf工具 - 先让用户选择文件
                    if tool_name == "open_pdf":
                        file_path = arguments.get("file_path")
                        if not file_path:
                            # 没有提供文件路径,显示文件选择器
                            self._add_action_bubble("file_chooser", {
                                "purpose": "选择PDF文件",
                                "file_filter": "PDF Files (*.pdf)",
                                "save_mode": False
                            })
                            return  # 等待用户选择文件

                    # 特殊处理save_pdf, insert_pdf_page, insert_image_page, extract_pages等需要输出路径的工具
                    output_path_tools = ["save_pdf", "extract_pages", "insert_pdf_page", "insert_image_page", "merge_pdf", "encrypt_pdf"]
                    if tool_name in output_path_tools:
                        output_path = arguments.get("output_path")
                        if not output_path:
                            # 没有提供输出路径,显示文件选择器
                            save_mode = tool_name != "insert_pdf_page" and tool_name != "insert_image_page"
                            self._add_action_bubble("file_chooser", {
                                "purpose": f"选择{tool.description}",
                                "file_filter": "PDF Files (*.pdf)",
                                "save_mode": True
                            })
                            return  # 等待用户选择保存位置

                    # 特殊处理insert_pdf_page, insert_image_page需要源文件/图片路径
                    if tool_name in ["insert_pdf_page", "insert_image_page"]:
                        source_path = arguments.get("pdf_path") if tool_name == "insert_pdf_page" else arguments.get("image_path")
                        if not source_path:
                            # 没有提供源文件路径,显示文件选择器
                            file_filter = "PDF Files (*.pdf)" if tool_name == "insert_pdf_page" else "Image Files (*.png *.jpg *.jpeg *.gif *.bmp *.tiff)"
                            self._add_action_bubble("file_chooser", {
                                "purpose": f"选择{tool.description}",
                                "file_filter": file_filter,
                                "save_mode": False
                            })
                            return  # 等待用户选择源文件

                    # 对于其他工具，异步执行
                    loop = asyncio.get_event_loop()
                    try:
                        if loop.is_running():
                            result = asyncio.run_coroutine_threadsafe(
                                self._execute_tool(tool_name, arguments), loop
                            ).result(timeout=120)  # 耗时工具延长超时到2分钟
                        else:
                            result = loop.run_until_complete(self._execute_tool(tool_name, arguments))
                    except RuntimeError:
                        result = asyncio.run(self._execute_tool(tool_name, arguments))

                    # 执行完成后清理
                    self._cleanup_after_tool_execution(tool_name)

                    # 收集工具执行结果
                    tool_results.append({
                        "name": tool_name,
                        "result": result
                    })

                except Exception as e:
                    logger.error(f"Error processing tool call {tool_name}: {e}", exc_info=True)
                    # 即使出错也要清理
                    self._cleanup_after_tool_execution(tool_name)

                    # 记录错误结果
                    tool_results.append({
                        "name": tool_name,
                        "result": {"success": False, "error": str(e)}
                    })

                    # 保存错误消息到会话
                    error_msg = f"\n❌ 工具执行错误: {str(e)}\n"
                    error_message = LLMMessage(role="assistant", content=error_msg)
                    self._save_current_message(error_message)
                    self._add_message_bubble("assistant", error_msg)

            # 所有工具执行完成，将结果统一反馈给大模型
            self._send_tool_results_to_llm(tool_results)

        except Exception as e:
            logger.error(f"Error in _handle_tool_calls: {e}", exc_info=True)
            error_msg = f"\n❌ 处理工具调用时出错: {str(e)}\n"

            # 保存错误消息到会话
            error_message = LLMMessage(role="assistant", content=error_msg)
            self._save_current_message(error_message)

            self._add_message_bubble("assistant", error_msg)

    def _get_file_filter_for_tool(self, tool_name: str) -> str:
        """根据工具名称获取文件过滤器"""
        filter_map = {
            "open_pdf": "PDF Files (*.pdf)",
            "save_pdf": "PDF Files (*.pdf)",
            "insert_pdf_page": "PDF Files (*.pdf)",
            "insert_image_page": "Image Files (*.png *.jpg *.jpeg *.gif *.bmp *.tiff)",
            "extract_pages": "PDF Files (*.pdf)",
            "merge_pdf": "PDF Files (*.pdf)",
            "encrypt_pdf": "PDF Files (*.pdf)"
        }
        return filter_map.get(tool_name, "All Files (*)")

    async def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """异步执行工具"""
        if not self._tool_manager:
            logger.error("Tool manager not available")
            return {"success": False, "error": "Tool manager not available"}

        # 检查工具是否需要在主线程中执行
        tool = self._tool_manager.get_tool_registry().get_tool(tool_name)
        if not tool:
            return {"success": False, "error": f"工具 '{tool_name}' 不存在"}

        # 获取工具描述
        tool_description = tool.description

        # 定义耗时工具列表(这些工具执行时间较长)
        time_consuming_tools = ["ocr_page", "create_searchable_pdf", "encrypt_pdf", "split_pdf", "merge_pdf"]

        # 判断是否为耗时工具
        is_time_consuming = tool_name in time_consuming_tools

        # 显示进度提示
        import time
        self._tool_start_time = time.time()

        # 禁用发送按钮,防止重复点击
        if hasattr(self, '_send_button'):
            self._send_button.setEnabled(False)

        # 显示状态栏提示
        parent_window = self.parent()
        while parent_window:
            if hasattr(parent_window, 'show_message'):
                parent_window.show_message(f"正在执行: {tool_description}...")
                break
            parent_window = parent_window.parent()

        # 如果是耗时工具,显示进度对话框
        if is_time_consuming:
            self._progress_dialog = QProgressDialog(
                f"正在{tool_description}...",
                "取消",
                0, 100, self
            )
            self._progress_dialog.setWindowTitle("处理中")
            self._progress_dialog.setWindowModality(Qt.WindowModal)
            self._progress_dialog.show()

        if tool.requires_main_thread():
            # 对于需要在主线程执行的同步工具,直接同步调用execute
            try:
                # 直接同步调用,不使用async
                import inspect
                if inspect.iscoroutinefunction(tool.execute):
                    # 如果是async方法,需要创建新的事件循环
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        result = loop.run_until_complete(tool.execute(arguments))
                        return result
                    finally:
                        loop.close()
                else:
                    # 同步方法,直接调用
                    result = tool.execute(arguments)
                    return result
            except Exception as e:
                logger.error(f"Error executing tool on main thread: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": f"工具执行失败: {str(e)}"
                }
        else:
            # 在异步线程中执行
            return await self._tool_manager.handle_tool_call(tool_name, arguments)

    def _cleanup_after_tool_execution(self, tool_name: str):
        """工具执行后的清理工作"""
        try:
            # 恢复发送按钮
            if hasattr(self, '_send_button'):
                self._send_button.setEnabled(True)

            # 关闭进度对话框
            if self._progress_dialog is not None:
                self._progress_dialog.close()
                self._progress_dialog = None

            # 清除状态栏提示
            parent_window = self.parent()
            while parent_window:
                if hasattr(parent_window, 'show_message'):
                    parent_window.show_message("")
                    break
                parent_window = parent_window.parent()

            logger.info(f"Tool execution cleanup completed for: {tool_name}")
        except Exception as e:
            logger.error(f"Error in cleanup after tool execution: {e}", exc_info=True)

    async def _encrypt_pdf_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """加密PDF文件"""
        password = params.get("password")
        output_path = params.get("output_path")
        
        if not password or not output_path:
            return {"success": False, "error": "缺少密码或输出路径"}
        
        # 获取主窗口的PDF处理器
        parent_window = self.parent()
        main_window = None
        while parent_window:
            if hasattr(parent_window, 'pdf_processor'):
                main_window = parent_window
                break
            parent_window = parent_window.parent()
        
        if not main_window:
            return {"success": False, "error": "无法访问PDF处理器"}
        
        try:
            # 使用主窗口的PDF处理器进行加密
            success = main_window.pdf_processor.encrypt_pdf(password, output_path)
            if success:
                return {"success": True, "message": f"PDF已加密并保存到: {output_path}"}
            else:
                return {"success": False, "error": "加密失败"}
        except Exception as e:
            logger.error(f"Error encrypting PDF: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def _handle_special_content(self, content: str) -> bool:
        """
        处理特殊内容标记，如$pdf_display, $pdf_controls等
        返回值：如果处理了特殊内容则返回True，否则返回False
        """
        # 查找所有以$开头的标记
        import re
        special_markers = re.findall(r'\$[a-zA-Z_][a-zA-Z0-9_]*', content)
        
        if not special_markers:
            return False
        
        # 标记是否处理了任何特殊内容
        handled = False
        
        # 获取主窗口
        parent_window = self.parent()
        main_window = None
        while parent_window:
            if hasattr(parent_window, 'pdf_processor'):
                main_window = parent_window
                break
            parent_window = parent_window.parent()
        
        for marker in special_markers:
            # 根据标记类型执行相应的操作
            if marker == "$pdf_display" or marker == "$pdf_controls":
                if main_window:
                    try:
                        main_window.update_preview()
                        handled = True
                    except Exception as e:
                        logger.error(f"Error updating PDF preview for {marker}: {e}")
            elif marker == "$refresh_ui":
                # 刷新UI
                try:
                    if hasattr(main_window, 'update_preview'):
                        main_window.update_preview()
                        handled = True
                    elif hasattr(main_window, 'repaint'):
                        main_window.repaint()
                        handled = True
                except Exception as e:
                    logger.error(f"Error refreshing UI for {marker}: {e}")
            elif marker == "$show_thumbnails":
                # 显示缩略图
                if main_window and hasattr(main_window, 'toggle_thumbnails'):
                    try:
                        main_window.toggle_thumbnails()
                        handled = True
                    except Exception as e:
                        logger.error(f"Error showing thumbnails for {marker}: {e}")
            elif marker == "$fit_to_width":
                # 适应宽度
                if main_window and hasattr(main_window, 'view_controller') and hasattr(main_window.view_controller, 'fit_to_width'):
                    try:
                        main_window.view_controller.fit_to_width()
                        handled = True
                    except Exception as e:
                        logger.error(f"Error fitting to width for {marker}: {e}")
            elif marker == "$fit_to_height":
                # 适应高度
                if main_window and hasattr(main_window, 'view_controller') and hasattr(main_window.view_controller, 'fit_to_height'):
                    try:
                        main_window.view_controller.fit_to_height()
                        handled = True
                    except Exception as e:
                        logger.error(f"Error fitting to height for {marker}: {e}")
            else:
                # 可以扩展更多标记类型
                logger.debug(f"Unknown special marker: {marker}")
        
        # 返回是否处理了任何特殊内容
        return handled

    def _clear_chat(self):
        """清空聊天"""
        # 清空消息布局
        for i in reversed(range(self._message_layout.count())):
            widget = self._message_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        # 清空消息历史
        self._messages.clear()

        # 添加欢迎消息
        self._add_message_bubble("assistant", "您好！我是AI助手，可以帮助您处理PDF文档。您可以问我任何关于PDF的问题或请求我执行相关操作。")

    def _create_new_session(self):
        """创建新会话"""
        if not self._session_manager:
            logger.warning("Session manager not initialized")
            return

        # 创建新会话
        new_session = self._session_manager.create_session("新对话", self._current_plugin)

        # 切换到新会话
        self._switch_to_session(new_session)

        # 刷新会话列表
        self._refresh_session_list()

        logger.info(f"Created new session: {new_session.session_id}")

    def _on_session_changed(self, index: int):
        """会话选择改变"""
        if index < 0 or not self._session_manager:
            return

        session_id = self._session_combo.itemData(index)
        if not session_id:
            return

        # 获取会话
        session = self._session_manager.get_session(session_id)
        if session and session.session_id != self._current_session.session_id:
            # 切换会话
            self._switch_to_session(session)
            logger.info(f"Switched to session: {session_id}")

    def _switch_to_session(self, session: ChatSession):
        """切换到指定会话"""
        # 切换当前会话
        self._current_session = session
        self._session_manager.set_current_session(session.session_id)

        # 加载会话历史
        self._load_session_history(session)

        # 更新插件选择
        if session.plugin:
            index = self._plugin_combo.findText(session.plugin)
            if index >= 0:
                self._plugin_combo.setCurrentIndex(index)

    def _save_current_message(self, message: LLMMessage):
        """保存消息到当前会话"""
        if self._current_session and self._session_manager:
            self._session_manager.add_message(self._current_session.session_id, message)

            # 如果是第一条用户消息,更新会话标题
            if message.role == "user" and len(self._current_session.messages) == 1:
                # 取消息的前30个字符作为标题
                title = message.content[:30] + "..." if len(message.content) > 30 else message.content
                self._session_manager.update_session_title(self._current_session.session_id, title)

                # 刷新会话列表
                self._refresh_session_list()

    def _delete_current_session(self):
        """删除当前会话"""
        from PyQt5.QtWidgets import QMessageBox

        if not self._current_session:
            QMessageBox.warning(self, "警告", "没有可删除的会话")
            return

        # 确认对话框
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setWindowTitle("确认删除")
        msg_box.setText(f"确定要删除会话「{self._current_session.title}」吗？")
        msg_box.setInformativeText("此操作不可恢复，会话及其所有消息将被永久删除。")

        yes_btn = msg_box.addButton("删除", QMessageBox.YesRole)
        no_btn = msg_box.addButton("取消", QMessageBox.NoRole)
        msg_box.setDefaultButton(no_btn)
        msg_box.exec_()

        if msg_box.clickedButton() != yes_btn:
            return

        # 执行删除
        session_id = self._current_session.session_id
        if self._session_manager.delete_session(session_id):
            # 清空消息显示
            self._clear_message_display()

            # 刷新会话列表
            self._refresh_session_list()

            # 加载新会话
            self._load_current_session()

            QMessageBox.information(self, "删除成功", "会话已成功删除")
        else:
            QMessageBox.critical(self, "删除失败", "删除会话失败，请稍后重试")

    def _clear_message_display(self):
        """清空消息显示区域"""
        # 删除所有消息气泡
        for i in reversed(range(self._message_layout.count())):
            item = self._message_layout.itemAt(i)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _load_current_session(self):
        """加载当前会话"""
        # 获取当前会话
        self._current_session = self._session_manager.get_current_session()

        if not self._current_session:
            # 如果没有当前会话，创建新会话
            self._current_session = self._session_manager.create_session()
            self._refresh_session_list()

        # 加载会话历史
        self._load_session_history(self._current_session)

    def _close_sidebar(self):
        """关闭侧边栏"""
        # 获取主窗口
        parent_window = self.parent()
        while parent_window:
            if hasattr(parent_window, '_toggle_llm_sidebar'):
                # 调用主窗口的切换方法来关闭侧边栏
                parent_window._toggle_llm_sidebar()
                break
            parent_window = parent_window.parent()

    def _get_document_context(self) -> str:
        """
        获取当前文档的上下文信息
        返回格式化后的文档状态字符串
        """
        context_parts = []
        
        # 获取主窗口
        parent_window = self.parent()
        main_window = None
        while parent_window:
            if hasattr(parent_window, 'pdf_processor'):
                main_window = parent_window
                break
            parent_window = parent_window.parent()
        
        if not main_window:
            return ""
        
        # 获取文档基本信息
        try:
            if hasattr(main_window, 'pdf_processor'):
                pdf_processor = main_window.pdf_processor
                
                # 获取总页数
                if hasattr(pdf_processor, 'page_count'):
                    total_pages = pdf_processor.page_count
                    context_parts.append(f"总页数: {total_pages}")
                
                # 获取当前页码
                if hasattr(main_window, 'current_page'):
                    current_page = main_window.current_page
                    context_parts.append(f"当前页: {current_page}")
                
                # 获取当前缩放比例
                if hasattr(main_window, 'pdf_renderer') and hasattr(main_window.pdf_renderer, 'current_scale'):
                    scale = main_window.pdf_renderer.current_scale
                    context_parts.append(f"缩放比例: {scale:.2f}x")
                
                # 获取文档路径
                if hasattr(pdf_processor, 'pdf_file'):
                    doc_path = pdf_processor.pdf_file
                    if doc_path:
                        import os
                        doc_name = os.path.basename(doc_path)
                        context_parts.append(f"文档名: {doc_name}")
                else:
                    context_parts.append("未打开文档")
                
                # 获取文档是否加密
                if hasattr(pdf_processor, 'is_encrypted'):
                    is_encrypted = pdf_processor.is_encrypted()
                    context_parts.append(f"是否加密: {'是' if is_encrypted else '否'}")
                
                # 获取文档是否已加载
                if hasattr(pdf_processor, 'is_loaded'):
                    is_loaded = pdf_processor.is_loaded()
                    context_parts.append(f"文档状态: {'已加载' if is_loaded else '未加载'}")
                
        except Exception as e:
            logger.error(f"Error getting document context: {e}", exc_info=True)
        
        return "\n".join(context_parts) if context_parts else ""
