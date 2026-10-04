import { test } from 'node:test';
import assert from 'node:assert/strict';
import { slug } from './slug.mjs';

test('single space', () => assert.equal(slug('Hello World'), 'hello-world'));
test('repeated whitespace', () => assert.equal(slug(' Hello  World '), 'hello-world'));
test('tab', () => assert.equal(slug('Hello\tWorld'), 'hello-world'));
