"""
LLM管理混入类
"""
from typing import Optional
from PyQt5.QtWidgets import QAction, QMenu, QDialog
from app.core.llm.llm_integration import LLMIntegration
from app.core.llm.memory.memory_manager import MemoryManager
from app.managers.llm_tool_manager import LLMToolManager
from app.managers.llm_plugin_manager import LLMPluginManager
from app.config.llm_plugin_config import LLMPluginConfigManager
from app.ui.llm_settings_dialog import LLMSettingsDialog
from app.utils.logger import get_logger

logger = get_logger(__name__)


class LLMManagerMixin:
    """LLM管理混入类"""

    def _init_llm_system(self):
        """初始化LLM系统"""
        try:
            # 创建配置管理器
            self._llm_config_manager = LLMPluginConfigManager()

            # 创建插件管理器
            self._llm_plugin_manager = LLMPluginManager()

            # 创建记忆管理器
            memory_config = self._llm_config_manager.get_memory_config()
            backend_type = memory_config.get("backend", "in_memory")

            if backend_type == "file":
                storage_path = memory_config.get("storage_path")
                self._llm_memory_manager = MemoryManager.create_file_backend(storage_path)
            else:
                max_size = memory_config.get("max_memory_size", 1000)
                self._llm_memory_manager = MemoryManager.create_in_memory(max_size)

            # 创建工具管理器
            self._llm_tool_manager = LLMToolManager()

            # 获取LLM集成实例并设置依赖
            self._llm_integration = LLMIntegration()
            self._llm_integration.set_plugin_manager(self._llm_plugin_manager)
            self._llm_integration.set_memory_manager(self._llm_memory_manager)
            self._llm_integration.set_tool_manager(self._llm_tool_manager)

            # 初始化LLM系统
            plugin_configs = self._llm_config_manager.get_all_plugin_configs()
            self._llm_integration.initialize_system(plugin_configs)

            logger.info("LLM system initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing LLM system: {e}", exc_info=True)

    def _setup_llm_menu(self):
        """设置LLM菜单"""
        try:
            # 查找或创建LLM菜单
            llm_menu = None
            for action in self.menuBar().actions():
                if action.text() == "LLM":
                    llm_menu = action.menu()
                    break

            if not llm_menu:
                llm_menu = self.menuBar().addMenu("LLM")

            # 添加菜单项
            self.llm_sidebar_action = QAction("显示AI助手", self)
            self.llm_sidebar_action.setCheckable(True)
            self.llm_sidebar_action.triggered.connect(self._toggle_llm_sidebar)
            llm_menu.addAction(self.llm_sidebar_action)

            settings_action = QAction("设置", self)
            settings_action.triggered.connect(self._show_llm_settings_dialog)
            llm_menu.addAction(settings_action)

            llm_menu.addSeparator()

            # 添加插件子菜单
            plugin_menu = llm_menu.addMenu("插件")

            for plugin_name in self._llm_integration.get_available_plugins():
                plugin_action = QAction(plugin_name, self)
                plugin_action.triggered.connect(lambda checked, name=plugin_name: self._switch_llm_plugin(name))
                plugin_menu.addAction(plugin_action)

            llm_menu.addSeparator()

            # 性能报告
            performance_action = QAction("性能报告", self)
            performance_action.triggered.connect(self._show_llm_performance_report)
            llm_menu.addAction(performance_action)

            logger.info("LLM menu setup completed")

        except Exception as e:
            logger.error(f"Error setting up LLM menu: {e}", exc_info=True)

    def _toggle_llm_sidebar(self):
        """切换LLM侧边栏显示"""
        try:
            if hasattr(self, 'llm_sidebar_dock'):
                if self.llm_sidebar_dock.isVisible():
                    self.llm_sidebar_dock.hide()
                    if hasattr(self, 'show_llm_sidebar'):
                        self.show_llm_sidebar = False
                else:
                    self.llm_sidebar_dock.show()
                    if hasattr(self, 'show_llm_sidebar'):
                        self.show_llm_sidebar = True
            else:
                logger.warning("LLM sidebar dock not found")
        except Exception as e:
            logger.error(f"Error toggling LLM sidebar: {e}", exc_info=True)

    def _show_llm_settings_dialog(self):
        """显示LLM设置对话框"""
        try:
            dialog = LLMSettingsDialog(self)
            if dialog.exec_() == QDialog.Accepted:
                # 重新初始化LLM系统以应用新配置
                self._init_llm_system()
        except Exception as e:
            logger.error(f"Error showing LLM settings dialog: {e}", exc_info=True)

    def _switch_llm_plugin(self, plugin_name: str):
        """切换LLM插件"""
        try:
            self._llm_integration.set_default_plugin(plugin_name)
            logger.info(f"Switched to LLM plugin: {plugin_name}")
        except Exception as e:
            logger.error(f"Error switching LLM plugin: {e}", exc_info=True)

    def _show_llm_performance_report(self):
        """显示LLM性能报告"""
        try:
            report = self._llm_integration.get_performance_report()

            # 构建报告文本
            report_text = f"""LLM性能报告
{'=' * 50}

总插件数: {report['total_plugins']}
总调用次数: {report['total_calls']}
总Token数: {report['total_tokens']}
总耗时: {report['total_time']:.2f}秒
总错误数: {report['total_errors']}
缓存大小: {report['cache_size']}/{report['cache_max_size']}

详细统计:
{'=' * 50}
"""

            for key, metrics in report['details'].items():
                report_text += f"""
插件: {key}
- 调用次数: {metrics['total_calls']}
- Token数: {metrics['total_tokens']}
- 耗时: {metrics['total_time']:.2f}秒
- 错误数: {metrics['error_count']}
- 平均Token/次: {metrics['average_tokens_per_call']:.2f}
- 平均耗时/次: {metrics['average_time_per_call']:.2f}秒
- 错误率: {metrics['error_rate']:.2%}
"""

            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.information(self, "LLM性能报告", report_text)

        except Exception as e:
            logger.error(f"Error showing performance report: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"获取性能报告失败: {str(e)}")

    def cleanup_llm_system(self):
        """清理LLM系统"""
        try:
            if hasattr(self, '_llm_integration'):
                # 清理所有插件
                for plugin_name in self._llm_integration.get_available_plugins():
                    plugin = self._llm_integration._plugins.get(plugin_name)
                    if plugin:
                        plugin.cleanup()

            logger.info("LLM system cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up LLM system: {e}", exc_info=True)
