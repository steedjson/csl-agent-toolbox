#!/usr/bin/env python3
"""Deterministic tests for scripts/sync_upstream.py (stdlib only, no network).

Run: python3 scripts/test_sync_upstream.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sync_upstream as sync  # noqa: E402

GIT_ENV = ["-c", "user.email=test@example.com", "-c", "user.name=test"]


def git(*args, cwd):
    return subprocess.run(["git", *GIT_ENV, *args], cwd=cwd, check=True,
                          capture_output=True).stdout.decode().strip()


class PlanTests(unittest.TestCase):
    def test_fast_forward_when_local_unmodified(self):
        base = {"a.md": b"one\n"}
        changes = sync.plan(base, {"a.md": b"one\n"}, {"a.md": b"two\n"})
        self.assertEqual(changes, [("update", "a.md", b"two\n", "fast-forward")])

    def test_keeps_local_edits_when_upstream_unmodified(self):
        base = {"a.md": b"one\n"}
        changes = sync.plan(base, {"a.md": b"local\n"}, {"a.md": b"one\n"})
        self.assertEqual([c[0] for c in changes], ["keep"])

    def test_merges_disjoint_edits(self):
        base = {"a.md": b"1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n"}
        local = {"a.md": b"1\n2\n3\n4\n5\n6\n7\n8\n9\n10-local\n"}
        upstream = {"a.md": b"1-up\n2\n3\n4\n5\n6\n7\n8\n9\n10\n"}
        changes = sync.plan(base, local, upstream)
        self.assertEqual(changes[0][0], "merge")
        self.assertEqual(changes[0][2], b"1-up\n2\n3\n4\n5\n6\n7\n8\n9\n10-local\n")

    def test_conflict_has_no_payload(self):
        base = {"a.md": b"1\n2\n3\n"}
        changes = sync.plan(base, {"a.md": b"1\nLOCAL\n3\n"}, {"a.md": b"1\nUP\n3\n"})
        self.assertEqual(changes[0][0], "conflict")
        self.assertIsNone(changes[0][2])

    def test_upstream_deletion_respects_local_edits(self):
        base = {"gone.md": b"x\n"}
        self.assertEqual(sync.plan(base, {"gone.md": b"x\n"}, {})[0][0], "delete")
        self.assertEqual(sync.plan(base, {"gone.md": b"edited\n"}, {})[0][0], "conflict")

    def test_add_and_local_only(self):
        changes = sync.plan({}, {"keep.md": b"k\n"}, {"new.md": b"n\n"})
        actions = {c[1]: c[0] for c in changes}
        self.assertEqual(actions, {"keep.md": "keep", "new.md": "add"})

    def test_both_added_differently_conflicts(self):
        changes = sync.plan({}, {"x.md": b"a\n"}, {"x.md": b"b\n"})
        self.assertEqual(changes[0][0], "conflict")


class FrontmatterTests(unittest.TestCase):
    def test_reads_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "SKILL.md"
            path.write_text("---\nname: alpha\ndescription: x\n---\nbody\n", encoding="utf-8")
            self.assertEqual(sync.frontmatter_name(Path(tmp)), "alpha")

    def test_missing_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "SKILL.md").write_text("body only\n", encoding="utf-8")
            self.assertIsNone(sync.frontmatter_name(Path(tmp)))

    def test_resolves_by_frontmatter_when_dir_differs(self):
        with tempfile.TemporaryDirectory() as tmp:
            installed = Path(tmp) / "taste-skill"
            installed.mkdir()
            (installed / "SKILL.md").write_text(
                "---\nname: design-taste-frontend\n---\n", encoding="utf-8")
            self.assertEqual(sync.resolve_install_target(Path(tmp), "design-taste-frontend"), installed)
            self.assertIsNone(sync.resolve_install_target(Path(tmp), "absent"))


class GithubFlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sync-test-"))
        self.upstream = self.tmp / "upstream"
        (self.upstream / "skills" / "demo" / "agents").mkdir(parents=True)
        (self.upstream / "skills" / "demo" / "SKILL.md").write_text("1\n2\n3\n", encoding="utf-8")
        (self.upstream / "skills" / "demo" / "agents" / "openai.yaml").write_text("v1\n", encoding="utf-8")
        git("init", "-q", "-b", "main", cwd=self.upstream)
        git("add", "-A", cwd=self.upstream)
        git("commit", "-qm", "v1", cwd=self.upstream)
        self.base = git("rev-parse", "HEAD", cwd=self.upstream)
        git("clone", "-q", "--bare", str(self.upstream), str(self.tmp / "upstream.git"), cwd=self.tmp)

        self.repo = self.tmp / "repo"
        skill_dir = self.repo / "demo"
        (skill_dir / "agents").mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("1\n2\n3\n", encoding="utf-8")
        (skill_dir / "agents" / "openai.yaml").write_text("v1\nlocal\n", encoding="utf-8")
        (self.repo / "skills.json").write_text(json.dumps({
            "name": "test",
            "skills": [{
                "name": "demo",
                "files": ["SKILL.md", "agents/openai.yaml"],
                "upstream": {
                    "type": "github", "repo": "upstream", "path": "skills/demo",
                    "ref": self.base, "license": "MIT", "synced_at": "2026-01-01",
                },
            }],
        }, indent=2) + "\n", encoding="utf-8")
        self.git_base = f"file://{self.tmp}"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def bump_upstream(self, files):
        for relative, content in files.items():
            path = self.upstream / "skills" / "demo" / relative
            if content is None:
                path.unlink()
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
        git("add", "-A", cwd=self.upstream)
        git("commit", "-qm", "bump", cwd=self.upstream)
        git("push", "-q", str(self.tmp / "upstream.git"), "main:main", cwd=self.upstream)
        return git("rev-parse", "HEAD", cwd=self.upstream)

    def test_apply_updates_pin_and_preserves_local_edits(self):
        new_sha = self.bump_upstream({"SKILL.md": "1-up\n2\n3\n", "new.md": "n\n"})
        code = sync.cmd_update(self.repo, set(), apply=True, install=False, prune=False,
                               git_base=self.git_base)
        self.assertEqual(code, 0)
        self.assertEqual((self.repo / "demo" / "SKILL.md").read_text(encoding="utf-8"), "1-up\n2\n3\n")
        self.assertEqual((self.repo / "demo" / "new.md").read_text(encoding="utf-8"), "n\n")
        self.assertIn("local", (self.repo / "demo" / "agents" / "openai.yaml").read_text(encoding="utf-8"))
        entry = json.loads((self.repo / "skills.json").read_text(encoding="utf-8"))["skills"][0]
        self.assertEqual(entry["upstream"]["ref"], new_sha)
        self.assertEqual(entry["files"], ["SKILL.md", "agents/openai.yaml", "new.md"])

    def test_conflict_skips_skill_without_writing(self):
        original = (self.repo / "demo" / "SKILL.md").read_text(encoding="utf-8")
        self.bump_upstream({"SKILL.md": "1-up\n2-up\n3\n"})
        (self.repo / "demo" / "SKILL.md").write_text("1-local\n2-local\n3\n", encoding="utf-8")
        before = (self.repo / "demo" / "SKILL.md").read_text(encoding="utf-8")
        code = sync.cmd_update(self.repo, set(), apply=True, install=False, prune=False,
                               git_base=self.git_base)
        self.assertEqual(code, 1)
        self.assertEqual((self.repo / "demo" / "SKILL.md").read_text(encoding="utf-8"), before)
        entry = json.loads((self.repo / "skills.json").read_text(encoding="utf-8"))["skills"][0]
        self.assertEqual(entry["upstream"]["ref"], self.base)
        self.assertNotEqual(original, before)

    def test_check_reports_drift_and_pin_state(self):
        self.assertEqual(sync.cmd_check(self.repo, set(), self.git_base), 0)
        self.bump_upstream({"SKILL.md": "1-up\n2\n3\n"})
        self.assertEqual(sync.cmd_check(self.repo, set(), self.git_base), 1)

    def test_deleted_upstream_file_is_removed(self):
        self.bump_upstream({"new.md": "n\n"})
        sync.cmd_update(self.repo, set(), apply=True, install=False, prune=False,
                        git_base=self.git_base)
        self.assertTrue((self.repo / "demo" / "new.md").exists())
        self.bump_upstream({"new.md": None})
        sync.cmd_update(self.repo, set(), apply=True, install=False, prune=False,
                        git_base=self.git_base)
        self.assertFalse((self.repo / "demo" / "new.md").exists())

    def test_install_mirrors_and_prunes(self):
        install_root = self.tmp / "installed"
        target = install_root / "demo"
        target.mkdir(parents=True)
        (target / "SKILL.md").write_text("old\n", encoding="utf-8")
        (target / "stale.md").write_text("stale\n", encoding="utf-8")
        self.bump_upstream({"SKILL.md": "1-up\n2\n3\n"})
        os.environ["SKILL_INSTALL_DIR"] = str(install_root)
        try:
            code = sync.cmd_update(self.repo, set(), apply=True, install=True, prune=True,
                                   git_base=self.git_base)
        finally:
            del os.environ["SKILL_INSTALL_DIR"]
        self.assertEqual(code, 0)
        self.assertEqual((target / "SKILL.md").read_text(encoding="utf-8"), "1-up\n2\n3\n")
        self.assertFalse((target / "stale.md").exists())
        self.assertTrue((target / "agents" / "openai.yaml").exists())


class BinaryTests(unittest.TestCase):
    def test_binary_merge_is_a_conflict_not_a_crash(self):
        base = {"logo.png": b"\x89PNG\r\n\x1a\n\x00\x00base"}
        local = {"logo.png": b"\x89PNG\r\n\x1a\n\x00\x00local"}
        upstream = {"logo.png": b"\x89PNG\r\n\x1a\n\x00\x00up"}
        changes = sync.plan(base, local, upstream)
        self.assertEqual(changes[0][0], "conflict")
        self.assertIsNone(changes[0][2])

    def test_binary_fast_forward_still_works(self):
        base = {"logo.png": b"\x89PNG\x00base"}
        upstream = {"logo.png": b"\x89PNG\x00up"}
        self.assertEqual(sync.plan(base, dict(base), upstream)[0][0], "update")


class SourceParsingTests(unittest.TestCase):
    def test_plain_slug(self):
        self.assertEqual(sync.parse_github_source("gnipbao/dao-skill"),
                         ("gnipbao/dao-skill", None, None))

    def test_url_and_dot_git(self):
        self.assertEqual(sync.parse_github_source("https://github.com/gnipbao/dao-skill.git"),
                         ("gnipbao/dao-skill", None, None))

    def test_blob_url_yields_skill_directory(self):
        self.assertEqual(
            sync.parse_github_source(
                "https://github.com/mattpocock/skills/blob/main/skills/productivity/grill-me/SKILL.md"),
            ("mattpocock/skills", "main", "skills/productivity/grill-me"))

    def test_tree_url(self):
        self.assertEqual(
            sync.parse_github_source(
                "https://github.com/mattpocock/skills/tree/main/skills/productivity/grill-me"),
            ("mattpocock/skills", "main", "skills/productivity/grill-me"))

    def test_npm_prefix_is_not_a_github_source(self):
        self.assertIsNone(sync.parse_github_source("npm:natureco-cli")[0])

    def test_derived_names(self):
        self.assertEqual(sync.import_name("gnipbao/dao-skill", None), "dao-skill")
        self.assertEqual(sync.import_name("mattpocock/skills", "skills/productivity/grill-me"), "grill-me")
        self.assertEqual(
            sync.import_name(
                "https://github.com/mattpocock/skills/blob/main/skills/productivity/grill-me/SKILL.md", None),
            "grill-me")
        self.assertEqual(sync.import_name("npm:natureco-cli", None), "natureco-cli")


class ImportFlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="import-test-"))
        self.upstream = self.tmp / "upstream"
        (self.upstream / "skills" / "demo").mkdir(parents=True)
        (self.upstream / "skills" / "demo" / "SKILL.md").write_text(
            "---\nname: demo\ndescription: demo skill\n---\nbody\n", encoding="utf-8")
        (self.upstream / "skills" / "demo" / "notes.md").write_text("n\n", encoding="utf-8")
        (self.upstream / "SKILL.md").write_text(
            "---\nname: whole\ndescription: whole repo\n---\nroot body\n", encoding="utf-8")
        (self.upstream / "README.md").write_text("root readme\n", encoding="utf-8")
        (self.upstream / "LICENSE").write_text("MIT License\n\nCopyright\n", encoding="utf-8")
        git("init", "-q", "-b", "main", cwd=self.upstream)
        git("add", "-A", cwd=self.upstream)
        git("commit", "-qm", "v1", cwd=self.upstream)
        self.sha = git("rev-parse", "HEAD", cwd=self.upstream)
        git("clone", "-q", "--bare", str(self.upstream), str(self.tmp / "upstream.git"), cwd=self.tmp)

        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        (self.repo / "skills.json").write_text('{"name":"t","skills":[]}\n', encoding="utf-8")
        self.git_base = f"file://{self.tmp}"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_import_subdirectory_records_pin(self):
        code = sync.cmd_import(self.repo, "demo", "upstream", "skills/demo", [], "test",
                               install=False, git_base=self.git_base)
        self.assertEqual(code, 0)
        self.assertEqual(sorted(p.name for p in (self.repo / "demo").iterdir()),
                         ["SKILL.md", "notes.md"])
        entry = json.loads((self.repo / "skills.json").read_text(encoding="utf-8"))["skills"][0]
        self.assertEqual(entry["upstream"]["ref"], self.sha)
        self.assertEqual(entry["upstream"]["path"], "skills/demo")
        self.assertEqual(entry["description"], "demo skill")
        self.assertEqual(entry["files"], ["SKILL.md", "notes.md"])

    def test_import_repo_root_includes_nested_files(self):
        code = sync.cmd_import(self.repo, "whole", "upstream", ".", [], "test",
                               install=False, git_base=self.git_base)
        self.assertEqual(code, 0)
        self.assertTrue((self.repo / "whole" / "SKILL.md").exists())
        self.assertTrue((self.repo / "whole" / "skills" / "demo" / "SKILL.md").exists())
        self.assertTrue((self.repo / "whole" / "README.md").exists())

    def test_import_exclude_drops_paths(self):
        code = sync.cmd_import(self.repo, "whole", "upstream", ".", ["skills/"], "test",
                               install=False, git_base=self.git_base)
        self.assertEqual(code, 0)
        self.assertFalse((self.repo / "whole" / "skills").exists())
        self.assertTrue((self.repo / "whole" / "SKILL.md").exists())

    def test_import_refuses_existing_directory(self):
        (self.repo / "demo").mkdir()
        code = sync.cmd_import(self.repo, "demo", "upstream", "skills/demo", [], "test",
                               install=False, git_base=self.git_base)
        self.assertEqual(code, 2)

    def test_import_requires_skill_md(self):
        code = sync.cmd_import(self.repo, "readme-only", "upstream", ".", ["skills/", "SKILL.md"], "test",
                               install=False, git_base=self.git_base)
        self.assertEqual(code, 2)

    def test_import_detects_license(self):
        code = sync.cmd_import(self.repo, "whole", "upstream", ".", [], "test",
                               install=False, git_base=self.git_base)
        self.assertEqual(code, 0)
        entry = json.loads((self.repo / "skills.json").read_text(encoding="utf-8"))["skills"][0]
        self.assertEqual(entry["upstream"]["license"], "MIT")

    def test_imported_skill_is_then_checkable(self):
        sync.cmd_import(self.repo, "demo", "upstream", "skills/demo", [], "test",
                        install=False, git_base=self.git_base)
        self.assertEqual(sync.cmd_check(self.repo, set(), self.git_base), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
