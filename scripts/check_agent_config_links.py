#!/usr/bin/env python3
"""Warn when a host's global instruction file stopped being a link to the canonical copy.

`codegraph install` replaces the symlink with a regular file, so the two agents
silently diverge: edits to the canonical file stop reaching the other host.
This runs at SessionStart and only reports; it never rewrites, because the
replacement file may hold newer content worth keeping.

Stdlib only, no third-party imports.
"""
import json
import os
import sys
from pathlib import Path

# (host file, canonical target). Both live under the two agents' config dirs.
LINKS = [
    ("~/.claude/CLAUDE.md", "~/.codex/AGENTS.md"),
    ("~/.claude/RTK.md", "~/.codex/RTK.md"),
]


def check(links=LINKS, expand=os.path.expanduser):
    """Return a list of human-readable problems; empty means all links are intact."""
    problems = []
    for link_s, target_s in links:
        link = Path(expand(link_s))
        target = Path(expand(target_s))
        if not target.exists():
            problems.append(f"{link_s}: canonical file {target_s} is missing")
            continue
        if link.is_symlink():
            if not link.exists():
                problems.append(f"{link_s}: dangling symlink (canonical is {target_s})")
            elif link.resolve() != target.resolve():
                problems.append(
                    f"{link_s}: links to {os.path.realpath(link)}, expected {target_s}"
                )
            continue
        if link.exists():
            problems.append(f"{link_s}: replaced by a regular file (canonical is {target_s})")
        else:
            problems.append(f"{link_s}: absent (canonical is {target_s})")
    return problems


def repair_command(links=LINKS):
    parts = [f"ln -sf {t} {l}" for l, t in links]
    return " && ".join(parts)


def main():
    problems = check()
    if not problems:
        return 0
    lines = ["AGENT CONFIG LINKS BROKEN — the two hosts have diverged:"]
    lines.extend(f"  - {p}" for p in problems)
    lines.append(f"Repair: {repair_command()}")
    lines.append("Check the replaced file's content first; it may be newer.")
    # Plain stdout from an async hook is dropped ("no response payload"); only
    # JSON with systemMessage reaches the user.
    print(json.dumps({"systemMessage": "\n".join(lines)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
