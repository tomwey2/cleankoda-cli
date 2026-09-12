import tempfile
import unittest
from pathlib import Path

from cleankoda.sandbox import Sandbox


class TestSandboxClass(unittest.TestCase):

    def test_sandbox_workspace_binding(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ws_path = Path(tmpdir).resolve()
            sandbox = Sandbox(default_image_id=None, workspace=ws_path)

            self.assertEqual(sandbox.workspace, ws_path)
            self.assertEqual(sandbox.current_env.workspace_path, ws_path)

    def test_sandbox_status(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ws_path = Path(tmpdir).resolve()
            sandbox = Sandbox(default_image_id=None, workspace=ws_path)
            self.assertEqual(sandbox.get_sandbox_image().id, "host")


if __name__ == "__main__":
    unittest.main()
