import test from 'node:test';
import assert from 'node:assert/strict';
import { formatLabel } from './labels.mjs';

test('trim outer whitespace', () => assert.equal(formatLabel('  North Star \t'), 'North Star'));
test('preserve repeated interior spaces', () => assert.equal(formatLabel('  North  Star  '), 'North  Star'));
test('keep a normalized label', () => assert.equal(formatLabel('North Star'), 'North Star'));
test('keep empty input', () => assert.equal(formatLabel(''), ''));
