import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from cleankoda.sandbox import Sandbox


class TestSandboxClass(unittest.TestCase):

    def test_sandbox_workspace_binding(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ws_path = Path(tmpdir).resolve()
            sandbox = Sandbox(workspace=ws_path, default_image=None)

            self.assertEqual(sandbox.workspace, ws_path)
            self.assertEqual(sandbox.fs.workspace_root, ws_path)
            self.assertEqual(sandbox.current_env.workspace_path, ws_path)

    def test_sandbox_file_operations(self):
        async def _test():
            with tempfile.TemporaryDirectory() as tmpdir:
                ws_path = Path(tmpdir).resolve()
                sandbox = Sandbox(workspace=ws_path, default_image=None)

                # Test write_file
                mock_call_write = MagicMock()
                mock_call_write.function.name = "write_file"
                mock_call_write.function.arguments = '{"path": "hello.txt", "content": "Hello Sandbox"}'

                res_write = await sandbox.run_tool(mock_call_write)
                self.assertIn("Successfully wrote", res_write)

                # Test read_file
                mock_call_read = MagicMock()
                mock_call_read.function.name = "read_file"
                mock_call_read.function.arguments = '{"path": "hello.txt"}'

                res_read = await sandbox.run_tool(mock_call_read)
                self.assertEqual(res_read, "Hello Sandbox")

                # Test list_dir
                mock_call_list = MagicMock()
                mock_call_list.function.name = "list_dir"
                mock_call_list.function.arguments = '{"path": "."}'

                res_list = await sandbox.run_tool(mock_call_list)
                self.assertIn("hello.txt", res_list)

        asyncio.run(_test())

    def test_sandbox_status(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ws_path = Path(tmpdir).resolve()
            sandbox = Sandbox(workspace=ws_path, default_image=None)
            self.assertEqual(sandbox.get_status(), "host")


if __name__ == "__main__":
    unittest.main()
