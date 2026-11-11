#!/usr/bin/env node
// Copyright (c) 2026 Kubai087. Licensed under the Kubai Icons License; see LICENSE.
// Packs the skill for release, from a committed revision so stray local edits never ship:
//   dist/kubai-icons-v<version>.zip           the standard skill (Claude Code, claude.ai)
//   dist/kubai-icons-v<version>-platform.zip  the same skill for marketplaces that read the
//                                             metadata fields at the top of the frontmatter
//
//   node scripts/pack.mjs [--ref HEAD] [--out dist]
//
// The version comes from metadata.version in SKILL.md. Needs git and zip.
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const args = process.argv.slice(2);
const opt = (name, fallback) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : fallback; };
const ref = opt('--ref', 'HEAD');
const out = path.resolve(opt('--out', path.join(root, 'dist')));

// What the skill needs at run time; the README media, history and repository tooling stay out.
const FILES = ['SKILL.md', 'PROMPT.md', 'LICENSE', 'README.md', 'index.html', 'src', 'scripts/check.mjs', 'scripts/export.mjs'];

const git = (...a) => execFileSync('git', ['-C', root, ...a], { encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 });
const skill = git('show', `${ref}:SKILL.md`);
const front = skill.match(/^---\n([\s\S]*?)\n---\n/);
if (!front) throw new Error('SKILL.md has no frontmatter.');
const meta = front[1].match(/^metadata:\n((?: {2}.*\n?)+)/m);
if (!meta) throw new Error('SKILL.md has no metadata block.');
const version = meta[1].match(/^ {2}version: "?([^"\n]+)"?$/m)?.[1];
if (!version) throw new Error('SKILL.md has no metadata.version.');

const work = fs.mkdtempSync(path.join(os.tmpdir(), 'kubai-icons-pack-'));
try {
  fs.mkdirSync(out, { recursive: true });
  const name = `kubai-icons-v${version}`;
  const standard = path.join(out, `${name}.zip`);
  const platform = path.join(out, `${name}-platform.zip`);
  fs.rmSync(standard, { force: true });
  fs.rmSync(platform, { force: true });
  git('archive', '--format=zip', '--prefix=kubai-icons/', '-o', standard, ref, ...FILES);

  // The platform copy lifts every metadata field to the top level of the frontmatter.
  const tar = path.join(work, 'skill.tar');
  git('archive', '--format=tar', '--prefix=kubai-icons/', '-o', tar, ref, ...FILES);
  execFileSync('tar', ['-xf', tar, '-C', work]);
  const lifted = meta[1].split('\n').filter(Boolean).map((line) => line.slice(2)).join('\n') + (meta[0].endsWith('\n') ? '\n' : '');
  const flat = skill.replace(front[0], `---\n${front[1].replace(meta[0], lifted)}\n---\n`);
  fs.writeFileSync(path.join(work, 'kubai-icons', 'SKILL.md'), flat);
  execFileSync('zip', ['-q', '-r', '-X', platform, 'kubai-icons'], { cwd: work });

  for (const file of [standard, platform]) console.log(`${path.relative(root, file)}: ${(fs.statSync(file).size / 1024).toFixed(0)} KB`);
} finally {
  fs.rmSync(work, { recursive: true, force: true });
}
