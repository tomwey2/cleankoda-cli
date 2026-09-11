import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from cleankoda.tools import ToolRegistry


class TestToolRegistryClass(unittest.TestCase):

    def test_tool_registry_workspace_binding(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ws_path = Path(tmpdir).resolve()
            registry = ToolRegistry(workspace=ws_path, sandbox_image=None)

            self.assertEqual(registry.workspace, ws_path)
            self.assertEqual(registry.fs.workspace_root, ws_path)
            self.assertEqual(registry.sandbox_manager.workspace_path, ws_path)

    def test_tool_registry_file_operations(self):
        async def _test():
            with tempfile.TemporaryDirectory() as tmpdir:
                ws_path = Path(tmpdir).resolve()
                registry = ToolRegistry(workspace=ws_path, sandbox_image=None)

                # Test write_file
                mock_call_write = MagicMock()
                mock_call_write.function.name = "write_file"
                mock_call_write.function.arguments = '{"path": "hello.txt", "content": "Hello World"}'

                res_write = await registry.run_tool(mock_call_write)
                self.assertIn("Successfully wrote", res_write)

                # Test read_file
                mock_call_read = MagicMock()
                mock_call_read.function.name = "read_file"
                mock_call_read.function.arguments = '{"path": "hello.txt"}'

                res_read = await registry.run_tool(mock_call_read)
                self.assertEqual(res_read, "Hello World")

                # Test list_dir
                mock_call_list = MagicMock()
                mock_call_list.function.name = "list_dir"
                mock_call_list.function.arguments = '{"path": "."}'

                res_list = await registry.run_tool(mock_call_list)
                self.assertIn("hello.txt", res_list)

        asyncio.run(_test())

    def test_tool_registry_sandbox_status(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ws_path = Path(tmpdir).resolve()
            registry = ToolRegistry(workspace=ws_path, sandbox_image=None)
            self.assertEqual(registry.get_sandbox_status(), "host")


if __name__ == "__main__":
    unittest.main()
