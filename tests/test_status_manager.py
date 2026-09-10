import unittest
from cleankoda.statusline import StatusLine


class TestStatusManager(unittest.TestCase):

    def test_empty_status_manager(self):
        sm = StatusLine()
        self.assertEqual(sm.get_combined_status(), "")

    def test_set_and_get_combined_status(self):
        sm = StatusLine()
        sm.set("sandbox", "Sandbox: Startet (docker:latest)...")
        self.assertEqual(sm.get_combined_status(), "Sandbox: Startet (docker:latest)...")

        sm.set("llm", "LLM Cold Start: Versuch 1/10 (10s gewartet)")
        self.assertEqual(
            sm.get_combined_status(),
            "Sandbox: Startet (docker:latest)... | LLM Cold Start: Versuch 1/10 (10s gewartet)",
        )

    def test_clear_status(self):
        sm = StatusLine()
        sm.set("sandbox", "Sandbox active")
        sm.set("tool", "Führe Tool aus: run_bash...")
        sm.clear("sandbox")
        self.assertEqual(sm.get_combined_status(), "Führe Tool aus: run_bash...")

        sm.clear("tool")
        self.assertEqual(sm.get_combined_status(), "")

    def test_observer_on_change(self):
        sm = StatusLine()
        notifications = 0

        def on_change_cb():
            nonlocal notifications
            notifications += 1

        sm.on_change = on_change_cb

        # Initial set triggers notification
        sm.set("sandbox", "Starting")
        self.assertEqual(notifications, 1)

        # Updating with same value does NOT trigger notification
        sm.set("sandbox", "Starting")
        self.assertEqual(notifications, 1)

        # Updating with new value triggers notification
        sm.set("sandbox", "Ready")
        self.assertEqual(notifications, 2)

        # Clearing existing slot triggers notification
        sm.clear("sandbox")
        self.assertEqual(notifications, 3)

        # Clearing non-existent slot does NOT trigger notification
        sm.clear("sandbox")
        self.assertEqual(notifications, 3)

    def test_observer_on_change_with_argument(self):
        statuses_received = []

        def on_change_cb(status: str):
            statuses_received.append(status)

        sm = StatusLine(on_change=on_change_cb)
        sm.set("tool", "Execute tool: list_files...")
        self.assertEqual(statuses_received, ["Execute tool: list_files..."])

        sm.clear("tool")
        self.assertEqual(statuses_received, ["Execute tool: list_files...", ""])


if __name__ == "__main__":
    unittest.main()
