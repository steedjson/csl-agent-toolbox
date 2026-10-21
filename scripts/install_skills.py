#!/usr/bin/env python3
"""Install skills from this repository into agent hosts by symlink.

This repository is the source of truth. Hosts discover a skill from its
SKILL.md, so a symlink from the host skills directory to the repository
directory is enough — no copy, no build, and edits here take effect
immediately in every host.

Usage:
    python3 scripts/install_skills.py status
    python3 scripts/install_skills.py link --skill <name> --host <agent>
    python3 scripts/install_skills.py link                 # all skills, all existing hosts
    python3 scripts/install_skills.py link --prune          # remove links pointing elsewhere
    python3 scripts/install_skills.py unlink --skill grilling

Hosts: claude (~/.claude/skills), codex (~/.codex/skills), agents (~/.agents/skills),
dsh (~/.dsh/skills), pi (~/.pi/agent/skills), omp (~/.omp/agent/skills). Override with --host.
Installing is always explicit: run this only when the user names the target agent.
Only symlinks are created or removed; repository files are never modified.
"""
import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

HOSTS = {
    "claude": "~/.claude/skills",
    "codex": "~/.codex/skills",
    "agents": "~/.agents/skills",
    "dsh": "~/.dsh/skills",
    "pi": "~/.pi/agent/skills",
    "omp": "~/.omp/agent/skills",
    "zcode": "~/.zcode/skills",
    "cow": "~/cow/skills",
}


def repo_skills():
    """Return {skill name: directory} for every root-level skill in this repository."""
    skills = {}
    for entry in sorted(REPO.iterdir()):
        if entry.is_dir() and (entry / "SKILL.md").is_file():
            skills[entry.name] = entry
    return skills


def host_paths(selected):
    names = selected or list(HOSTS)
    resolved = {}
    for name in names:
        if name not in HOSTS:
            raise SystemExit(f"error: unknown host {name!r}; known: {', '.join(HOSTS)}")
        path = Path(HOSTS[name]).expanduser()
        resolved[name] = path
    return resolved


def same_path(left, right):
    """Compare paths after resolving symlinks on both sides (macOS /var -> /private/var)."""
    return Path(os.path.realpath(left)) == Path(os.path.realpath(right))


def link_state(link, source):
    """Describe one host entry: missing, linked-to-source, or linked-elsewhere."""
    if not link.is_symlink():
        if link.exists():
            return "real-directory"
        return "missing"
    return "ok" if same_path(link, source) else "elsewhere"


def cmd_status(selected_hosts, selected_skills):
    skills = repo_skills()
    wanted = {n: d for n, d in skills.items() if not selected_skills or n in selected_skills}
    for host, root in host_paths(selected_hosts).items():
        if not root.is_dir():
            print(f"{host}: {root} does not exist")
            continue
        if root.is_symlink() and same_path(root, REPO):
            print(f"{host}: {root} -> direct connection (directory symlink to the repository)")
            print(f"  all {len(skills)} repository skill(s) visible; nothing to link or unlink")
            continue
        counts = {"ok": 0, "elsewhere": 0, "missing": 0, "real-directory": 0}
        problems = []
        for name, source in wanted.items():
            state = link_state(root / name, source)
            counts[state] += 1
            if state in ("elsewhere", "real-directory"):
                target = os.path.realpath(root / name) if state == "elsewhere" else "(copy, not a link)"
                problems.append(f"  {state:<14} {name:<42} -> {target}")
        print(f"{host}: {root}")
        print(f"  linked={counts['ok']} elsewhere={counts['elsewhere']} "
              f"missing={counts['missing']} real-directory={counts['real-directory']}")
        for line in problems:
            print(line)
    return 0


def cmd_link(selected_hosts, selected_skills, prune, dry_run):
    skills = repo_skills()
    wanted = {n: d for n, d in skills.items() if not selected_skills or n in selected_skills}
    unknown = set(selected_skills) - set(skills)
    if unknown:
        print(f"error: not a repository skill: {', '.join(sorted(unknown))}", file=sys.stderr)
        return 2

    changed = 0
    for host, root in host_paths(selected_hosts).items():
        if not root.is_dir():
            print(f"{host}: skipped ({root} does not exist)")
            continue
        for name, source in wanted.items():
            link = root / name
            state = link_state(link, source)
            if state == "ok":
                continue
            if state == "real-directory":
                print(f"{host}/{name}: skipped (real directory, not a link; remove it manually)")
                continue
            if state == "elsewhere" and not prune:
                print(f"{host}/{name}: skipped (links elsewhere; rerun with --prune to replace)")
                continue
            if dry_run:
                print(f"{host}/{name}: would link -> {source}")
                changed += 1
                continue
            if state == "elsewhere":
                link.unlink()
            link.symlink_to(source)
            print(f"{host}/{name}: linked -> {source}")
            changed += 1

    if not dry_run:
        print(f"\n{changed} link(s) changed")
    return 0


def cmd_unlink(selected_hosts, selected_skills):
    if not selected_skills:
        print("error: unlink requires --skill", file=sys.stderr)
        return 2
    skills = repo_skills()
    removed = 0
    for host, root in host_paths(selected_hosts).items():
        if not root.is_dir():
            continue
        for name in selected_skills:
            link = root / name
            if not link.is_symlink():
                continue
            if name in skills and link_state(link, skills[name]) != "ok":
                print(f"{host}/{name}: skipped (links elsewhere)")
                continue
            link.unlink()
            print(f"{host}/{name}: unlinked")
            removed += 1
    print(f"\n{removed} link(s) removed")
    return 0


def cmd_list(selected_hosts):
    skills = repo_skills()
    data = {}
    registry = REPO / "skills.json"
    if registry.is_file():
        try:
            data = {s["name"]: s for s in json.loads(registry.read_text(encoding="utf-8"))["skills"]}
        except (json.JSONDecodeError, KeyError):
            data = {}
    print(f"{len(skills)} repository skill(s)")
    for name, directory in skills.items():
        entry = data.get(name, {})
        upstream = entry.get("upstream") or {}
        origin = "local"
        if upstream:
            origin = upstream.get("repo") or upstream.get("package") or "upstream"
            origin = f"{origin}@{upstream.get('ref') or upstream.get('version')}"
        deps = entry.get("depends_on") or []
        suffix = f"  depends_on={','.join(deps)}" if deps else ""
        print(f"  {name:<42} {origin}{suffix}")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=["status", "link", "unlink", "list"])
    parser.add_argument("--host", action="append", default=[], help="limit to one host (repeatable)")
    parser.add_argument("--skill", action="append", default=[], help="limit to one skill (repeatable)")
    parser.add_argument("--prune", action="store_true",
                        help="replace links that point outside this repository")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.command == "status":
        return cmd_status(args.host, set(args.skill))
    if args.command == "list":
        return cmd_list(args.host)
    if args.command == "unlink":
        return cmd_unlink(args.host, args.skill)
    return cmd_link(args.host, set(args.skill), args.prune, args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
