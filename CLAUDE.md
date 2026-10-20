

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

`my-skills` is source repo for portable Agent Skills. Each top-level directory containing `SKILL.md` is one distributable skill. Skills install per skill (Claude Code: `~/.claude/skills/<skill-name>/`); Codex plugins install via the local marketplace. Registry name is `vlong-skills` (`skills.json`); marketplace name is `vlong-skills-local` (`.agents/plugins/marketplace.json`).

**This repository is the single source of truth.** Host skill directories are symlink mounts; `~/.cc-switch/skills` is a legacy copy location, not a source. Install with `python3 scripts/install_skills.py link`; never `cp` a skill into a host directory, and never author skills in `~/.cc-switch/skills`.

No workflow runtime or test harness exists in this repo. Repository scripts: `scripts/validate_repo.py` (consistency checks), `scripts/sync_upstream.py` (third-party skill import/update), `scripts/install_skills.py` (symlink skills into hosts), `scripts/test_sync_upstream.py` (offline updater tests). Do not document or invoke missing commands.

## Structure

- `skills.json`: repository metadata and public skill registry.
- `<skill-name>/SKILL.md`: required skill definition.
- `<skill-name>/references/`, `scripts/`, `assets/`: optional skill resources.
- `plugins/<plugin-name>/`: installable Codex plugin packages.
- `.agents/plugins/marketplace.json`: repository plugin marketplace catalog; local plugin paths resolve relative to repository root.
- `skills.json` `category`: discovery and classification metadata only, never a path resolver.
- `README.md`: public skill list and usage overview.

## Commands

```bash
jq empty skills.json                          # validate registry JSON
python3 scripts/validate_repo.py              # registry/marketplace/path/contract checks
python3 scripts/sync_upstream.py check        # third-party skill drift (exit 1 = drift)
python3 scripts/sync_upstream.py update --apply
python3 scripts/sync_upstream.py import --source <owner/repo|URL|npm:pkg>   # vendor + pin
python3 scripts/install_skills.py status      # host link coverage
python3 scripts/install_skills.py link        # symlink repo skills into hosts
python3 scripts/test_sync_upstream.py         # offline updater tests
git diff --check                              # whitespace/conflict check
```

For new/changed skills, also run Skill Creator `quick_validate.py` when available (needs Python with `PyYAML`). For resource scripts, run focused script tests. For source migrations, compare migrated files byte-for-byte when exact preservation is required.

## Third-Party Skills

Vendored skills declare an `upstream` block in `skills.json` (`type`, source coordinates, pinned `ref`/`version`, `license`, `synced_at`, optional `exclude`). `scripts/sync_upstream.py` does a three-way merge with the pin as merge base: unchanged-local takes upstream, unchanged-upstream keeps local, both-changed merges via `git merge-file`, and a conflict skips that skill without touching files or advancing the pin. Binary files never merge — both sides changed is a conflict. Never hand-edit a pinned revision; advance it through `update --apply`, which also refreshes `files` and `synced_at`. Vendor new skills with `import --source <owner/repo|GitHub URL|npm:pkg>`, never by hand. A skill whose body only forwards to another skill needs that dependency vendored plus `"depends_on": ["<name>"]`. Keep `license` accurate.

## Code Navigation

If repo root contains `.codegraph/`, use CodeGraph before `rg`/`find`/broad reads:

```bash
codegraph explore "<symbol or question>"
```

Skip entirely if `.codegraph/` absent — indexing is user's call.

## Skill Changes

Follow portable Agent Skills layout.

- Skill folder name: lowercase letters/digits/hyphens, max 64 chars.
- `SKILL.md` frontmatter: prefer only `name` + `description` for portable skills. Preserve intentional legacy fields on existing skills unless the task requires migration.
- `description`: state capability and trigger conditions; put operational workflow in the body.
- `README.md` per skill is optional — don't create one just to satisfy the installer.
- Add reusable scripts only when deterministic execution or real reuse warrants them; test every script added.
- Register every shipped skill in `skills.json`; keep `files` list accurate and remove entries for absent skill directories.
- Update root `README.md` when the public skill list changes.
- Preserve source skill behavior during migrations — don't restore files a later source revision removed.

## CodexRadar Skill

- Treat CodexRadar as third-party empirical source, not OpenAI-official benchmark.
- Recommend only OpenAI Codex model/effort combinations present in current measured data.
- Fetch current page and community-rating endpoint; never reuse remembered measurements.
- Keep latest rolling rating distinct from 15-day historical context.
- Do not map Anthropic, Google, local, or uncovered models to Codex IQ values.
- Treat configuration changes as separate action. Preserve unrelated settings and respect target scope.

## Worktree Safety

Repo may contain unrelated uncommitted work. Preserve it — inspect overlapping diffs before editing, never reset/delete user changes.

## Response Style

Respond terse, like a smart caveman. Keep all technical substance; cut fluff only.

- Drop articles, filler (just/really/basically), pleasantries, hedging.
- Fragments OK. Short synonyms. Technical terms exact. Code stays unchanged.
- Pattern: `[thing] [action] [reason]. [next step].`
- Switch level: `/caveman lite|full|ultra|wenyan`. Stop: "stop caveman" or "normal mode".
- Drop caveman automatically for security warnings, irreversible actions, or user confusion; resume after.
- Code, commits, and PR text are always written normal (not caveman-style).

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
