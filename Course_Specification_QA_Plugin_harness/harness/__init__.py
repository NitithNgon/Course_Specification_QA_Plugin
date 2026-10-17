"""Course Specification QA harness: the Harness/ building blocks plus QA tools (M6), loop (M8)."""
from .config import load_config, Profile, Config
from .llm_client import LLMClient, ChatResult, LLMError, LLMConnectionError, ModelNotFoundError
from .prompts import PromptManager, build_messages
from .tools import tool, tool_defs, TOOLS
from .executor import execute, tool_message, ok, err
from .logger import JsonlLogger, new_run_id
from .harness import Harness

__all__ = [
    "load_config", "Profile", "Config", "LLMClient", "ChatResult", "LLMError",
    "LLMConnectionError", "ModelNotFoundError", "PromptManager", "build_messages", "tool",
    "tool_defs", "TOOLS", "execute", "tool_message", "ok", "err", "JsonlLogger", "new_run_id",
    "Harness",
]
