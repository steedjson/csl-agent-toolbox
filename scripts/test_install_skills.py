#!/usr/bin/env python3
"""Deterministic tests for scripts/install_skills.py (stdlib only).

Run: python3 scripts/test_install_skills.py
"""
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import install_skills as inst  # noqa: E402


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="install-test-"))
        self.repo = self.tmp / "repo"
        for name in ("alpha", "beta"):
            (self.repo / name).mkdir(parents=True)
            (self.repo / name / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: {name}\n---\nbody\n", encoding="utf-8")
        (self.repo / "README.md").write_text("not a skill\n", encoding="utf-8")
        (self.repo / "skills.json").write_text(
            '{"name":"t","skills":[{"name":"alpha","upstream":'
            '{"type":"github","repo":"o/r","ref":"abc1234"}}]}\n', encoding="utf-8")
        self.hosts = self.tmp / "hosts"
        self.host = self.hosts / "codex"
        self.host.mkdir(parents=True)
        self.patch = mock.patch.object(inst, "REPO", self.repo)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_cmd(self, *argv):
        with mock.patch.object(inst, "HOSTS", {"codex": str(self.host)}):
            with mock.patch.object(sys, "argv", ["install_skills.py", *argv]):
                return inst.main()

    def test_repo_skills_ignores_non_skill_dirs(self):
        self.assertEqual(sorted(inst.repo_skills()), ["alpha", "beta"])

    def test_link_creates_symlinks_to_repo(self):
        self.assertEqual(self.run_cmd("link"), 0)
        self.assertTrue((self.host / "alpha").is_symlink())
        self.assertTrue(inst.same_path(self.host / "alpha", self.repo / "alpha"))

    def test_link_is_idempotent(self):
        self.run_cmd("link")
        self.assertEqual(self.run_cmd("link"), 0)
        self.assertTrue((self.host / "alpha").is_symlink())

    def test_link_skips_foreign_symlink_without_prune(self):
        elsewhere = self.tmp / "old" / "alpha"
        elsewhere.mkdir(parents=True)
        (self.host / "alpha").symlink_to(elsewhere)
        self.run_cmd("link")
        self.assertTrue(inst.same_path(self.host / "alpha", elsewhere))

    def test_prune_retargets_foreign_symlink(self):
        elsewhere = self.tmp / "old" / "alpha"
        elsewhere.mkdir(parents=True)
        (self.host / "alpha").symlink_to(elsewhere)
        self.run_cmd("link", "--prune")
        self.assertTrue(inst.same_path(self.host / "alpha", self.repo / "alpha"))

    def test_real_directory_is_never_replaced(self):
        (self.host / "alpha").mkdir()
        (self.host / "alpha" / "SKILL.md").write_text("copy\n", encoding="utf-8")
        self.run_cmd("link", "--prune")
        self.assertFalse((self.host / "alpha").is_symlink())
        self.assertEqual((self.host / "alpha" / "SKILL.md").read_text(encoding="utf-8"), "copy\n")

    def test_dry_run_writes_nothing(self):
        self.run_cmd("link", "--dry-run")
        self.assertFalse((self.host / "alpha").exists())

    def test_unknown_skill_is_an_error(self):
        self.assertEqual(self.run_cmd("link", "--skill", "nope"), 2)

    def test_skill_filter_links_only_that_skill(self):
        self.run_cmd("link", "--skill", "alpha")
        self.assertTrue((self.host / "alpha").is_symlink())
        self.assertFalse((self.host / "beta").exists())

    def test_unlink_removes_only_links(self):
        self.run_cmd("link")
        self.run_cmd("unlink", "--skill", "alpha")
        self.assertFalse((self.host / "alpha").exists())
        self.assertTrue((self.repo / "alpha" / "SKILL.md").exists())

    def test_unlink_requires_skill(self):
        self.assertEqual(self.run_cmd("unlink"), 2)

    def test_unlink_leaves_foreign_links(self):
        elsewhere = self.tmp / "old" / "alpha"
        elsewhere.mkdir(parents=True)
        (self.host / "alpha").symlink_to(elsewhere)
        self.run_cmd("unlink", "--skill", "alpha")
        self.assertTrue((self.host / "alpha").is_symlink())

    def test_status_reports_counts(self):
        self.run_cmd("link", "--skill", "alpha")
        self.assertEqual(self.run_cmd("status"), 0)

    def test_missing_host_directory_is_skipped(self):
        with mock.patch.object(inst, "HOSTS", {"ghost": str(self.tmp / "nope")}):
            with mock.patch.object(sys, "argv", ["install_skills.py", "link"]):
                self.assertEqual(inst.main(), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
