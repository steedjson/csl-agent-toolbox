#!/usr/bin/env python3
"""Deterministic tests for scripts/sync_upstream.py (stdlib only, no network).

Run: python3 scripts/test_sync_upstream.py
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tarfile
import unittest
from pathlib import Path
from unittest.mock import patch

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
        code = sync.cmd_update(self.repo, set(), apply=True, git_base=self.git_base)
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
        code = sync.cmd_update(self.repo, set(), apply=True, git_base=self.git_base)
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
        sync.cmd_update(self.repo, set(), apply=True, git_base=self.git_base)
        self.assertTrue((self.repo / "demo" / "new.md").exists())
        self.bump_upstream({"new.md": None})
        sync.cmd_update(self.repo, set(), apply=True, git_base=self.git_base)
        self.assertFalse((self.repo / "demo" / "new.md").exists())


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
        code = sync.cmd_import(self.repo, "demo", "upstream", "skills/demo", [], "test", git_base=self.git_base)
        self.assertEqual(code, 0)
        self.assertEqual(sorted(p.name for p in (self.repo / "demo").iterdir()),
                         ["SKILL.md", "notes.md"])
        entry = json.loads((self.repo / "skills.json").read_text(encoding="utf-8"))["skills"][0]
        self.assertEqual(entry["upstream"]["ref"], self.sha)
        self.assertEqual(entry["upstream"]["path"], "skills/demo")
        self.assertEqual(entry["description"], "demo skill")
        self.assertEqual(entry["files"], ["SKILL.md", "notes.md"])

    def test_import_repo_root_includes_nested_files(self):
        code = sync.cmd_import(self.repo, "whole", "upstream", ".", [], "test", git_base=self.git_base)
        self.assertEqual(code, 0)
        self.assertTrue((self.repo / "whole" / "SKILL.md").exists())
        self.assertTrue((self.repo / "whole" / "skills" / "demo" / "SKILL.md").exists())
        self.assertTrue((self.repo / "whole" / "README.md").exists())

    def test_import_exclude_drops_paths(self):
        code = sync.cmd_import(self.repo, "whole", "upstream", ".", ["skills/"], "test", git_base=self.git_base)
        self.assertEqual(code, 0)
        self.assertFalse((self.repo / "whole" / "skills").exists())
        self.assertTrue((self.repo / "whole" / "SKILL.md").exists())

    def test_import_refuses_existing_directory(self):
        (self.repo / "demo").mkdir()
        code = sync.cmd_import(self.repo, "demo", "upstream", "skills/demo", [], "test", git_base=self.git_base)
        self.assertEqual(code, 2)

    def test_import_requires_skill_md(self):
        code = sync.cmd_import(self.repo, "readme-only", "upstream", ".", ["skills/", "SKILL.md"], "test", git_base=self.git_base)
        self.assertEqual(code, 2)

    def test_import_detects_license(self):
        code = sync.cmd_import(self.repo, "whole", "upstream", ".", [], "test", git_base=self.git_base)
        self.assertEqual(code, 0)
        entry = json.loads((self.repo / "skills.json").read_text(encoding="utf-8"))["skills"][0]
        self.assertEqual(entry["upstream"]["license"], "MIT")

    def test_imported_skill_is_then_checkable(self):
        sync.cmd_import(self.repo, "demo", "upstream", "skills/demo", [], "test", git_base=self.git_base)
        self.assertEqual(sync.cmd_check(self.repo, set(), self.git_base), 0)

    def test_explicit_branch_remains_update_target(self):
        self.assertEqual(sync.cmd_import(self.repo, "demo", "upstream/tree/main/skills/demo",
                                       None, [], "test", self.git_base), 0)
        entry = json.loads((self.repo / "skills.json").read_text())["skills"][0]
        self.assertEqual(entry["upstream"]["branch"], "main")
        self.assertEqual(sync.latest_revision(entry["upstream"], self.git_base), "main")

    def test_git_symlink_is_rejected(self):
        (self.upstream / "skills/demo/link").symlink_to("../../../../outside")
        git("add", "-A", cwd=self.upstream)
        git("commit", "-qm", "link", cwd=self.upstream)
        git("push", "-q", str(self.tmp / "upstream.git"), "main:main", cwd=self.upstream)
        with self.assertRaisesRegex(RuntimeError, "link"):
            sync.cmd_import(self.repo, "demo", "upstream", "skills/demo", [], "test", self.git_base)
        self.assertFalse((self.repo / "demo").exists())


class ComponentFlowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="component-sync-test-")
        self.addCleanup(self.temporary.cleanup)
        self.repo = Path(self.temporary.name)
        (self.repo / "skills.json").write_text('{"skills": []}\n')

    def metadata(self):
        return json.loads((self.repo / "skills.json").read_text())

    def fixture(self, kind, manifest=None):
        manifest = manifest or {"skill": "SKILL.md", "plugin": ".codex-plugin/plugin.json",
                                "mcp": "mcp.json"}[kind]
        body = (b"---\nname: demo\ndescription: demo\n---\nbody\n" if kind == "skill"
                else b'{"name":"demo","description":"demo"}\n')
        return {manifest: body, "LICENSE": b"MIT License\n", "notes.md": b"v1\n"}

    def import_package(self, kind="skill", name="demo", files=None):
        with patch.object(sync, "fetch", return_value=(files or self.fixture(kind), "v1")):
            self.assertEqual(sync.cmd_import(self.repo, name, "npm:test", None, [], "test", "unused",
                                             kind=kind), 0)

    def test_all_component_kinds_import_check_update(self):
        for kind, (collection, directory) in sync.COMPONENTS.items():
            with self.subTest(kind=kind):
                self.import_package(kind)
                target = self.repo / directory / "demo"
                self.assertEqual(sync.component_dir(self.repo, "demo", kind), target.resolve())
                entry = self.metadata()[collection][0]
                self.assertEqual(entry["upstream"]["license"], "MIT")
                self.assertEqual(entry["description"], "demo")
                before, after = self.fixture(kind), self.fixture(kind)
                after["notes.md"] = b"v2\n"

                def fetch(upstream, revision, git_base):
                    return (before, "v1") if revision == "v1" else (after, "v2")

                with patch.object(sync, "fetch", side_effect=fetch):
                    self.assertEqual(sync.cmd_check(self.repo, {"demo"}, "unused", kind), 1)
                    self.assertEqual(sync.cmd_update(self.repo, {"demo"}, True, "unused", kind), 0)
                self.assertEqual((target / "notes.md").read_bytes(), b"v2\n")
                self.assertEqual(self.metadata()[collection][0]["upstream"]["version"], "v2")

    def test_plugin_manifest_locations(self):
        for index, manifest in enumerate(("plugin.json", ".codex-plugin/plugin.json",
                                          ".claude-plugin/plugin.json")):
            self.import_package("plugin", f"plugin-{index}", self.fixture("plugin", manifest))
        self.assertEqual(len(self.metadata()["plugins"]), 3)

    def test_omp_pi_plugin_packages(self):
        for host in ("omp", "pi"):
            files = {"package.json": json.dumps({"name": "demo", host: {"extensions": ["index.js"]},
                                                   "description": "native plugin"}).encode(),
                     "index.js": b"export default function () {}\n"}
            self.import_package("plugin", host, files)
        self.assertEqual([entry["description"] for entry in self.metadata()["plugins"]],
                         ["native plugin", "native plugin"])

    def test_ordinary_npm_package_is_not_a_plugin(self):
        for metadata in ({"name": "ordinary"}, {"name": "ordinary", "pi": True},
                         {"name": "ordinary", "omp": "not an object"}):
            with patch.object(sync, "fetch", return_value=({"package.json": json.dumps(metadata).encode()}, "v1")):
                self.assertEqual(sync.cmd_import(self.repo, "demo", "npm:test", None, [], "test",
                                                 "unused", kind="plugin"), 2)
        self.assertNotIn("plugins", self.metadata())

    def test_non_skill_requires_own_manifest(self):
        for kind in ("plugin", "mcp"):
            with patch.object(sync, "fetch", return_value=(self.fixture("skill"), "v1")):
                self.assertEqual(sync.cmd_import(self.repo, "demo", "npm:test", None, [], "test",
                                                 "unused", kind=kind), 2)
            self.assertNotIn(sync.COMPONENTS[kind][0], self.metadata())

    def test_import_failure_rolls_back_tree_and_registry(self):
        before = (self.repo / "skills.json").read_bytes()
        with patch.object(sync, "save_registry", side_effect=OSError("disk full")):
            with self.assertRaisesRegex(OSError, "disk full"):
                self.import_package()
        self.assertFalse((self.repo / "demo").exists())
        self.assertEqual((self.repo / "skills.json").read_bytes(), before)
        self.assertFalse(list(self.repo.glob(".sync-*")))

    def test_update_registry_failure_rolls_back_content(self):
        self.import_package()
        before = (self.repo / "skills.json").read_bytes()
        old = sync.local_files(self.repo / "demo")
        after = dict(old, **{"notes.md": b"v2\n"})
        with patch.object(sync, "fetch", side_effect=[(old, "v1"), (after, "v2")]), \
                patch.object(sync, "save_registry", side_effect=OSError("disk full")):
            with self.assertRaisesRegex(OSError, "disk full"):
                sync.cmd_update(self.repo, set(), True, "unused")
        self.assertEqual(sync.local_files(self.repo / "demo"), old)
        self.assertEqual((self.repo / "skills.json").read_bytes(), before)

    def test_staging_write_failure_preserves_tree(self):
        self.import_package()
        before = (self.repo / "skills.json").read_bytes()
        old = sync.local_files(self.repo / "demo")
        after = dict(old, **{"notes.md": b"v2\n"})
        original = Path.write_bytes

        def write(path, payload):
            if path.name == "notes.md" and payload == b"v2\n":
                raise OSError("disk full")
            return original(path, payload)

        with patch.object(sync, "fetch", side_effect=[(old, "v1"), (after, "v2")]), \
                patch.object(Path, "write_bytes", write):
            with self.assertRaisesRegex(OSError, "disk full"):
                sync.cmd_update(self.repo, set(), True, "unused")
        self.assertEqual(sync.local_files(self.repo / "demo"), old)
        self.assertEqual((self.repo / "skills.json").read_bytes(), before)

    def test_completed_component_pin_survives_later_fetch_failure(self):
        self.import_package(name="alpha")
        self.import_package(name="beta")
        old = self.fixture("skill")
        after = dict(old, **{"notes.md": b"v2\n"})
        with patch.object(sync, "fetch", side_effect=[(old, "v1"), (after, "v2"),
                                                      RuntimeError("later source down")]):
            with self.assertRaisesRegex(RuntimeError, "later source down"):
                sync.cmd_update(self.repo, set(), True, "unused")
        entries = self.metadata()["skills"]
        self.assertEqual([e["upstream"]["version"] for e in entries], ["v2", "v1"])
        self.assertEqual((self.repo / "alpha/notes.md").read_bytes(), b"v2\n")
        self.assertEqual((self.repo / "beta/notes.md").read_bytes(), b"v1\n")

    def test_pin_only_update_persisted_before_later_failure(self):
        self.import_package(name="alpha")
        self.import_package(name="beta")
        old = self.fixture("skill")
        with patch.object(sync, "fetch", side_effect=[(old, "v1"), (old, "v2"),
                                                      RuntimeError("later source down")]):
            with self.assertRaisesRegex(RuntimeError, "later source down"):
                sync.cmd_update(self.repo, set(), True, "unused")
        self.assertEqual(self.metadata()["skills"][0]["upstream"]["version"], "v2")

    def test_dry_run_reports_pending_pin_advance(self):
        self.import_package()
        old = self.fixture("skill")
        with patch.object(sync, "fetch", side_effect=[(old, "v1"), (old, "v2")]):
            self.assertEqual(sync.cmd_update(self.repo, set(), False, "unused"), 1)
        self.assertEqual(self.metadata()["skills"][0]["upstream"]["version"], "v1")

    def test_check_reports_outdated_pin_when_local_already_matches_latest(self):
        self.import_package()
        old = self.fixture("skill")
        after = dict(old, **{"notes.md": b"v2\n"})
        (self.repo / "demo/notes.md").write_bytes(b"v2\n")
        with patch.object(sync, "fetch", side_effect=[(old, "v1"), (after, "v2")]):
            self.assertEqual(sync.cmd_check(self.repo, set(), "unused"), 1)

    def test_update_refuses_to_remove_required_manifest(self):
        self.import_package("mcp")
        old = self.fixture("mcp")
        after = {key: value for key, value in old.items() if key != "mcp.json"}
        before = (self.repo / "skills.json").read_bytes()
        with patch.object(sync, "fetch", side_effect=[(old, "v1"), (after, "v2")]):
            with self.assertRaisesRegex(RuntimeError, "manifest"):
                sync.cmd_update(self.repo, set(), True, "unused", "mcp")
        self.assertTrue((self.repo / "mcp/demo/mcp.json").is_file())
        self.assertEqual((self.repo / "skills.json").read_bytes(), before)

    def test_unknown_filter_returns_error(self):
        for command in ("check", "update"):
            with self.subTest(command=command):
                self.assertEqual(sync.main([command, "--repo", str(self.repo),
                                            "--component", "missing"]), 2)

    def test_cli_kind_and_legacy_filter(self):
        self.import_package("mcp")
        old = self.fixture("mcp")
        with patch.object(sync, "fetch", return_value=(old, "v1")):
            self.assertEqual(sync.main(["check", "--kind", "mcp", "--skill", "demo", "--repo",
                                        str(self.repo)]), 0)

    def test_import_rejects_malicious_relative_paths(self):
        for relative in ("../outside", "/tmp/outside", "a/../../outside", "C:/outside"):
            files = dict(self.fixture("skill"), **{relative: b"bad"})
            with self.subTest(relative=relative), \
                    patch.object(sync, "fetch", return_value=(files, "v1")):
                with self.assertRaisesRegex(RuntimeError, "unsafe"):
                    sync.cmd_import(self.repo, "demo", "npm:test", None, [], "test", "unused")
            self.assertFalse((self.repo / "demo").exists())

    def test_local_symlink_rejected_before_update(self):
        self.import_package()
        outside = self.repo / "outside"
        outside.write_bytes(b"untouched")
        (self.repo / "demo/link").symlink_to(outside)
        with patch.object(sync, "fetch", return_value=(self.fixture("skill"), "v1")):
            with self.assertRaisesRegex(RuntimeError, "symlink"):
                sync.cmd_update(self.repo, set(), True, "unused")
        self.assertEqual(outside.read_bytes(), b"untouched")

    def test_component_parent_symlink_escape_rejected(self):
        with tempfile.TemporaryDirectory() as outside:
            (self.repo / "plugins").symlink_to(outside)
            with self.assertRaisesRegex(RuntimeError, "leaves repository"):
                sync.component_dir(self.repo, "demo", "plugin")

    def test_atomic_registry_write_failure_keeps_original(self):
        before = (self.repo / "skills.json").read_bytes()
        with patch.object(sync.os, "replace", side_effect=OSError("disk full")):
            with self.assertRaisesRegex(OSError, "disk full"):
                sync.save_registry(self.repo, {"skills": ["changed"]})
        self.assertEqual((self.repo / "skills.json").read_bytes(), before)
        self.assertFalse(list(self.repo.glob(".skills-*")))


class NpmArchiveTests(unittest.TestCase):
    def archive(self, entries):
        output = io.BytesIO()
        with tarfile.open(fileobj=output, mode="w:gz") as archive:
            for name, payload, kind in entries:
                info = tarfile.TarInfo(name)
                info.type = kind
                info.size = len(payload)
                info.linkname = "../../outside" if kind != tarfile.REGTYPE else ""
                archive.addfile(info, io.BytesIO(payload))
        return output.getvalue()

    def fetch_archive(self, entries, path="."):
        payload = self.archive(entries)
        with patch.object(sync, "http_json", return_value={"version": "1.0.0", "dist": {
                "tarball": "https://example.invalid/archive.tgz"}}), \
                patch.object(sync, "http_bytes", return_value=payload):
            return sync.npm_files("demo", "latest", path)

    def test_package_root_dot_matches_package_prefix(self):
        files, revision = self.fetch_archive([("package/SKILL.md", b"skill", tarfile.REGTYPE),
                                              ("package/nested/a.txt", b"a", tarfile.REGTYPE)])
        self.assertEqual(files, {"SKILL.md": b"skill", "nested/a.txt": b"a"})
        self.assertEqual(revision, "1.0.0")

    def test_subdirectory_still_works(self):
        files, _ = self.fetch_archive([("package/skills/demo/SKILL.md", b"skill", tarfile.REGTYPE)],
                                      "skills/demo")
        self.assertEqual(files, {"SKILL.md": b"skill"})

    def test_archive_path_traversal_rejected(self):
        for path in ("package/../../outside", "/tmp/outside", "package/skills/../outside"):
            with self.subTest(path=path), self.assertRaisesRegex(RuntimeError, "unsafe"):
                self.fetch_archive([(path, b"bad", tarfile.REGTYPE)])

    def test_archive_links_rejected(self):
        for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE):
            with self.subTest(kind=kind), self.assertRaisesRegex(RuntimeError, "link"):
                self.fetch_archive([("package/link", b"", kind)])

    def test_source_path_traversal_rejected_before_fetch(self):
        with patch.object(sync, "http_json") as http:
            for path in ("../other", "/etc", "nested/../other"):
                with self.assertRaisesRegex(RuntimeError, "unsafe"):
                    sync.npm_files("demo", "latest", path)
            http.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
