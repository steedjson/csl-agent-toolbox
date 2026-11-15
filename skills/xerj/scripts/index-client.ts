import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const sha256 = (path: string) => createHash('sha256').update(readFileSync(path)).digest('hex');

// Keep the format-4 server intact; the patched public client only speaks HTTP.
export function indexClient(storage: string, native: string): string {
  let manifest;
  try { manifest = JSON.parse(readFileSync(join(storage, 'index-client/manifest.json'), 'utf8')); }
  catch (error) { if (error.code === 'ENOENT') return native; throw error; }
  if (manifest.schema !== 1 || !/^[a-f0-9]{64}$/.test(manifest.native_sha256)
      || !/^[a-f0-9]{64}$/.test(manifest.client_sha256)) {
    throw new Error('invalid XERJ index-client manifest');
  }
  if (sha256(native) !== manifest.native_sha256) {
    throw new Error('XERJ changed; revalidate/rebuild the index client before indexing');
  }
  const client = join(storage, 'index-client', manifest.client_sha256, 'xerj-index-client');
  if (sha256(client) !== manifest.client_sha256) throw new Error('XERJ index-client checksum mismatch');
  return client;
}
