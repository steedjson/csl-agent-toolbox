#!/usr/bin/env python3
"""Offline stdlib-only consistency validator for csl-agent-toolbox."""
import json
import re
import subprocess
import sys
from pathlib import Path

from sync_upstream import COMPONENTS, component_dir

HOME_PATH_RE = re.compile(r"/(?:Users|home)/[^/\s]+")


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def check_skills(repo):
    errors = []
    data = load_json(repo / "skills.json")
    for kind, (key, _) in COMPONENTS.items():
        seen = set()
        for entry in data.get(key, []):
            name = entry.get("name", "")
            if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", name) or name in seen:
                errors.append(f"invalid or duplicate {kind} name: {name!r}")
                continue
            seen.add(name)
            root = component_dir(repo, name, kind)
            if not root.is_dir() or not root.resolve().is_relative_to(repo.resolve()):
                errors.append(f"{kind} directory missing or outside repository: {name}")
                continue
            for rel in entry.get("files", []):
                file = root / rel
                if not file.is_file() or not file.resolve().is_relative_to(root.resolve()):
                    errors.append(f"invalid {kind} file: {name}/{rel}")
            if kind == "plugin" and not any((root / manifest).is_file() for manifest in
                    ("plugin.json", ".codex-plugin/plugin.json", ".claude-plugin/plugin.json", "package.json")):
                errors.append(f"plugin manifest missing: {name}")
            if kind == "mcp":
                try:
                    from toolbox import mcp_server
                    mcp_server(root, name)
                except (ValueError, OSError, KeyError) as error:
                    errors.append(f"invalid MCP package {name}: {error}")
    for skill in data.get("skills", []):
        name = skill.get("name")
        if not name:
            errors.append("skill entry missing 'name'")
            continue
        sdir = repo / name
        if not sdir.is_dir():
            errors.append(f"skill dir missing: {name}/")
            continue
        if not (sdir / "SKILL.md").is_file():
            errors.append(f"skill missing SKILL.md: {name}/")
        for rel in skill.get("files", []):
            if not (sdir / rel).is_file():
                errors.append(f"skill file missing: {name}/{rel}")
    return errors


def check_upstreams(repo):
    errors = []
    data = load_json(repo / "skills.json")
    names = {s.get("name") for s in data.get("skills", [])}
    entries = [entry for key, _ in COMPONENTS.values() for entry in data.get(key, [])]
    for skill in entries:
        name = skill.get("name")
        for dep in skill.get("depends_on", []):
            if dep not in names:
                errors.append(f"skill {name}: depends_on unknown skill {dep!r}")
        upstream = skill.get("upstream")
        if not upstream:
            continue
        kind = upstream.get("type")
        if kind == "github":
            for field in ("repo", "path", "ref"):
                if not upstream.get(field):
                    errors.append(f"upstream {name}: missing '{field}' for github source")
            ref = upstream.get("ref", "")
            if ref and not re.fullmatch(r"[0-9a-f]{7,40}", ref):
                errors.append(f"upstream {name}: github 'ref' must be a commit sha, got {ref!r}")
        elif kind == "npm":
            for field in ("package", "path", "version"):
                if not upstream.get(field):
                    errors.append(f"upstream {name}: missing '{field}' for npm source")
        else:
            errors.append(f"upstream {name}: unsupported type {kind!r}")
        if not upstream.get("license"):
            errors.append(f"upstream {name}: missing 'license'")
        synced = upstream.get("synced_at", "")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(synced)):
            errors.append(f"upstream {name}: 'synced_at' must be YYYY-MM-DD, got {synced!r}")
    return errors


def check_marketplace(repo):
    mp = repo / ".agents" / "plugins" / "marketplace.json"
    if not mp.is_file():
        return []
    data = load_json(mp)
    errors = []
    for plug in data.get("plugins", []):
        name = plug.get("name")
        if not name:
            errors.append("marketplace plugin entry missing 'name'")
            continue
        path = (plug.get("source") or {}).get("path", "")
        if not path:
            errors.append(f"marketplace plugin {name} missing source.path")
            continue
        pdir = Path(path) if Path(path).is_absolute() else repo / path
        manifest = pdir / ".codex-plugin" / "plugin.json"
        if not manifest.is_file():
            errors.append(f"plugin manifest missing: {name} -> {manifest}")
            continue
        try:
            load_json(manifest)
        except json.JSONDecodeError as e:
            errors.append(f"plugin manifest invalid JSON ({name}): {e}")
    return errors


def _tracked_docs(repo):
    docs = ["CLAUDE.md", "README.md", "AGENTS.md"]
    plugs = repo / "plugins"
    if plugs.is_dir():
        for pdir in sorted(plugs.iterdir()):
            readme = pdir / "README.md"
            if readme.is_file():
                docs.append(str(readme.relative_to(repo)))
    return docs


def check_paths(repo):
    errors = []
    for rel in _tracked_docs(repo):
        path = repo / rel
        if not path.is_file():
            continue
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if HOME_PATH_RE.search(line):
                errors.append(f"hardcoded home path {rel}:{line_no}: {line.strip()[:80]}")
    return errors


def check_skill_contracts(repo):
    errors = []
    for script in sorted(repo.glob("*/scripts/validate_contract.py")):
        result = subprocess.run(
            [sys.executable, str(script)],
            cwd=repo,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode:
            detail = result.stderr.strip() or result.stdout.strip() or "unknown failure"
            errors.append(f"skill contract failed ({script.relative_to(repo)}): {detail}")
    return errors


def main():
    repo = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
    errors = check_skills(repo) + check_upstreams(repo) + check_marketplace(repo) + check_paths(repo) + check_skill_contracts(repo)
    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        print(f"\n{len(errors)} problem(s) found.", file=sys.stderr)
        return 1
    print("OK: skills.json, marketplace.json, plugin manifests, tracked docs, and skill contracts validated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
