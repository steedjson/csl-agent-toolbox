# Repository Instructions

## Purpose

`csl-agent-toolbox` is a personal source collection for Agent Skills, MCP packages, and native agent plugins. Keep original and third-party components together, distinguished by provenance metadata. Each top-level directory containing `SKILL.md` is one distributable skill.

## Source Of Truth

This repository is the single source for every skill and plugin. Host skill directories (`~/.claude/skills`, `~/.codex/skills`, `~/.agents/skills`, `~/.dsh/skills`, `~/.pi/agent/skills`, `~/.omp/agent/skills`, `~/.zcode/skills`, `~/cow/skills`) are symlink mounts, not sources. `~/.cc-switch/skills` is a legacy copy location and is not a source either.

**Install location policy**: by default a skill installs into the target agent's own skills directory (`~/.claude/skills`, `~/.codex/skills`, `~/.omp/agent/skills`, `~/.pi/agent/skills`, `~/.zcode/skills`, `~/cow/skills`, `~/.dsh/skills`). The user-level cross-tool directory `~/.agents/skills` is used ONLY when the user explicitly says "用户级" / "装到用户级目录" — never mount or link it by default, and never point it at the repository on your own initiative. omp discovers skills from its own directory plus user-level/project `.agents` walk-up; when omp needs a skill, link it into `~/.omp/agent/skills` (`--host omp`), not the user-level directory.

- Never install into an agent on your own initiative. Installing happens only when the user names the target agent ("装到 codex"). Until then, `import` / `update` / sync write repository files only and never touch host skill directories. When the user does ask, run `python3 scripts/install_skills.py link --skill <name> --host <agent>` (symlink, never copy); check coverage with `status`, remove with `unlink`.
- Never `cp` a skill into a host directory: a copy detaches from the repository and silently goes stale.
- Edit skills here, in place. Changes reach every host immediately through the links.
- Do not add, edit, or delete skills in `~/.cc-switch/skills`. If a skill exists only there, vendor it here first, then relink.

## Structure

- `skills.json`: sole component catalog (`skills`, `plugins`, `mcps`); filename remains for compatibility.
- `<skill-name>/SKILL.md`: required skill definition.
- `<skill-name>/references/`, `scripts/`, `assets/`: optional skill resources.
- `plugins/<plugin-name>/`: host-native plugin packages; manifest determines compatibility.
- `mcp/<name>/mcp.json`: one portable MCP server configuration package.
- `.agents/plugins/marketplace.json`: repository plugin marketplace catalog; local plugin paths resolve relative to repository root.
- `skills.json` `category`: discovery and classification metadata only, never a path resolver.
- `README.md`: public skill list and usage overview.
- `codexradar-model-advisor/`: current OpenAI Codex model-advice skill.

Entry point: `python3 scripts/toolbox.py` (`list`, `hosts`, `status`, `install`, `uninstall`, `import`, `check`, `update`). Reuse `scripts/install_skills.py` for Skill links and `scripts/sync_upstream.py` for three-way upstream merges. Offline tests: `python3 -m unittest discover -s scripts -p 'test_*.py'`. Do not document commands that do not exist.

`install` / `uninstall` require named hosts and components; never infer a target or install after import/update. `--host agents` explicitly selects shared user-level Skills. MCP and plugins have host-specific user configuration, not a universal shared install directory. Unknown adapters fail before writes. Preserve unrelated host config, keep credentials out of the repository/output, and use native CLIs when supported. See `docs/installation.md` for verified adapters and limits.

## Code Navigation

When repository root contains `.codegraph/`, use CodeGraph before `rg`, `find`, or broad file reads:

```bash
codegraph explore "<symbol or question>"
```

Skip CodeGraph completely when `.codegraph/` is absent. User decides whether to create index.

## Skill Changes

Follow portable Agent Skills layout.

- Skill folder name: lowercase letters, digits, hyphens; maximum 64 characters.
- `SKILL.md` frontmatter: prefer only `name` and `description` for portable skills. Preserve intentional legacy fields in existing skills unless task requires migration.
- A skill adapted from an unpinnable source (a gist, an article, a chat) carries a `source_note` field in its `skills.json` entry recording what was adapted, when, and which parts are original. `source_note` is provenance memory, not a sync contract; it never replaces `upstream` (which is for pinnable sources).
- `description`: state capability and trigger conditions. Put operational workflow in body.
- `README.md`: optional. Do not create auxiliary docs solely to satisfy installer.
- Add reusable scripts only when deterministic execution or meaningful reuse warrants them. Test every added script.
- Register every shipped skill in `skills.json`; keep `files` list accurate and remove entries for absent skill directories.
- Keep standalone Skill packages flat at repository root; category metadata in `skills.json` does not control paths.
- Update root `README.md` when public skill list or install commands change.
- Preserve source skill behavior during migrations. Do not restore files removed by later source revisions.

## Third-Party Components

Vendored components declare an `upstream` block in `skills.json` (`type`, source coordinates, pinned `ref`/`version`, `license`, `synced_at`, optional `exclude`). `scripts/sync_upstream.py` performs the three-way merge; the pin doubles as the merge base. Use `--kind skill|plugin|mcp`; default remains `skill` for the legacy script. `toolbox.py check/update` defaults to all registered upstream kinds. Self-developed entries have no upstream and are skipped.

- Vendor with `python3 scripts/sync_upstream.py import --source <owner/repo|GitHub URL|npm:pkg> [--path ...] [--exclude ...]`. It writes files and records the pin in one step; never copy files in by hand, because an unrecorded pin makes local edits indistinguishable from upstream changes.
- Never hand-edit a pinned `ref`/`version`. Advance it with `python3 scripts/sync_upstream.py update --apply`, which also refreshes the `files` list and `synced_at`.
- Local adaptations are allowed and expected; they survive updates as long as they do not collide with the same upstream hunk. Collisions abort that skill and leave files untouched. Binary files never merge: both sides changed means conflict.
- A skill that delegates to another skill (its body is only `Call the Skill tool with "<name>"`) needs that dependency vendored too and declared as `"depends_on": ["<name>"]`; `validate_repo.py` checks the reference resolves.
- Check before adding a new third-party skill: record the upstream coordinates and pin the revision actually vendored, then run `check` to confirm a clean baseline.
- Keep the upstream `license` field accurate; do not vendor sources whose license forbids redistribution.

## CodexRadar Skill

- Treat CodexRadar as third-party empirical source, not OpenAI-official benchmark.
- Recommend only OpenAI Codex model/effort combinations present in current measured data.
- Fetch current page and community-rating endpoint; never reuse remembered measurements.
- Keep latest rolling rating distinct from 15-day historical context.
- Do not map Anthropic, Google, local, unknown, or uncovered models to Codex IQ values.
- Treat configuration changes as separate action. Preserve unrelated settings and respect target scope.

## Verification

Run checks proportional to change:

```bash
jq empty skills.json
git diff --check
```

For new or changed skills, also run Skill Creator `quick_validate.py` when available. Use Python environment containing `PyYAML`.

For resource scripts, run focused script tests. For source migrations, compare migrated files byte-for-byte when exact preservation is required.

For plugin changes, validate `plugins/<plugin-name>/` with Plugin Creator `validate_plugin.py`, then confirm hook activation in a new Codex task after re-trusting hooks. Source validation does not prove installed-cache activation.

## Worktree Safety

Repository may contain unrelated uncommitted work. Preserve it. Inspect overlapping diffs before editing; never reset or delete user changes.

## Response Style

Respond terse like smart caveman. All technical substance stay. Only fluff die.

Rules:
- Drop: articles (a/an/the), filler (just/really/basically), pleasantries, hedging
- Fragments OK. Short synonyms. Technical terms exact. Code unchanged.
- Pattern: [thing] [action] [reason]. [next step].
- Not: "Sure! I'd be happy to help you with that."
- Yes: "Bug in auth middleware. Fix:"

Switch level: /caveman lite|full|ultra|wenyan
Stop: "stop caveman" or "normal mode"

Auto-Clarity: drop caveman for security warnings, irreversible actions, user confused. Resume after.

Boundaries: code/commits/PRs written normal.

## BUGLOG — 已知坑与修法(跨 agent 共享)

- 位置:`docs/BUGLOG/<当前分支>.md`(按分支一文件;分支名 `/`→`-`;无 git 用 `default.md`)
- **读的时机**:修改函数签名/对外行为前;审查 diff 前;fix 类提交前。通读最近 30 条及命中模块条目
- **写的时机**:修复缺陷并确认根因后,立即追加一条(最新在上):

  ```md
  ## [YYYY-MM-DD][模块] 简述
  - 现象: / - 根因: / - 修法: / - 关联: commit 或 文件:行号
  - 复发: N 次 · 最近 日期(可选) / - 教训: 一句话
  ```

- **脱敏红线**:禁止客户名/真实姓名/内网地址/凭证,用 `<占位符>` 替代
- 文件不存在则先创建标准头;条目只追加不删改
