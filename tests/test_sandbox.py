import asyncio
import json
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

from cleankoda.sandbox import (
    DockerSandbox,
    ExecutionEnvironment,
    HostSandbox,
    SandboxManager,
)
from cleankoda.tools.bash import BashCommand


class TestSandboxPackage(unittest.TestCase):

    def setUp(self):
        self.workspace = Path.cwd()

    def test_host_sandbox_execution(self):
        host_env = HostSandbox(workspace_path=self.workspace)

        async def _run():
            res = await host_env.run("echo 'Hello World'")
            self.assertTrue(res["success"])
            self.assertEqual(res["exit_code"], 0)
            self.assertEqual(res["output"], "Hello World")

        asyncio.run(_run())

    def test_host_sandbox_truncation(self):
        host_env = HostSandbox(workspace_path=self.workspace, max_output_chars=50)

        async def _run():
            res = await host_env.run("python3 -c \"print('A' * 100)\"")
            self.assertTrue(res["success"])
            self.assertIn("[... 50 Zeichen gekürzt / Output Truncated ...]", res["output"])

        asyncio.run(_run())

    @patch("cleankoda.sandbox.manager.DockerSandbox")
    def test_sandbox_manager_switching(self, mock_docker_sandbox):
        def _make_mock(workspace_path, image):
            mock = MagicMock()
            mock.image = image
            return mock

        mock_docker_sandbox.side_effect = _make_mock

        manager = SandboxManager(workspace_path=self.workspace, default_image=None)
        self.assertIsInstance(manager.current_env, HostSandbox)
        self.assertEqual(manager.get_status(), "host")

        status_msg = manager.switch_environment("python:3.11-slim")
        self.assertIn("Sandbox aktiv", status_msg)
        self.assertEqual(manager.get_status(), "python:3.11-slim")

        status_msg_off = manager.switch_environment(None)
        self.assertIn("Sandbox deaktiviert", status_msg_off)
        self.assertEqual(manager.get_status(), "host")

    def test_bash_command_tool(self):
        manager = SandboxManager(workspace_path=self.workspace, default_image=None)
        bash_tool = BashCommand(sandbox_manager=manager)

        async def _run():
            output_json = await bash_tool.execute("echo 'Tool Test'")
            data = json.loads(output_json)
            self.assertTrue(data["success"])
            self.assertEqual(data["output"], "Tool Test")

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
