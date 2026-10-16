import test from 'node:test';
import assert from 'node:assert/strict';
import { formatLabel } from './labels.mjs';

test('trim outer whitespace', () => assert.equal(formatLabel('  North Hall \t'), 'North Hall'));
test('preserve interior spaces', () => assert.equal(formatLabel('  North  Hall  '), 'North  Hall'));
test('keep a normalized label', () => assert.equal(formatLabel('North Hall'), 'North Hall'));
test('keep empty input', () => assert.equal(formatLabel(''), ''));
