import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("check_agent_config_links.py")
spec = importlib.util.spec_from_file_location("links", SCRIPT)
links = importlib.util.module_from_spec(spec)
spec.loader.exec_module(links)


class CheckAgentConfigLinks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.canon = self.root / "canonical.md"
        self.canon.write_text("# canon\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _paths(self):
        link = self.root / "host" / "CLAUDE.md"
        return [("~/replaced", "~/canonical")]

    def _check(self, pairs):
        # expand maps the fake "~/" names onto the temp tree
        def expand(p):
            return str(self.root / p[2:])

        return links.check(pairs, expand=expand)

    def test_healthy_link_is_silent(self):
        host = self.root / "host"
        host.mkdir()
        (host / "CLAUDE.md").symlink_to(self.canon)
        self.assertEqual(self._check([("~/host/CLAUDE.md", "~/canonical.md")]), [])

    def test_regular_file_is_reported(self):
        host = self.root / "host"
        host.mkdir()
        (host / "CLAUDE.md").write_text("# diverged\n", encoding="utf-8")
        problems = self._check([("~/host/CLAUDE.md", "~/canonical.md")])
        self.assertEqual(len(problems), 1)
        self.assertIn("replaced by a regular file", problems[0])

    def test_dangling_link_is_reported(self):
        host = self.root / "host"
        host.mkdir()
        (host / "CLAUDE.md").symlink_to(self.root / "gone.md")
        problems = self._check([("~/host/CLAUDE.md", "~/canonical.md")])
        self.assertEqual(len(problems), 1)
        self.assertIn("dangling symlink", problems[0])

    def test_missing_canonical_is_reported(self):
        self.canon.unlink()
        host = self.root / "host"
        host.mkdir()
        (host / "CLAUDE.md").symlink_to(self.canon)
        problems = self._check([("~/host/CLAUDE.md", "~/canonical.md")])
        self.assertEqual(len(problems), 1)
        self.assertIn("is missing", problems[0])

    def test_link_to_wrong_target_is_reported(self):
        other = self.root / "other.md"
        other.write_text("# other\n", encoding="utf-8")
        host = self.root / "host"
        host.mkdir()
        (host / "CLAUDE.md").symlink_to(other)
        problems = self._check([("~/host/CLAUDE.md", "~/canonical.md")])
        self.assertEqual(len(problems), 1)
        self.assertIn("expected", problems[0])

    def test_absent_file_is_reported(self):
        (self.root / "host").mkdir()
        problems = self._check([("~/host/CLAUDE.md", "~/canonical.md")])
        self.assertEqual(len(problems), 1)
        self.assertIn("absent", problems[0])

    def test_repair_command_names_both_sides(self):
        cmd = links.repair_command([("~/.claude/CLAUDE.md", "~/.codex/AGENTS.md")])
        self.assertEqual(cmd, "ln -sf ~/.codex/AGENTS.md ~/.claude/CLAUDE.md")

    def test_main_emits_json_system_message(self):
        # Async hooks drop plain stdout; the warning must be a JSON systemMessage.
        original = links.check
        links.check = lambda: ["~/.claude/CLAUDE.md: replaced by a regular file"]
        try:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                self.assertEqual(links.main(), 0)
        finally:
            links.check = original
        payload = json.loads(buf.getvalue())
        self.assertIn("AGENT CONFIG LINKS BROKEN", payload["systemMessage"])
        self.assertIsInstance(payload["systemMessage"], str)

    def test_main_is_silent_when_healthy(self):
        original = links.check
        links.check = lambda: []
        try:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                links.main()
        finally:
            links.check = original
        self.assertEqual(buf.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
