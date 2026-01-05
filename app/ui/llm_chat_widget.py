"""
新的LLM聊天窗口组件 - 重构版本
提供美观的聊天界面和自然语言交互功能
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFrame, QComboBox, 
    QPushButton, QLabel, QSizePolicy
)
from PyQt5.QtCore import Qt
from typing import List, Dict, Optional, Any
import json
import asyncio

from app.core.llm.llm_plugin_interface import LLMMessage
from app.core.llm.llm_integration import LLMIntegration
from app.config.llm_plugin_config import LLMPluginConfigManager
from app.managers.llm_tool_manager import LLMToolManager
from app.core.llm.tool_interactions.interaction_handler import ToolInteractionHandler
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

        self._init_ui()
        self._get_llm_integration()
        self._load_tools()
        self._load_plugins()

    def _get_llm_integration(self):
        """获取主窗口的LLM集成实例"""
        parent_window = self.parent()
        while parent_window:
            if hasattr(parent_window, '_llm_integration'):
                self._llm_integration = parent_window._llm_integration
                logger.info("Using parent window's LLM integration")
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
                logger.info("Using parent window's LLM tool manager")
                break
            parent_window = parent_window.parent()

        if not self._tool_manager:
            self._tool_manager = LLMToolManager()
            logger.warning("Creating new LLM tool manager instance")

        # 初始化工具交互处理器，使用self作为父对象（NewLLMChatWidget继承自QWidget）
        self._interaction_handler = ToolInteractionHandler(self)
        self._interaction_handler.tool_execution_completed.connect(self._on_tool_execution_completed)
        self._interaction_handler.action_required.connect(self._on_action_required)

    def _on_tool_execution_completed(self, tool_name: str, result: dict):
        """工具执行完成回调"""
        logger.info(f"Tool execution completed: {tool_name}, success: {result.get('success')}")

    def _on_action_required(self, action_type: str, params: Dict[str, Any]):
        """工具需要用户操作"""
        logger.info(f"Tool requires user action: {action_type}, params: {params}")
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
        
        # 清空按钮
        clear_button = QPushButton("🗑️")
        clear_button.setMaximumWidth(40)
        clear_button.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.2);
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 4px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.3);
            }
        """)
        clear_button.clicked.connect(self._clear_chat)
        toolbar_layout.addWidget(clear_button)

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

        logger.info(f"Loaded {len(enabled_plugins)} enabled plugins: {enabled_plugins}")

        # 连接信号
        self._input_edit.textChanged.connect(self._on_input_changed)
        self._plugin_combo.currentTextChanged.connect(self._on_plugin_changed)

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
        logger.info(f"Adding action bubble: {action_type}, params: {params}")
        bubble = ActionBubble(action_type, params)
        bubble.action_completed.connect(self._on_action_completed)
        self._message_layout.addWidget(bubble)

        # 异步滚动到底部，避免阻塞
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(0, self._scroll_to_bottom)

        logger.info(f"Action bubble added successfully: {action_type}")
        return bubble

    def _scroll_to_bottom(self):
        """滚动到底部的辅助方法"""
        try:
            message_area = self._message_container.parent()
            if isinstance(message_area, QScrollArea):
                message_area.verticalScrollBar().setValue(
                    message_area.verticalScrollBar().maximum()
                )
        except Exception as e:
            logger.error(f"Error scrolling to bottom: {e}", exc_info=True)

    def _on_action_completed(self, action_type: str, result: Dict[str, Any]):
        """操作完成回调"""
        logger.info(f"Action completed: {action_type}, result: {result}")

        # 特殊处理:如果是保存模式的文件选择,不添加消息,直接继续
        if action_type == "file_chooser":
            # 使用result中的save_mode标志来判断是否为保存模式
            save_mode = result.get('save_mode', False)
            
            if save_mode:
                # 直接调用继续处理,不添加消息
                self._continue_after_action(action_type, result)
                return

        # 将操作结果添加到消息历史
        result_content = json.dumps(result, ensure_ascii=False)
        self._messages.append(LLMMessage(
            role="user",
            content=f"用户操作 {action_type} 完成: {result_content}"
        ))

        # 显示操作结果消息
        result_msg = f"\n✅ 用户操作 [{action_type}]\n"
        if result.get('success', True):
            result_msg += f"成功: {result.get('message', '操作完成')}\n"
        else:
            result_msg += f"失败: {result.get('error', '未知错误')}\n"
        self._add_message_bubble("assistant", result_msg)

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
                
                # 只依赖save_mode标志，不再进行关键词匹配
                # save_mode应该在工具调用时由系统正确设置

                if save_mode:
                    # 如果是保存模式，记录保存路径，然后询问密码
                    self._pending_encrypt_output_path = file_path

                    # 添加密码输入气泡
                    self._add_action_bubble("password", {
                        "message": "请输入加密密码",
                        "placeholder": "请输入密码"
                    })
                    return

                # 否则，执行 open_pdf 工具（包含打开和渲染的完整流程）
                loop = asyncio.get_event_loop()

                try:
                    if loop.is_running():
                        open_result = asyncio.run_coroutine_threadsafe(
                            self._execute_tool("open_pdf", {"file_path": file_path}), loop
                        ).result(timeout=30)
                    else:
                        open_result = loop.run_until_complete(self._execute_tool("open_pdf", {"file_path": file_path}))
                except RuntimeError:
                    open_result = asyncio.run(self._execute_tool("open_pdf", {"file_path": file_path}))

                # 显示执行结果
                open_msg = f"\n✅ 打开PDF\n"
                if open_result.get('success'):
                    open_msg += f"成功: {open_result.get('message', 'PDF已打开并渲染')}\n"
                else:
                    open_msg += f"失败: {open_result.get('error', '未知错误')}\n"

                self._add_message_bubble("assistant", open_msg)

                # 将工具执行结果添加到消息历史
                self._messages.append(LLMMessage(
                    role="user",
                    content=f"工具 open_pdf 执行结果: {json.dumps(open_result, ensure_ascii=False)}"
                ))
                self._start_generation()

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
            self._add_message_bubble("assistant", f"\n❌ 继续执行失败: {str(e)}\n")
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

        # 添加用户消息
        self._add_message_bubble("user", user_text)
        self._messages.append(LLMMessage(role="user", content=user_text))

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

        # 添加助手消息气泡
        self._current_assistant_bubble = MessageBubble("assistant", "")
        self._message_layout.addWidget(self._current_assistant_bubble)

        # 创建并启动对话线程
        tools = self._tool_manager.get_tools_for_llm() if self._tool_manager else None

        # 如果有工具,添加system prompt强制使用工具
        messages_to_send = self._messages.copy()
        if tools and len(tools) > 0:
            # 检查是否已经有system message
            has_system = any(m.role == "system" for m in messages_to_send)
            if not has_system:
                # 添加system prompt,明确要求使用工具
                system_prompt = (
                    "你是一个PDF文档助手。当用户要求打开、拆分、OCR、合并或加密PDF文档时,"
                    "你必须使用相应的工具来完成操作。"
                    "不要询问参数,如果参数缺失,工具会提示用户输入。"
                    "可用工具: " + ", ".join([t["function"]["name"] for t in tools])
                )
                messages_to_send.insert(0, LLMMessage(role="system", content=system_prompt))
                logger.info(f"Added system prompt to enforce tool usage")

        logger.info(f"Starting generation with {len(tools) if tools else 0} tools for plugin: {self._current_plugin}")

        self._chat_thread = LLMChatThread(self._llm_integration, self._current_plugin, messages_to_send, tools)
        self._chat_thread.response_signal.connect(self._on_response)
        self._chat_thread.start()

    def _on_response(self, content: str, is_error: bool, error_msg: str, is_complete: bool, metadata: dict):
        """处理LLM响应"""
        try:
            # 检查是否为工具调用
            metadata_has_tool_calls = metadata and "tool_calls" in metadata

            if is_error:
                # 显示错误信息
                self._add_message_bubble("assistant", f"❌ {error_msg}")
                logger.error(f"LLM error: {error_msg}")
            elif content:
                # 更新助手消息内容
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
                logger.info(f"Received tool calls: {metadata['tool_calls']}")
                
                # 安全地将工具调用转换为普通数据结构，防止特殊对象引发阻塞
                raw_tool_calls = metadata["tool_calls"]
                tool_calls = []
                
                if raw_tool_calls:
                    # 将可能的特殊对象转换为普通字典
                    for call in raw_tool_calls:
                        try:
                            if isinstance(call, dict):
                                # 如果已经是字典，直接添加
                                tool_calls.append(dict(call))
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
                                # 其他情况，尝试直接转换
                                tool_calls.append(dict(call))
                        except Exception as e:
                            logger.error(f"Error converting tool call to dict: {e}")
                            # 如果转换失败，跳过这个工具调用
                            continue

                if tool_calls:
                    logger.info(f"About to call _handle_tool_calls")
                    self._handle_tool_calls(tool_calls)

            if is_complete:
                # 对话完成
                self._is_generating = False
                self._send_button.setEnabled(True)
                self._send_button.setText("🚀 发送")
                
                # 将完整回复添加到消息历史
                final_content = self._current_assistant_bubble._text_edit.toPlainText()
                if final_content.strip():
                    self._messages.append(LLMMessage(role="assistant", content=final_content))
                
                logger.info("LLM generation completed")

        except Exception as e:
            logger.error(f"Error in _on_response: {e}", exc_info=True)
            self._add_message_bubble("assistant", f"❌ 处理响应时出错: {str(e)}")
            
            # 确保即使出错也能恢复状态
            self._is_generating = False
            self._send_button.setEnabled(True)
            self._send_button.setText("🚀 发送")

    def _handle_tool_calls(self, tool_calls: List[Dict[str, Any]]):
        """
        处理工具调用
        """
        try:
            logger.info(f"_handle_tool_calls called with {len(tool_calls) if tool_calls else 0} tool calls, tool_manager: {self._tool_manager is not None}")

            # 安全地获取tool_calls和tool_manager的布尔值，避免在条件判断中卡住
            tool_calls_available = bool(tool_calls) if tool_calls is not None else False
            tool_manager_available = self._tool_manager is not None
            
            logger.debug(f"Checking tool calls: tool_calls_available={tool_calls_available}, tool_manager_available={tool_manager_available}")
            
            if not tool_calls_available or not tool_manager_available:
                logger.warning(f"Skipping tool calls: tool_calls={tool_calls_available}, tool_manager={tool_manager_available}")
                return

            logger.info(f"Received {len(tool_calls)} tool calls")

            # 安全地获取并输出首个工具调用名称日志，满足用户要求
            first_tool_name = 'N/A'
            if tool_calls and len(tool_calls) > 0:
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
            
            logger.info(f"First tool call name: {first_tool_name}")

            # 注意:工具调用已经在 _on_response 中添加到消息历史,这里不需要再次添加

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
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse arguments: {arguments_str}")
                        arguments = {}
                    
                    logger.info(f"Executing tool: {tool_name} with args: {arguments}")

                    logger.debug(f"Checking tool type: {tool_name}, expected 'file_chooser'")
                    logger.debug(f"Tool name == 'file_chooser': {tool_name == 'file_chooser'}")
                    
                    # 特殊处理file_chooser工具 - 在对话中显示文件选择UI
                    if tool_name == "file_chooser":
                        logger.info(f"About to add file_chooser bubble with args: {arguments}")
                        try:
                            self._add_action_bubble("file_chooser", arguments)
                            logger.info(f"file_chooser bubble added, continuing to next tool")
                        except Exception as e:
                            logger.error(f"Error adding file_chooser bubble: {e}", exc_info=True)
                            self._add_message_bubble("assistant", f"\n❌ 无法显示文件选择界面: {str(e)}\n")
                        continue  # 直接处理下一个工具调用

                    # 特殊处理confirm工具 - 在对话中显示确认UI
                    if tool_name == "confirm":
                        try:
                            self._add_action_bubble("confirm", arguments)
                        except Exception as e:
                            logger.error(f"Error adding confirm bubble: {e}", exc_info=True)
                            self._add_message_bubble("assistant", f"\n❌ 无法显示确认界面: {str(e)}\n")
                        continue

                    # 特殊处理input工具 - 在对话中显示输入UI
                    if tool_name == "user_input":
                        try:
                            self._add_action_bubble("input", arguments)
                        except Exception as e:
                            logger.error(f"Error adding input bubble: {e}", exc_info=True)
                            self._add_message_bubble("assistant", f"\n❌ 无法显示输入界面: {str(e)}\n")
                        continue

                    # 特殊处理encrypt_pdf工具 - 先让用户选择保存路径
                    if tool_name == "encrypt_pdf":
                        # 先让用户选择保存路径
                        import os
                        parent_window = self.parent()
                        main_window = None
                        while parent_window:
                            if hasattr(parent_window, 'pdf_processor'):
                                main_window = parent_window
                                break
                            parent_window = parent_window.parent()

                        if main_window:
                            # 添加文件选择气泡，设置为保存模式
                            save_args = arguments.copy()
                            save_args["save_mode"] = True
                            save_args["purpose"] = "选择加密后保存的文件路径"
                            save_args["file_filter"] = "PDF Files (*.pdf)"
                            
                            self._add_action_bubble("file_chooser", save_args)
                        else:
                            logger.error("Main window not found, cannot access PDF processor")
                            self._add_message_bubble("assistant", "\n❌ 无法访问PDF处理器\n")
                        continue

                    # 特殊处理password工具 - 在对话中显示密码输入UI
                    if tool_name == "password":
                        try:
                            self._add_action_bubble("password", arguments)
                        except Exception as e:
                            logger.error(f"Error adding password bubble: {e}", exc_info=True)
                            self._add_message_bubble("assistant", f"\n❌ 无法显示密码输入界面: {str(e)}\n")
                        continue

                    # 对于其他工具，异步执行
                    logger.info(f"Executing general tool: {tool_name}")
                    loop = asyncio.get_event_loop()
                    try:
                        if loop.is_running():
                            result = asyncio.run_coroutine_threadsafe(
                                self._execute_tool(tool_name, arguments), loop
                            ).result(timeout=30)
                        else:
                            result = loop.run_until_complete(self._execute_tool(tool_name, arguments))
                    except RuntimeError:
                        result = asyncio.run(self._execute_tool(tool_name, arguments))

                    # 将工具执行结果添加到消息历史
                    result_content = json.dumps(result, ensure_ascii=False)
                    self._messages.append(LLMMessage(
                        role="user",
                        content=f"工具 {tool_name} 执行结果: {result_content}"
                    ))

                    # 显示执行结果
                    result_msg = f"\n✅ 工具 [{tool_name}]\n"
                    if result.get('success'):
                        result_msg += f"成功: {result.get('message', '执行完成')}\n"
                    else:
                        result_msg += f"失败: {result.get('error', '未知错误')}\n"
                    self._add_message_bubble("assistant", result_msg)

                except Exception as e:
                    logger.error(f"Error processing tool call {tool_name}: {e}", exc_info=True)
                    self._add_message_bubble("assistant", f"\n❌ 工具执行错误: {str(e)}\n")

        except Exception as e:
            logger.error(f"Error in _handle_tool_calls: {e}", exc_info=True)
            self._add_message_bubble("assistant", f"\n❌ 处理工具调用时出错: {str(e)}\n")

    async def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """异步执行工具"""
        if self._tool_manager:
            return await self._tool_manager.execute_tool(tool_name, arguments)
        else:
            logger.error("Tool manager not available")
            return {"success": False, "error": "Tool manager not available"}

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
