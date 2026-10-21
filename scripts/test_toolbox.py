#!/usr/bin/env python3
"""Offline tests for host adapters; all files and host directories are temporary."""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import toolbox


class ToolboxTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        (self.repo / "demo").mkdir()
        (self.repo / "demo/SKILL.md").write_text("---\nname: demo\ndescription: demo\n---\n")
        self.mcp = self.repo / "mcp/echo-server"
        self.mcp.mkdir(parents=True)
        self.server = {"type": "stdio", "command": "echo", "args": ["hello"]}
        self.write_server(self.server)
        self.plugin = self.repo / "plugins/bridge"
        (self.plugin / ".codex-plugin").mkdir(parents=True)
        (self.plugin / ".codex-plugin/plugin.json").write_text('{"name":"bridge"}')
        (self.repo / ".agents/plugins").mkdir(parents=True)
        (self.repo / ".agents/plugins/marketplace.json").write_text(json.dumps({
            "name": "test-local", "plugins": [{"name": "bridge", "source": {"path": "./plugins/bridge"}}]
        }))
        (self.repo / "skills.json").write_text(json.dumps({
            "skills": [{"name": "demo"}], "mcps": [{"name": "echo-server"}], "plugins": [{"name": "bridge"}]
        }))
        self.host = self.root / "skills"
        self.patches = [mock.patch.object(toolbox, "REPO", self.repo),
                        mock.patch.object(toolbox.install_skills, "REPO", self.repo),
                        mock.patch.object(toolbox.install_skills, "HOSTS", {
                            "codex": str(self.host), "claude": str(self.root / "claude-skills"),
                            "omp": str(self.root / "omp-skills"), "pi": str(self.root / "pi-skills"),
                            "agents": str(self.root / "shared-skills"),
                        })]
        for patch in self.patches:
            patch.start()

    def tearDown(self):
        for patch in reversed(self.patches):
            patch.stop()
        self.tmp.cleanup()

    def write_server(self, server):
        (self.mcp / "mcp.json").write_text(json.dumps({"mcpServers": {"echo-server": server}}))

    def test_multi_skill_host_selection_and_shared_scope(self):
        code = toolbox.main(["install", "--skill", "demo", "--host", "codex", "--host", "agents"])
        self.assertEqual(code, 0)
        self.assertTrue((self.host / "demo").is_symlink())
        self.assertTrue((self.root / "shared-skills/demo").is_symlink())
        self.assertFalse((self.root / "claude-skills").exists())

    def test_no_host_and_dry_run_never_mutate(self):
        self.assertEqual(toolbox.main(["install", "--skill", "demo"]), 2)
        self.assertEqual(toolbox.main(["install", "--skill", "demo", "--mcp", "echo-server", "--host", "codex", "--dry-run"]), 0)
        self.assertFalse(self.host.exists())

    def test_unsupported_plugin_is_checked_before_skill_install(self):
        self.assertEqual(toolbox.main(["install", "--skill", "demo", "--plugin", "bridge", "--host", "claude"]), 2)
        self.assertFalse((self.root / "claude-skills").exists())

    def test_shared_scope_does_not_claim_mcp_support(self):
        self.assertEqual(toolbox.main(["install", "--mcp", "echo-server", "--host", "agents", "--dry-run"]), 2)

    def test_invalid_mcp_fields_are_not_silently_dropped(self):
        self.write_server({**self.server, "unexpected": True})
        self.assertEqual(toolbox.main(["install", "--mcp", "echo-server", "--host", "codex", "--dry-run"]), 2)

    def test_native_stdio_and_http_protocols(self):
        commands = toolbox.mcp_commands("codex", "demo", self.server)
        self.assertEqual(commands, [["codex", "mcp", "add", "demo", "--", "echo", "hello"]])
        http = {"type": "http", "url": "https://example.invalid/mcp", "bearer_token_env_var": "TEST_TOKEN"}
        for host in ("codex", "pi"):
            self.assertIn("--bearer-token-env-var", toolbox.mcp_commands(host, "demo", http)[0])
        command = toolbox.mcp_commands("claude", "demo", http)[0]
        self.assertEqual(command[:6], ["claude", "mcp", "add-json", "--scope", "user", "demo"])
        self.assertEqual(json.loads(command[6])["headers"]["Authorization"], "Bearer ${TEST_TOKEN}")

    def test_unset_secret_is_preflight_error(self):
        self.write_server({**self.server, "env": {"TOKEN": "${TOOLBOX_TEST_UNSET}"}})
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(toolbox.shutil, "which", return_value="cli"), \
                mock.patch.object(toolbox, "mcp_exists", return_value=False), mock.patch.object(toolbox, "run_commands") as run:
            self.assertEqual(toolbox.main(["install", "--skill", "demo", "--mcp", "echo-server", "--host", "codex"]), 2)
        run.assert_not_called()
        self.assertFalse(self.host.exists())

    def test_existing_mcp_is_not_overwritten(self):
        with mock.patch.object(toolbox.shutil, "which", return_value="cli"), \
                mock.patch.object(toolbox, "mcp_exists", return_value=True), mock.patch.object(toolbox, "run_commands") as run:
            self.assertEqual(toolbox.main(["install", "--mcp", "echo-server", "--host", "codex"]), 2)
        run.assert_not_called()

    def test_native_failure_does_not_print_credentials(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), mock.patch.object(toolbox.subprocess, "run", return_value=mock.Mock(returncode=1)):
            with self.assertRaises(ValueError) as error:
                toolbox.run_commands([["codex", "mcp", "add", "server", "--env", "TOKEN=private-token"]])
        self.assertNotIn("private-token", out.getvalue() + str(error.exception))

    def test_omp_merge_preserves_unrelated_configuration(self):
        root = self.root / "omp-agent"
        root.mkdir()
        path = root / "mcp.json"
        original = {"extra": 1, "mcpServers": {"existing": {"command": "keep"}}}
        path.write_text(json.dumps(original))
        with mock.patch.dict(os.environ, {"PI_CODING_AGENT_DIR": str(root)}):
            self.assertEqual(toolbox.main(["install", "--mcp", "echo-server", "--host", "omp"]), 0)
            data = json.loads(path.read_text())
            self.assertEqual(data["extra"], 1)
            self.assertEqual(data["mcpServers"]["existing"], original["mcpServers"]["existing"])
            self.assertEqual(toolbox.main(["uninstall", "--mcp", "echo-server", "--host", "omp", "--dry-run"]), 0)
            self.assertIn("echo-server", json.loads(path.read_text())["mcpServers"])
            self.assertEqual(toolbox.main(["uninstall", "--mcp", "echo-server", "--host", "omp"]), 0)
        self.assertEqual(json.loads(path.read_text()), original)

    def test_plugin_uses_native_marketplace(self):
        commands = toolbox.plugin_commands(self.repo, self.plugin, "codex", "bridge", False)
        self.assertEqual(commands[-1], ["codex", "plugin", "add", "bridge@test-local"])
        (self.plugin / ".codex-plugin/plugin.json").unlink()
        (self.plugin / "package.json").write_text('{"name":"test-bridge","pi":{}}')
        self.assertEqual(toolbox.plugin_commands(self.repo, self.plugin, "pi", "bridge", False), [["pi", "install", str(self.plugin)]])
        self.assertEqual(toolbox.plugin_commands(self.repo, self.plugin, "omp", "bridge", True), [["omp", "plugin", "uninstall", "test-bridge"]])

    def test_config_path_overrides(self):
        with mock.patch.dict(os.environ, {"PI_CONFIG_DIR": str(self.root / "omp")}, clear=True):
            self.assertEqual(toolbox.omp_config_path(), self.root / "omp/agent/mcp.json")

    def test_omp_rejects_manifest_without_native_package(self):
        (self.plugin / "plugin.json").write_text('{"name":"bridge"}')
        self.assertEqual(toolbox.main(["install", "--skill", "demo", "--plugin", "bridge", "--host", "omp", "--dry-run"]), 2)
        self.assertFalse((self.root / "omp-skills").exists())

    def test_updates_default_to_all_tracked_kinds(self):
        data = {key: [{"name": "example", "upstream": {"type": "github"}}]
                for key in ("skills", "plugins", "mcps")}
        (self.repo / "skills.json").write_text(json.dumps(data))
        with mock.patch.object(toolbox.sync_upstream, "main", return_value=0) as run:
            self.assertEqual(toolbox.main(["update", "--apply"]), 0)
            self.assertEqual([call.args[0][call.args[0].index('--kind') + 1] for call in run.call_args_list], ["skill", "plugin", "mcp"])

    def test_equals_options_do_not_broaden_update_scope(self):
        with mock.patch.object(toolbox.sync_upstream, "main", return_value=0) as run:
            self.assertEqual(toolbox.main(["update", "--kind=plugin", "--apply"]), 0)
            run.assert_called_once_with(["update", "--kind=plugin", "--apply"])
        with mock.patch.object(toolbox.sync_upstream, "main", return_value=0) as run:
            self.assertEqual(toolbox.main(["update", "--skill=demo", "--apply"]), 0)
            run.assert_called_once_with(["update", "--skill=demo", "--apply"])
        other = self.root / "other"
        other.mkdir()
        (other / "skills.json").write_text('{"mcps":[{"name":"example","upstream":{"type":"github"}}]}')
        with mock.patch.object(toolbox.sync_upstream, "main", return_value=0) as run:
            self.assertEqual(toolbox.main(["check", f"--repo={other}"]), 0)
            self.assertEqual(run.call_args.args[0], ["check", "--repo", str(other), "--kind", "mcp", "--component", "example"])

    def test_runtime_preflight_respects_server_path(self):
        binary = self.root / "bin"
        binary.mkdir()
        executable = binary / "toolbox-test-runner"
        executable.write_text('#!/bin/sh\nexit 0\n')
        executable.chmod(0o755)
        self.write_server({"command": executable.name, "env": {"PATH": str(binary)}})
        native_which = toolbox.shutil.which

        def which(command, **kwargs):
            return "cli" if command == "codex" else native_which(command, **kwargs)

        with mock.patch.object(toolbox.shutil, "which", side_effect=which), \
                mock.patch.object(toolbox, "mcp_exists", return_value=False), mock.patch.object(toolbox, "run_commands") as run:
            self.assertEqual(toolbox.main(["install", "--mcp", "echo-server", "--host", "codex"]), 0)
        run.assert_called_once()

    def test_invalid_omp_config_remains_unchanged(self):
        root = self.root / "invalid-omp"
        root.mkdir()
        path = root / "mcp.json"
        path.write_text('[]')
        with mock.patch.dict(os.environ, {"PI_CODING_AGENT_DIR": str(root)}):
            self.assertEqual(toolbox.main(["install", "--mcp", "echo-server", "--host", "omp"]), 2)
        self.assertEqual(path.read_text(), '[]')


if __name__ == "__main__":
    unittest.main()
