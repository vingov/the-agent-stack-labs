import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import { normalizeLabel } from './labels.mjs';

test('preserves meaningful interior spaces', () => {
  assert.equal(normalizeLabel('Beta  Gamma'), 'Beta  Gamma');
});
test('trims outer whitespace', () => {
  assert.equal(normalizeLabel('  Alpha  '), 'Alpha');
});
test('normalizes an all-whitespace label', () => {
  assert.equal(normalizeLabel('\t \n'), '');
});
test('preserves the empty label', () => {
  assert.equal(normalizeLabel(''), '');
});
test('catalogue has the intended label values', async () => {
  assert.deepEqual(JSON.parse(await readFile('catalogue.json', 'utf8')), {
    labels: ['Alpha', 'Beta  Gamma', 'Delta'],
  });
});
test('manifest identifies the actual catalogue bytes', async () => {
  const bytes = await readFile('catalogue.json');
  const manifest = JSON.parse(await readFile('catalogue.manifest.json', 'utf8'));
  assert.deepEqual(manifest, {
    algorithm: 'sha256', catalogueSha256: createHash('sha256').update(bytes).digest('hex'),
  });
});
