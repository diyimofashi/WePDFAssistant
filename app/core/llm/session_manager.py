"""会话管理器 - 管理聊天会话和历史记录"""
import json
import os
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from app.core.llm.llm_plugin_interface import LLMMessage
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ChatSession:
    """聊天会话数据类"""
    session_id: str
    title: str
    messages: List[Dict[str, Any]]
    created_at: str
    updated_at: str
    plugin: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChatSession':
        """从字典创建实例"""
        return cls(**data)


class SessionManager:
    """会话管理器"""

    _instance: Optional["SessionManager"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """初始化会话管理器"""
        if self._initialized:
            return

        self._sessions: Dict[str, ChatSession] = {}
        self._current_session_id: Optional[str] = None
        self._storage_dir = os.path.join(os.path.expanduser("~"), ".pypdf", "sessions")
        self._initialized = True

        # 确保存储目录存在
        os.makedirs(self._storage_dir, exist_ok=True)

        # 加载保存的会话
        self._load_sessions()

        logger.info("SessionManager initialized")

    def _get_session_file_path(self, session_id: str) -> str:
        """获取会话文件路径"""
        return os.path.join(self._storage_dir, f"{session_id}.json")

    def _load_sessions(self):
        """加载所有会话"""
        try:
            if not os.path.exists(self._storage_dir):
                return

            for filename in os.listdir(self._storage_dir):
                if not filename.endswith('.json'):
                    continue

                file_path = os.path.join(self._storage_dir, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        session = ChatSession.from_dict(data)
                        self._sessions[session.session_id] = session
                except Exception as e:
                    logger.error(f"Error loading session from {filename}: {e}", exc_info=True)

            logger.info(f"Loaded {len(self._sessions)} sessions")

            # 如果有会话，设置当前会话为最后一个
            if self._sessions:
                self._current_session_id = list(self._sessions.keys())[-1]

        except Exception as e:
            logger.error(f"Error loading sessions: {e}", exc_info=True)

    def _save_session(self, session: ChatSession):
        """保存单个会话到文件"""
        try:
            file_path = self._get_session_file_path(session.session_id)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(session.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving session {session.session_id}: {e}", exc_info=True)

    def _delete_session_file(self, session_id: str):
        """删除会话文件"""
        try:
            file_path = self._get_session_file_path(session_id)
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            logger.error(f"Error deleting session file {session_id}: {e}", exc_info=True)

    def create_session(self, title: str = "新对话", plugin: Optional[str] = None) -> ChatSession:
        """
        创建新会话

        Args:
            title: 会话标题
            plugin: 使用的插件

        Returns:
            创建的会话对象
        """
        from uuid import uuid4

        session_id = str(uuid4())
        now = datetime.now().isoformat()

        session = ChatSession(
            session_id=session_id,
            title=title,
            messages=[],
            created_at=now,
            updated_at=now,
            plugin=plugin
        )

        self._sessions[session_id] = session
        self._current_session_id = session_id
        self._save_session(session)

        logger.info(f"Created new session: {session_id}")
        return session

    def delete_session(self, session_id: str) -> bool:
        """
        删除会话

        Args:
            session_id: 会话ID

        Returns:
            是否删除成功
        """
        if session_id not in self._sessions:
            return False

        del self._sessions[session_id]
        self._delete_session_file(session_id)

        # 如果删除的是当前会话，切换到另一个会话
        if self._current_session_id == session_id:
            if self._sessions:
                self._current_session_id = list(self._sessions.keys())[-1]
            else:
                self._current_session_id = None

        logger.info(f"Deleted session: {session_id}")
        return True

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """获取指定会话"""
        return self._sessions.get(session_id)

    def get_current_session(self) -> Optional[ChatSession]:
        """获取当前会话"""
        if self._current_session_id:
            return self._sessions.get(self._current_session_id)
        return None

    def set_current_session(self, session_id: str) -> bool:
        """
        设置当前会话

        Args:
            session_id: 会话ID

        Returns:
            是否设置成功
        """
        if session_id not in self._sessions:
            return False

        self._current_session_id = session_id
        logger.info(f"Switched to session: {session_id}")
        return True

    def get_all_sessions(self) -> List[ChatSession]:
        """获取所有会话，按更新时间排序"""
        sessions = list(self._sessions.values())
        sessions.sort(key=lambda x: x.updated_at, reverse=True)
        return sessions

    def update_session_title(self, session_id: str, title: str) -> bool:
        """
        更新会话标题

        Args:
            session_id: 会话ID
            title: 新标题

        Returns:
            是否更新成功
        """
        if session_id not in self._sessions:
            return False

        session = self._sessions[session_id]
        session.title = title
        session.updated_at = datetime.now().isoformat()
        self._save_session(session)
        return True

    def add_message(self, session_id: str, message: LLMMessage) -> bool:
        """
        添加消息到会话

        Args:
            session_id: 会话ID
            message: 消息对象

        Returns:
            是否添加成功
        """
        if session_id not in self._sessions:
            return False

        session = self._sessions[session_id]
        session.messages.append({
            "role": message.role,
            "content": message.content,
            "timestamp": message.timestamp
        })
        session.updated_at = datetime.now().isoformat()
        self._save_session(session)
        return True

    def update_session_plugin(self, session_id: str, plugin: str) -> bool:
        """
        更新会话的插件

        Args:
            session_id: 会话ID
            plugin: 插件名称

        Returns:
            是否更新成功
        """
        if session_id not in self._sessions:
            return False

        session = self._sessions[session_id]
        session.plugin = plugin
        session.updated_at = datetime.now().isoformat()
        self._save_session(session)
        return True

    def get_session_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """
        获取会话的所有消息

        Args:
            session_id: 会话ID

        Returns:
            消息列表
        """
        if session_id not in self._sessions:
            return []
        return self._sessions[session_id].messages.copy()

    def get_current_session_messages(self) -> List[Dict[str, Any]]:
        """获取当前会话的所有消息"""
        if self._current_session_id:
            return self.get_session_messages(self._current_session_id)
        return []

    def clear_current_session_messages(self) -> bool:
        """
        清空当前会话的消息

        Returns:
            是否清空成功
        """
        if not self._current_session_id:
            return False

        session = self._sessions[self._current_session_id]
        session.messages = []
        session.updated_at = datetime.now().isoformat()
        self._save_session(session)
        return True
