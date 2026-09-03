import json
from pathlib import Path
from typing import Any


class Memory:
    """Manages chat message history for LLM interactions and logs conversation to a formatted JSON file."""

    def __init__(
        self,
        system_prompt: str | None = None,
        initial_messages: list[dict[str, Any] | Any] | None = None,
        file: str | Path | None = "conversation.json",
    ) -> None:
        """Initialize Memory with an optional system prompt, initial messages list, and log file."""
        self._file: Path | None = Path(file) if file else None
        if self._file and self._file.parent:
            self._file.parent.mkdir(parents=True, exist_ok=True)

        self._messages: list[dict[str, Any] | Any] = []
        if not self.load_memory():
            if system_prompt:
                self.add_system(system_prompt)
            if initial_messages:
                for msg in initial_messages:
                    self.add_message(msg)

    def load_memory(self, file_path: str | Path | None = None) -> bool:
        """Load messages from a log file into memory. Returns True if loaded successfully."""
        target_file = Path(file_path) if file_path else self._file
        if not target_file or not target_file.is_file():
            return False
        try:
            with open(target_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list) and len(data) > 0:
                self._messages = data
                return True
        except Exception:
            pass
        return False

    @property
    def file(self) -> Path | None:
        """Return the current log file path."""
        return self._file

    @file.setter
    def file(self, value: str | Path | None) -> None:
        """Set or change the log file path."""
        self._file = Path(value) if value else None
        if self._file and self._file.parent:
            self._file.parent.mkdir(parents=True, exist_ok=True)
        self._save_memory()

    @property
    def messages(self) -> list[dict[str, Any] | Any]:
        """Return the list of stored messages."""
        return self._messages

    def _message_to_dict(self, message: Any) -> dict[str, Any]:
        """Convert a message object or dictionary to a dictionary representation."""
        if isinstance(message, dict):
            return message
        if hasattr(message, "model_dump") and callable(message.model_dump):
            return message.model_dump()
        if hasattr(message, "dict") and callable(message.dict):
            return message.dict()
        if hasattr(message, "__dict__"):
            return {k: v for k, v in message.__dict__.items() if not k.startswith("_")}
        role = getattr(message, "role", "unknown")
        content = getattr(message, "content", str(message))
        return {"role": role, "content": content}

    def _save_memory(self) -> None:
        """Write all messages to the log file as a formatted JSON array."""
        if not self._file:
            return
        try:
            data = [self._message_to_dict(msg) for msg in self._messages]
            formatted_json = json.dumps(data, indent=2, ensure_ascii=False, default=str)
            with open(self._file, "w", encoding="utf-8") as f:
                f.write(formatted_json + "\n")
        except Exception:
            pass

    def add_message(self, message: dict[str, Any] | Any) -> None:
        """Add a raw message object or dictionary to memory and log it."""
        self._messages.append(message)
        self._save_memory()

    def add_system(self, content: str) -> None:
        """Add a system message to memory."""
        self.add_message({"role": "system", "content": content})

    def add_user(self, content: str) -> None:
        """Add a user message to memory."""
        self.add_message({"role": "user", "content": content})

    def add_assistant(
        self, content: str | None = None, tool_calls: list[Any] | None = None
    ) -> None:
        """Add an assistant response message to memory."""
        msg: dict[str, Any] = {"role": "assistant", "content": content}
        if tool_calls is not None:
            msg["tool_calls"] = tool_calls
        self.add_message(msg)

    def add_tool_result(self, tool_call_id: str, content: str) -> None:
        """Add a tool result message to memory."""
        self.add_message({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": content,
        })

    # Aliases for convenience
    add_system_message = add_system
    add_user_message = add_user
    add_assistant_message = add_assistant
    add_tool_message = add_tool_result

    def get_messages(self) -> list[dict[str, Any] | Any]:
        """Return a copy of all stored messages."""
        return list(self._messages)

    def clear(self, keep_system: bool = True) -> None:
        """Clear memory. If keep_system is True, preserves system messages."""
        if keep_system:
            self._messages = [
                msg for msg in self._messages
                if (isinstance(msg, dict) and msg.get("role") == "system")
                or getattr(msg, "role", None) == "system"
            ]
        else:
            self._messages.clear()
        self._save_memory()

    def append(self, message: dict[str, Any] | Any) -> None:
        """Append a message (supports list-like append syntax)."""
        self.add_message(message)

    def __len__(self) -> int:
        return len(self._messages)

    def __getitem__(self, index: int) -> dict[str, Any] | Any:
        return self._messages[index]

    def __iter__(self):
        return iter(self._messages)

    def __repr__(self) -> str:
        return f"Memory(messages_count={len(self._messages)}, log_file={self._file})"
