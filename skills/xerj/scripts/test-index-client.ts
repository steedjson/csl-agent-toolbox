import { test, expect } from 'bun:test';
import { createHash } from 'node:crypto';
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { indexClient } from './index-client';

test('repair is optional, checks both binaries, and rejects malformed manifests', () => {
  const storage = mkdtempSync(join(tmpdir(), 'xerj-client-test-'));
  try {
    const native = join(storage, 'native');
    writeFileSync(native, 'native');
    expect(indexClient(storage, native)).toBe(native);
    const hash = (s: string) => createHash('sha256').update(s).digest('hex');
    const manifest = { schema: 1, native_sha256: hash('native'), client_sha256: hash('client') };
    const dir = join(storage, 'index-client', manifest.client_sha256);
    const client = join(dir, 'xerj-index-client');
    const meta = join(storage, 'index-client/manifest.json');
    mkdirSync(dir, { recursive: true });
    writeFileSync(client, 'client');
    writeFileSync(meta, JSON.stringify(manifest));
    expect(indexClient(storage, native)).toBe(client);
    writeFileSync(native, 'new-native');
    expect(() => indexClient(storage, native)).toThrow('XERJ changed');
    writeFileSync(native, 'native');
    writeFileSync(client, 'changed-client');
    expect(() => indexClient(storage, native)).toThrow('checksum mismatch');
    rmSync(client);
    expect(() => indexClient(storage, native)).toThrow();
    writeFileSync(meta, JSON.stringify({ ...manifest, client_sha256: '../elsewhere' }));
    expect(() => indexClient(storage, native)).toThrow('invalid');
    writeFileSync(meta, '{');
    expect(() => indexClient(storage, native)).toThrow();
  } finally { rmSync(storage, { recursive: true, force: true }); }
});
