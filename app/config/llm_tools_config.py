"""
LLM工具配置
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional
from app.utils.logger import get_logger

logger = get_logger(__name__)


class LLMToolConfigManager:
    """LLM工具配置管理器"""

    def __init__(self, config_file: Optional[str] = None):
        """
        初始化配置管理器

        Args:
            config_file: 配置文件路径
        """
        if config_file is None:
            project_root = Path(__file__).parent.parent
            config_dir = project_root / "config"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_file = config_dir / "llm_tools_config.json"

        self.config_file = Path(config_file)
        self._config: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        """加载配置文件"""
        if not self.config_file.exists():
            self._create_default_config()
            return

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
        except Exception as e:
            logger.error(f"Error loading tool config: {e}", exc_info=True)
            self._create_default_config()

    def _create_default_config(self) -> None:
        """创建默认配置"""
        self._config = {
            "tools": {
                "open_pdf": {
                    "enabled": True,
                    "require_user_confirmation": True,
                    "auto_fill_params": {
                        "file_path": "last_used_path"
                    }
                },
                "split_pdf": {
                    "enabled": True,
                    "require_user_confirmation": True,
                    "default_split_mode": "pages"
                },
                "ocr_pdf": {
                    "enabled": True,
                    "require_user_confirmation": True,
                    "default_language": "chi_sim+eng"
                },
                "merge_pdf": {
                    "enabled": True,
                    "require_user_confirmation": True
                },
                "encrypt_pdf": {
                    "enabled": True,
                    "require_user_confirmation": True
                }
            },
            "interaction": {
                "auto_show_ui": True,
                "remember_user_choices": True,
                "max_interaction_attempts": 3
            }
        }
        self._save_config()

    def _save_config(self) -> None:
        """保存配置文件"""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving tool config: {e}", exc_info=True)

    def get_tool_config(self, tool_name: str) -> Dict[str, Any]:
        """
        获取工具配置

        Args:
            tool_name: 工具名称

        Returns:
            工具配置字典
        """
        return self._config.get("tools", {}).get(tool_name, {})

    def set_tool_config(self, tool_name: str, config: Dict[str, Any]) -> None:
        """
        设置工具配置

        Args:
            tool_name: 工具名称
            config: 配置字典
        """
        if "tools" not in self._config:
            self._config["tools"] = {}

        self._config["tools"][tool_name] = config
        self._save_config()

    def is_tool_enabled(self, tool_name: str) -> bool:
        """
        检查工具是否启用

        Args:
            tool_name: 工具名称

        Returns:
            是否启用
        """
        return self.get_tool_config(tool_name).get("enabled", True)

    def set_tool_enabled(self, tool_name: str, enabled: bool) -> None:
        """
        设置工具启用状态

        Args:
            tool_name: 工具名称
            enabled: 是否启用
        """
        tool_config = self.get_tool_config(tool_name)
        tool_config["enabled"] = enabled
        self.set_tool_config(tool_name, tool_config)

    def require_user_confirmation(self, tool_name: str) -> bool:
        """
        检查工具是否需要用户确认

        Args:
            tool_name: 工具名称

        Returns:
            是否需要确认
        """
        return self.get_tool_config(tool_name).get("require_user_confirmation", True)

    def get_interaction_config(self) -> Dict[str, Any]:
        """获取交互配置"""
        return self._config.get("interaction", {})

    def set_interaction_config(self, config: Dict[str, Any]) -> None:
        """
        设置交互配置

        Args:
            config: 配置字典
        """
        self._config["interaction"] = config
        self._save_config()

    def get_config(self) -> Dict[str, Any]:
        """获取完整配置"""
        return self._config.copy()
