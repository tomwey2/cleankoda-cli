import asyncio
from pathlib import Path

class JailedFilesystem:
    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root.resolve()

    def _resolve_safe_path(self, relative_path: str | Path) -> Path:
        target = (self.workspace_root / relative_path).resolve()
        try:
            target.relative_to(self.workspace_root)
        except ValueError:
            raise PermissionError(f"Access Denied: '{relative_path}' points outside workspace root.")
        return target

    # --- Synchrone I/O-Worker ---
    def _read_sync(self, path: str, max_chars: int = 50_000) -> str:
        safe_path = self._resolve_safe_path(path)
        if not safe_path.exists():
            return f"Error: File '{path}' does not exist."
        if safe_path.is_dir():
            return f"Error: '{path}' is a directory, not a file."

        content = safe_path.read_text(encoding="utf-8", errors="replace")
        if len(content) > max_chars:
            return content[:max_chars] + f"\n\n[... Truncated after {max_chars} characters ...]"
        return content

    def _write_sync(self, path: str, content: str) -> str:
        safe_path = self._resolve_safe_path(path)
        safe_path.parent.mkdir(parents=True, exist_ok=True)
        safe_path.write_text(content, encoding="utf-8")
        return f"Successfully wrote {len(content)} characters to '{path}'."

    def _list_sync(self, path: str = ".") -> str:
        safe_path = self._resolve_safe_path(path)
        if not safe_path.exists():
            return f"Error: Directory '{path}' does not exist."
        if not safe_path.is_dir():
            return f"Error: '{path}' is a file, not a directory."

        items = []
        for item in sorted(safe_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
            prefix = "[DIR] " if item.is_dir() else "      "
            items.append(f"{prefix}{item.name}")
        return "\n".join(items) if items else "(Empty directory)"

    # --- Öffentliche asynchrone Schnittstellen ---
    async def read_file(self, path: str) -> str:
        return await asyncio.to_thread(self._read_sync, path)

    async def write_file(self, path: str, content: str) -> str:
        return await asyncio.to_thread(self._write_sync, path, content)

    async def list_dir(self, path: str = ".") -> str:
        return await asyncio.to_thread(self._list_sync, path)
