#!/usr/bin/env python3
"""Build a pinned HTTP-only autoindex client. Never replace the native server.

Source: xerj-org/xerj@3f6aefa8d00f16bad714256998afff922ddfbdb7 (Apache-2.0).
Pass an extracted, trusted upstream source tree. Cargo downloads locked deps.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

COMMIT = '3f6aefa8d00f16bad714256998afff922ddfbdb7'
BEFORE = 'e6388f3da8d636abe417744f14ea0b72681c67c260b601f213fbf71de08d551b'
AFTER = '06a6f49e9436f72addd75cc1bc8016fd43c99d1ef3ca5850c2ea4489fd92c4af'
ROUTE_BEFORE = '3af288862687e80aab93e47a10b83d2007143bdbce3b77dd389363bb71ed8d9e'
ROUTE_AFTER = 'a5d2d33ee0f7374c8fbdbb482db746aa072698f87f4f0dd5d627112c641d60d2'
BIN = '\n[[bin]]\nname = "xerj-index-client"\npath = "src/index_client_main.rs"\n'
MAIN = 'fn main() { std::process::exit(xerj_autoindex::run_cli()); }\n'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    if len(sys.argv) != 2:
        raise SystemExit('Usage: build-index-client.py <trusted-upstream-source-root>')
    source = Path(sys.argv[1]).resolve(strict=True)
    native = Path.home() / '.bun/bin/xerj'
    if subprocess.check_output([str(native), '--version'], text=True).strip() != 'xerj v1.0.0-rc.101':
        raise SystemExit('This patch requires native XERJ rc.101; revalidate on upgrades')
    native_hash = digest(native)
    sync = source / 'engine/crates/xerj-autoindex/src/sync.rs'
    patch = Path(__file__).with_name('group-split.patch')
    route = sync.with_name('reconcile_plan.rs')
    hashes = (digest(sync), digest(route))
    if hashes == (BEFORE, ROUTE_BEFORE):
        subprocess.run(['patch', '-p1', '-i', str(patch.resolve())], cwd=source, check=True)
    if (digest(sync), digest(route)) != (AFTER, ROUTE_AFTER):
        raise SystemExit('Unexpected autoindex sources; use the pinned upstream source')
    crate = sync.parent.parent
    manifest = crate / 'Cargo.toml'
    text = manifest.read_text()
    if 'name = "xerj-index-client"' not in text:
        manifest.write_text(text + BIN)
    (sync.parent / 'index_client_main.rs').write_text(MAIN)
    cargo = ['cargo', '--locked', '--manifest-path', str(source / 'engine/Cargo.toml'),
             '-p', 'xerj-autoindex']
    # All reconciliation invariants, including the reproducer, must pass before installation.
    for suite in ['sync::tests', 'reconcile_plan::tests']:
        subprocess.run([cargo[0], 'test', *cargo[1:], '--lib', suite, '-j', '2'], check=True)
    subprocess.run([cargo[0], 'build', *cargo[1:], '--bin', 'xerj-index-client', '-j', '2',
                    '--config', 'profile.dev.package.xerj-autoindex.opt-level=2'], check=True)
    binary = source / 'engine/target/debug/xerj-index-client'
    storage = Path.home() / 'Library/Application Support/xerj'
    with (storage / 'lifecycle.flock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if digest(native) != native_hash:
            raise SystemExit('Native XERJ changed during build; retry against the installed version')
        install = storage / 'index-client'
        install.mkdir(mode=0o700, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.build-', dir=install) as stage_dir:
            stage = Path(stage_dir)
            client = stage / 'xerj-index-client'
            shutil.copy2(binary, client)
            subprocess.run(['/usr/bin/strip', '-x', str(client)], check=True)
            client_hash = digest(client)
            shutil.copy2(source / 'LICENSE', stage / 'LICENSE')
            data = {'schema': 1, 'source_commit': COMMIT, 'native_sha256': native_hash,
                    'client_sha256': client_hash, 'patch_sha256': digest(patch)}
            (stage / 'provenance.json').write_text(json.dumps(data, indent=2) + '\n')
            release = install / client_hash
            if not release.exists():
                os.rename(stage, release)
            meta = install / '.manifest.tmp'
            meta.write_text(json.dumps(data, indent=2) + '\n')
            os.replace(meta, install / 'manifest.json')
        print(f'Installed HTTP-only index client: {release}')


if __name__ == '__main__':
    main()
