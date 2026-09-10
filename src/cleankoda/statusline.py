from collections.abc import Callable
from dataclasses import dataclass, field

@dataclass
class StatusManager:
    _slots: dict[str, str] = field(default_factory=dict)
    on_change: Callable[[str], None] | Callable[[], None] | None = None

    def set(self, source: str, message: str) -> None:
        """Sets or updates the status of a source and notifies observers."""
        if self._slots.get(source) != message:
            self._slots[source] = message
            self._notify()

    def clear(self, source: str) -> None:
        """Removes the status of a source."""
        if source in self._slots:
            del self._slots[source]
            self._notify()

    def get_combined_status(self) -> str:
        """Returns active status messages in a formatted, separated by ' | '."""
        if not self._slots:
            return ""
        return " | ".join(self._slots.values())

    def _notify(self) -> None:
        if self.on_change:
            combined = self.get_combined_status()
            try:
                self.on_change(combined)  # type: ignore[call-arg]
            except TypeError:
                self.on_change()  # type: ignore[call-arg]
