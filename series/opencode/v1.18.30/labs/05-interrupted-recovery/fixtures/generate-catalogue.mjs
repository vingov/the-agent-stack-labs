// Deliberately exposes the interval between two related writes. It never rolls back.
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { existsSync } from 'node:fs';
import { readFile, rename, writeFile } from 'node:fs/promises';
import { dirname, isAbsolute, join, relative, resolve } from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';
import { fileURLToPath } from 'node:url';
import { normalizeLabel } from './labels.mjs';

async function main() {
  const workspace = dirname(fileURLToPath(import.meta.url));
  assert.equal(resolve(process.cwd()), workspace, 'Run from the fixture workspace');
  const control = process.env.LAB_CONTROL_DIR;
  const nonce = process.env.LAB_RUN_NONCE;
  assert.ok(control && isAbsolute(control), 'Absolute control directory required');
  assert.match(nonce ?? '', /^[a-f0-9]{32}$/);
  const rel = relative(workspace, resolve(control));
  assert.ok(rel.startsWith('..') || isAbsolute(rel), 'Control state must be outside the workspace');
  const lifetime = Number(process.env.LAB_GENERATOR_TIMEOUT_MS ?? 180000);
  assert.ok(Number.isInteger(lifetime) && lifetime >= 100 && lifetime <= 300000);
  for (const name of ['ready.json', 'release.json', 'stop.json']) {
    assert.equal(existsSync(join(control, name)), false, 'Fresh coordination state required');
  }
  const input = JSON.parse(await readFile('source-data.json', 'utf8'));
  assert.ok(Array.isArray(input) && input.every(value => typeof value === 'string'));
  const bytes = JSON.stringify({ labels: input.map(normalizeLabel) }, null, 2) + '\n';
  await writeFile('catalogue.json', bytes, 'utf8');
  const ready = JSON.stringify({ nonce, pid: process.pid, stage: 'catalogue-written' }) + '\n';
  await writeFile(join(control, 'ready.tmp'), ready, { encoding: 'utf8', flag: 'wx' });
  await rename(join(control, 'ready.tmp'), join(control, 'ready.json'));
  process.stdout.write('CATALOGUE_WRITTEN\n');
  const deadline = performance.now() + lifetime;
  async function marked(name) {
    const path = join(control, name);
    if (!existsSync(path)) return false;
    assert.equal(JSON.parse(await readFile(path, 'utf8')).nonce, nonce);
    return true;
  }
  while (performance.now() < deadline) {
    if (await marked('stop.json')) {
      process.exitCode = 75; // Explicit harness cleanup, not runtime cancellation.
      return;
    }
    if (await marked('release.json')) {
      const manifest = {
        algorithm: 'sha256',
        catalogueSha256: createHash('sha256').update(bytes).digest('hex'),
      };
      await writeFile('catalogue.manifest.json', JSON.stringify(manifest, null, 2) + '\n', 'utf8');
      process.stdout.write('MANIFEST_WRITTEN\n');
      return;
    }
    await delay(40);
  }
  process.exitCode = 76; // Fixture fail-safe; no manifest write or rollback.
}

await main();
