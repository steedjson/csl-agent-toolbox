#!/usr/bin/env python3
"""Check and update vendored third-party skills from their upstream sources.

Every skill in skills.json may declare an "upstream" block:

    "upstream": {
      "type": "github",
      "repo": "owner/repo",
      "path": "skills/example",          # directory inside the repo
      "ref": "<commit sha or branch>",   # revision currently vendored
      "license": "MIT",
      "synced_at": "2026-08-21"
    }

    "upstream": {
      "type": "npm",
      "package": "some-cli",
      "path": "skills/example",          # directory inside the package
      "version": "1.2.3",
      "license": "MIT",
      "synced_at": "2026-08-21"
    }

"ref"/"version" is the upstream revision the repository was last synced to, and
also the merge base for three-way merges. Local edits are therefore preserved:

    local == base      -> take upstream (fast-forward)
    upstream == base   -> keep local
    both changed       -> git merge-file; conflicts abort that file
    upstream deleted   -> delete only when local is unmodified

Usage:
    python3 scripts/sync_upstream.py check
    python3 scripts/sync_upstream.py update --apply
    python3 scripts/sync_upstream.py update --apply --install

Exit codes: 0 clean/applied, 1 drift or conflict, 2 error.
"""
import argparse
import atexit
import base64
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

NPM_REGISTRY = "https://registry.npmjs.org"
DEFAULT_GIT_BASE = "https://github.com"
SKIP_NAMES = {".DS_Store", "__pycache__"}


def run(cmd, cwd=None):
    result = subprocess.run(cmd, cwd=cwd, capture_output=True)
    if result.returncode:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(cmd)}\n"
            f"{result.stderr.decode('utf-8', 'replace').strip()}"
        )
    return result.stdout


_HTTP_CACHE = {}


def http_bytes(url, attempts=3):
    """Download a URL with bounded retries; cached per process to avoid repeat fetches."""
    if url in _HTTP_CACHE:
        return _HTTP_CACHE[url]
    last = None
    for _ in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=120) as response:
                payload = response.read()
            _HTTP_CACHE[url] = payload
            return payload
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            last = error
    raise RuntimeError(f"download failed after {attempts} attempts: {url}: {last}")


def http_json(url):
    return json.loads(http_bytes(url).decode("utf-8"))


def fetch_revision(work, ref):
    """Fetch one revision; fall back to a full fetch when the host rejects an unadvertised SHA."""
    try:
        run([
            "git", "-C", work, "fetch", "-q", "--depth", "1",
            "--filter=blob:none", "--no-tags", "origin", ref,
        ])
        return run(["git", "-C", work, "rev-parse", "FETCH_HEAD"]).decode().strip()
    except RuntimeError:
        run(["git", "-C", work, "fetch", "-q", "--filter=blob:none", "--no-tags", "origin"])
        probe = subprocess.run(
            ["git", "-C", work, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"],
            capture_output=True,
        )
        if probe.returncode:
            raise RuntimeError(f"upstream revision not found: {ref}")
        return probe.stdout.decode().strip()


_WORK_CACHE = {}
_SHA_CACHE = {}
_WORK_DIRS = []


def _cleanup_works():
    for work in _WORK_DIRS:
        shutil.rmtree(work, ignore_errors=True)
    _WORK_DIRS.clear()
    _WORK_CACHE.clear()
    _SHA_CACHE.clear()


def reset_caches():
    """Drop per-run fetch state so a later command sees a mutated upstream."""
    _cleanup_works()


atexit.register(_cleanup_works)


def prepare_work(repo, ref, git_base):
    """Return (work_dir, sha) for one repo revision, fetching each revision once per run."""
    key = (repo, git_base, ref)
    if key in _WORK_CACHE:
        return _WORK_CACHE[key]

    work = tempfile.mkdtemp(prefix="sync-upstream-")
    _WORK_DIRS.append(work)
    run(["git", "init", "-q", work])
    run(["git", "-C", work, "remote", "add", "origin", f"{git_base}/{repo}.git"])
    sha = fetch_revision(work, ref)

    known = _SHA_CACHE.get((repo, git_base, sha))
    if known is not None:
        shutil.rmtree(work, ignore_errors=True)
        _WORK_DIRS.remove(work)
        _WORK_CACHE[key] = (known, sha)
        return known, sha

    _SHA_CACHE[(repo, git_base, sha)] = work
    _WORK_CACHE[key] = (work, sha)
    return work, sha


def github_files(repo, path, ref, git_base, exclude=()):
    """Return ({relative path: bytes}, resolved commit sha) for one repo directory.

    Blobs are prefetched in one request; a partial clone would otherwise fetch
    each file separately, which is minutes for a few dozen files.
    """
    work, sha = prepare_work(repo, ref, git_base)
    scope = [] if path.strip() in ("", ".") else ["--", path]
    listing = run(["git", "-C", work, "ls-tree", "-r", "--name-only", sha, *scope]).decode().splitlines()
    if not listing:
        raise RuntimeError(f"upstream path not found: {repo}/{path}@{ref}")

    listing = [item for item in listing if not _excluded(item, path, exclude)]
    if not listing:
        raise RuntimeError(f"every file excluded: {repo}/{path}@{ref}")

    oids = run(["git", "-C", work, "ls-tree", "-r", "--format=%(objectname)", sha, *scope]).decode().split()
    prefetch_blobs(work, [oid for oid in oids if oid])

    prefix = "" if path.strip() in ("", ".") else path.strip("/") + "/"
    files = {}
    for item in listing:
        relative = item[len(prefix):] if item.startswith(prefix) else item
        files[relative] = run(["git", "-C", work, "show", f"{sha}:{item}"])
    return files, sha


def _excluded(item, path, exclude):
    """Match a repo-relative path against exclude globs, also trying the skill-relative form."""
    if not exclude:
        return False
    from fnmatch import fnmatch

    prefix = "" if path.strip() in ("", ".") else path.strip("/") + "/"
    relative = item[len(prefix):] if item.startswith(prefix) else item
    for pattern in exclude:
        if fnmatch(item, pattern) or fnmatch(relative, pattern):
            return True
        if pattern.endswith("/") and (item.startswith(pattern) or relative.startswith(pattern)):
            return True
    return False


def prefetch_blobs(work, oids):
    """Fetch many blobs in one request so later reads stay local."""
    if not oids:
        return
    chunk = 400
    for start in range(0, len(oids), chunk):
        batch = oids[start:start + chunk]
        try:
            run(["git", "-C", work, "fetch", "-q", "--no-tags", "--no-write-fetch-head",
                 "origin", *batch])
        except RuntimeError:
            run(["git", "-C", work, "fetch", "-q", "--no-tags", "origin"])
            return


def npm_files(package, version, path, exclude=()):
    """Return ({relative path: bytes}, resolved version) for one package directory."""
    base = f"{NPM_REGISTRY}/{urllib.parse.quote(package, safe='@')}"
    meta = http_json(f"{base}/latest" if version in ("latest", None) else f"{base}/{version}")
    resolved = meta["version"]
    tarball_url = meta["dist"]["tarball"]
    payload = http_bytes(tarball_url)

    integrity = meta["dist"].get("integrity") or ""
    if integrity.startswith("sha512-"):
        digest = hashlib.sha512(payload).digest()
        if base64.b64encode(digest).decode() != integrity[len("sha512-"):]:
            raise RuntimeError(f"npm integrity mismatch: {package}@{resolved}")

    prefix = "package/" + path.strip("/") + "/"
    files = {}
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
        for member in archive.getmembers():
            if not member.isfile() or not member.name.startswith(prefix):
                continue
            relative = member.name[len(prefix):]
            if _excluded(relative, ".", exclude):
                continue
            handle = archive.extractfile(member)
            if handle is not None:
                files[relative] = handle.read()
    if not files:
        raise RuntimeError(f"upstream path not found: {package}@{resolved}/{path}")
    return files, resolved


def fetch(upstream, revision, git_base):
    if upstream.get("type") == "github":
        return github_files(upstream["repo"], upstream["path"], revision, git_base,
                            upstream.get("exclude") or ())
    if upstream.get("type") == "npm":
        return npm_files(upstream["package"], revision, upstream["path"],
                         upstream.get("exclude") or ())
    raise RuntimeError(f"unsupported upstream type: {upstream.get('type')!r}")


def pinned_revision(upstream):
    return upstream.get("ref") if upstream.get("type") == "github" else upstream.get("version")


def latest_revision(upstream, git_base):
    """Revision to fetch for the newest upstream state."""
    if upstream.get("type") == "github":
        return upstream.get("branch") or "HEAD"
    return "latest"


def local_files(skill_dir):
    files = {}
    for path in sorted(skill_dir.rglob("*")):
        if not path.is_file() or path.name in SKIP_NAMES:
            continue
        relative = path.relative_to(skill_dir)
        if "__pycache__" in relative.parts:
            continue
        files[relative.as_posix()] = path.read_bytes()
    return files


def is_binary(payload):
    return b"\0" in payload[:8000]


def merge3(local, base, upstream):
    """Three-way merge bytes via git merge-file. Returns (content, conflicted)."""
    if any(is_binary(payload) for payload in (local, base, upstream)):
        return None, True
    work = tempfile.mkdtemp(prefix="sync-merge-")
    try:
        names = {}
        for label, payload in (("local", local), ("base", base), ("upstream", upstream)):
            names[label] = os.path.join(work, label)
            with open(names[label], "wb") as handle:
                handle.write(payload)
        result = subprocess.run(
            ["git", "merge-file", "-p", "-L", "local", "-L", "base", "-L", "upstream",
             names["local"], names["base"], names["upstream"]],
            capture_output=True,
        )
        if result.returncode in (0, 1):
            return result.stdout, result.returncode == 1
        raise RuntimeError(result.stderr.decode("utf-8", "replace").strip())
    finally:
        shutil.rmtree(work, ignore_errors=True)


def plan(base, local, upstream):
    """Return list of (action, path, payload, note) for one skill."""
    changes = []
    for path in sorted(set(base) | set(local) | set(upstream)):
        in_base, in_local, in_up = path in base, path in local, path in upstream
        if in_base and in_local and in_up:
            if local[path] == base[path]:
                if upstream[path] != local[path]:
                    changes.append(("update", path, upstream[path], "fast-forward"))
            elif upstream[path] == base[path]:
                changes.append(("keep", path, local[path], "local edits kept"))
            else:
                merged, conflicted = merge3(local[path], base[path], upstream[path])
                if conflicted:
                    changes.append(("conflict", path, None, "both sides changed"))
                else:
                    changes.append(("merge", path, merged, "local edits merged"))
        elif in_base and in_local and not in_up:
            if local[path] == base[path]:
                changes.append(("delete", path, None, "upstream removed"))
            else:
                changes.append(("conflict", path, None, "upstream removed, local modified"))
        elif in_base and not in_local and in_up:
            if upstream[path] == base[path]:
                changes.append(("keep-deleted", path, None, "local deletion kept"))
            else:
                changes.append(("conflict", path, None, "local deleted, upstream modified"))
        elif not in_base and in_up and not in_local:
            changes.append(("add", path, upstream[path], "new upstream file"))
        elif not in_base and in_up and in_local:
            if local[path] == upstream[path]:
                changes.append(("keep", path, local[path], "identical"))
            else:
                changes.append(("conflict", path, None, "both added differently"))
        else:
            changes.append(("keep", path, local.get(path), "local only"))
    return changes


def tracked_skills(repo, only):
    data = json.loads((repo / "skills.json").read_text(encoding="utf-8"))
    selected = []
    for skill in data.get("skills", []):
        if not skill.get("upstream"):
            continue
        if only and skill["name"] not in only:
            continue
        selected.append(skill)
    return data, selected


def describe(change):
    action, path, _, note = change
    return f"  {action:<13} {path:<40} {note}"


def report(name, changes, verbose, header=True):
    actionable = [c for c in changes if c[0] not in ("keep", "keep-deleted")]
    if not actionable:
        if header:
            print(f"{name}: up to date")
        return
    if header:
        print(f"{name}: {len(actionable)} change(s)")
    for change in actionable:
        print(describe(change))
    if verbose:
        for change in changes:
            if change[0] in ("keep", "keep-deleted"):
                print(describe(change))


def parse_github_source(source):
    """Parse owner/repo, a GitHub URL, or a /tree/<ref>/<path> blob URL.

    Returns (repo, ref, path). repo is None when the source is unrecognized.
    """
    text = source.strip()
    match = re.fullmatch(
        r"(?:https?://(?:www\.)?github\.com/)?((?:[\w.-]+/)?[\w.-]+?)(?:\.git)?"
        r"(?:/(?:tree|blob)/([^/]+)(/[^?#]*)?)?/?",
        text,
    )
    if not match:
        return None, None, None
    repo_part, ref, rest = match.group(1), match.group(2), match.group(3) or ""
    tree_path = rest.strip("/")
    if tree_path.endswith("/SKILL.md"):
        tree_path = tree_path[: -len("/SKILL.md")]
    elif tree_path == "SKILL.md":
        tree_path = ""
    return repo_part, ref, tree_path or None


def cmd_import(repo, name, source, subpath, exclude, category, install, git_base, license_id=None):
    """Vendor a third-party skill into the repo and record its upstream pin."""
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", name):
        print(f"error: invalid skill name {name!r} (lowercase letters, digits, hyphens)", file=sys.stderr)
        return 2
    skill_dir = repo / name
    if skill_dir.exists():
        print(f"error: {name}/ already exists; use update for vendored skills", file=sys.stderr)
        return 2

    if source.startswith("npm:"):
        upstream = {"type": "npm", "package": source[len("npm:"):], "path": subpath or "."}
    else:
        repo_part, branch, tree_path = parse_github_source(source)
        if repo_part is None:
            print(f"error: unsupported source {source!r}; use owner/repo, a GitHub URL, or npm:<package>",
                  file=sys.stderr)
            return 2
        upstream = {"type": "github", "repo": repo_part, "path": subpath or tree_path or "."}
        if branch:
            upstream["ref"] = branch
    if exclude:
        upstream["exclude"] = exclude

    resolved = pinned_revision(upstream) if upstream.get("ref") or upstream.get("version") else "HEAD"
    files, revision = fetch(upstream, resolved, git_base)
    if "SKILL.md" not in files:
        print(f"error: no SKILL.md at {source}/{upstream['path']}", file=sys.stderr)
        return 2

    for relative, payload in files.items():
        target = skill_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    upstream["ref" if upstream["type"] == "github" else "version"] = revision
    upstream["license"] = license_id or lookup_license(repo, name, source)
    upstream["synced_at"] = date.today().isoformat()

    data = json.loads((repo / "skills.json").read_text(encoding="utf-8"))
    entry = {
        "name": name,
        "category": category,
        "description": frontmatter_description(skill_dir) or "",
        "files": sorted(files),
        "upstream": upstream,
    }
    data["skills"].append(entry)
    (repo / "skills.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"imported {name}: {len(files)} file(s) at {revision[:12]}")
    print("next: add a README entry, then run scripts/validate_repo.py")
    if install:
        mirror_installs(repo, {name: entry}, [name], prune=False)
    return 0


def lookup_license(repo, name, source):
    """Report the license when the upstream ships one; never guess."""
    skill_dir = repo / name
    for candidate in ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING"):
        path = skill_dir / candidate
        if path.is_file():
            head = path.read_text(encoding="utf-8", errors="replace")[:400].lower()
            for key, value in (("mit license", "MIT"), ("apache license", "Apache-2.0"),
                               ("gnu general public", "GPL"), ("creative commons", "CC"),
                               ("bsd", "BSD")):
                if key in head:
                    return value
    return "UNVERIFIED"


def frontmatter_description(skill_dir):
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return None
    lines = skill_md.read_text(encoding="utf-8", errors="replace").splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() == "---":
            return None
        if line.startswith("description:"):
            text = line.split(":", 1)[1].strip()
            return text.strip("'\"")[:300]
    return None


def cmd_check(repo, only, git_base):
    reset_caches()
    _, skills = tracked_skills(repo, only)
    drift = 0
    for skill in skills:
        upstream = skill["upstream"]
        base, base_rev = fetch(upstream, pinned_revision(upstream), git_base)
        latest, latest_rev = fetch(upstream, latest_revision(upstream, git_base), git_base)
        local = local_files(repo / skill["name"])
        changes = plan(base, local, latest)
        actionable = [c for c in changes if c[0] not in ("keep", "keep-deleted")]
        if latest != base:
            status = "drift"
        elif latest_rev != base_rev:
            status = "pin behind"
        else:
            status = "current"
        local_edits = sum(1 for c in changes if c[0] in ("keep", "merge", "conflict", "keep-deleted")
                          and c[1] in base)
        note = f", {local_edits} local edit(s)" if local_edits else ""
        print(f"{skill['name']}: {status} (pinned {base_rev[:12]}, latest {latest_rev[:12]}{note})")
        if actionable:
            drift += 1
            report(skill["name"], changes, verbose=True, header=False)
        elif status == "pin behind":
            drift += 1
    return 1 if drift else 0


def update_files_list(skill_dir, entry):
    entry["files"] = sorted(local_files(skill_dir))


def cmd_update(repo, only, apply, install, prune, git_base):
    reset_caches()
    data, skills = tracked_skills(repo, only)
    if not skills:
        print("no skill declares an upstream block", file=sys.stderr)
        return 2

    conflicts = 0
    changed = []
    pending = 0
    for skill in skills:
        name = skill["name"]
        upstream = skill["upstream"]
        skill_dir = repo / name
        base, base_rev = fetch(upstream, pinned_revision(upstream), git_base)
        latest, latest_rev = fetch(upstream, latest_revision(upstream, git_base), git_base)
        local = local_files(skill_dir)
        changes = plan(base, local, latest)

        actionable = [c for c in changes if c[0] not in ("keep", "keep-deleted")]
        if not actionable:
            if latest_rev != base_rev and apply:
                upstream["ref" if upstream["type"] == "github" else "version"] = latest_rev
                upstream["synced_at"] = date.today().isoformat()
                changed.append(name)
                print(f"{name}: content unchanged, pin advanced {base_rev[:12]} -> {latest_rev[:12]}")
            else:
                print(f"{name}: up to date ({base_rev[:12]})")
            continue

        pending += 1
        report(name, changes, verbose=True)
        skill_conflicts = [c for c in changes if c[0] == "conflict"]
        if skill_conflicts:
            conflicts += len(skill_conflicts)
            print(f"{name}: skipped, resolve conflicts first (pin left at {base_rev[:12]})")
            continue
        if not apply:
            continue

        for action, path, payload, _ in changes:
            target = skill_dir / path
            if action in ("update", "merge", "add"):
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(payload)
            elif action == "delete":
                target.unlink(missing_ok=True)

        upstream["ref" if upstream["type"] == "github" else "version"] = latest_rev
        upstream["synced_at"] = date.today().isoformat()
        update_files_list(skill_dir, skill)
        changed.append(name)
        print(f"{name}: applied -> {latest_rev[:12]}")

    if not apply:
        print("\ndry run: rerun with --apply to write changes")
        return 1 if pending or conflicts else 0

    if changed:
        (repo / "skills.json").write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(f"\nupdated skills.json for: {', '.join(changed)}")

    if install and changed:
        mirror_installs(repo, {s["name"]: s for s in skills}, changed, prune)
    return 1 if conflicts else 0


def frontmatter_name(skill_dir):
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return None
    lines = skill_md.read_text(encoding="utf-8", errors="replace").splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() == "---":
            return None
        if line.startswith("name:"):
            return line.split(":", 1)[1].strip().strip("'\"")
    return None


def resolve_install_target(root, name):
    """Find the install directory for a skill: directory name first, then frontmatter name."""
    direct = root / name
    if direct.is_dir():
        return direct
    for candidate in sorted(root.iterdir()):
        if candidate.is_dir() and frontmatter_name(candidate) == name:
            return candidate
    return None


def mirror_installs(repo, skills, changed, prune=False):
    """Mirror updated skills into an existing local install directory.

    The repository is the source of truth; this only refreshes copies that a host
    made by hand. Symlinked installs already track the repository and are skipped.
    """
    root = Path(os.environ.get("SKILL_INSTALL_DIR", "~/.cc-switch/skills")).expanduser()
    if not root.is_dir():
        print(f"install: skipped (no directory at {root})")
        return
    for name in changed:
        target = resolve_install_target(root, name)
        if target is None:
            print(f"install: skipped {name} (no installed copy under {root})")
            continue
        if target.is_symlink():
            print(f"install: skipped {name} (symlink at {target}; link already tracks the source)")
            continue
        source = repo / name
        wanted = set()
        for path in sorted(source.rglob("*")):
            if not path.is_file() or path.name in SKIP_NAMES or "__pycache__" in path.parts:
                continue
            relative = path.relative_to(source)
            wanted.add(relative)
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
        pruned = 0
        if prune:
            for path in sorted(target.rglob("*")):
                if not path.is_file() or path.name in SKIP_NAMES or "__pycache__" in path.parts:
                    continue
                if path.relative_to(target) not in wanted:
                    path.unlink()
                    pruned += 1
        suffix = f", pruned {pruned} stale file(s)" if pruned else ""
        print(f"install: synced {name} -> {target}{suffix}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=["check", "update", "import"])
    parser.add_argument("--skill", action="append", default=[], help="limit to one skill (repeatable)")
    parser.add_argument("--apply", action="store_true", help="write changes and update skills.json")
    parser.add_argument("--install", action="store_true", help="mirror applied skills into CC_SWITCH_SKILLS")
    parser.add_argument("--prune", action="store_true", help="with --install, delete files absent from the repo copy")
    parser.add_argument("--source", help="import: owner/repo, GitHub URL, or npm:<package>")
    parser.add_argument("--name", help="import: local skill directory name (defaults to the upstream basename)")
    parser.add_argument("--path", help="import: directory inside the source (default: repo/package root)")
    parser.add_argument("--exclude", action="append", default=[], help="import: glob to skip (repeatable)")
    parser.add_argument("--category", default="uncategorized", help="import: skills.json category")
    parser.add_argument("--license", dest="license_id",
                        help="import: license id when the source ships no LICENSE file")
    parser.add_argument("--git-base", default=os.environ.get("SYNC_UPSTREAM_GIT_BASE", DEFAULT_GIT_BASE),
                        help="git host for github upstreams (default: https://github.com)")
    parser.add_argument("--repo", default=str(Path(__file__).resolve().parent.parent))
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    try:
        if args.command == "import":
            if not args.source:
                parser.error("import requires --source")
            name = args.name or import_name(args.source, args.path)
            return cmd_import(repo, name, args.source, args.path, args.exclude,
                              args.category, args.install, args.git_base, args.license_id)
        if args.command == "check":
            return cmd_check(repo, set(args.skill), args.git_base)
        return cmd_update(repo, set(args.skill), args.apply, args.install, args.prune, args.git_base)
    except (RuntimeError, urllib.error.URLError, KeyError, tarfile.TarError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


GENERIC_DIR_NAMES = {"skill", "skills", "src", "source", "dist", "package", "lib"}


def import_name(source, path):
    """Derive a skill directory name from the source and its subdirectory."""
    derived = None
    if path and path.strip("/") not in ("", "."):
        derived = path.rstrip("/").split("/")[-1].lower()
    else:
        _, _, tree_path = parse_github_source(source)
        if tree_path:
            derived = tree_path.rstrip("/").split("/")[-1].lower()
    if derived and derived not in GENERIC_DIR_NAMES:
        return derived

    # A generic leaf ("skill", "skills") is not a usable directory name; use the source name.
    if source.startswith("npm:"):
        return re.sub(r"[^a-z0-9-]+", "-", source[len("npm:"):].lower()).strip("-")
    repo_part, _, _ = parse_github_source(source)
    base = (repo_part or source).rstrip("/").split("/")[-1]
    return re.sub(r"[^a-z0-9-]+", "-", base.lower()).strip("-")


if __name__ == "__main__":
    raise SystemExit(main())
