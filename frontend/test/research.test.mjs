import test from 'node:test';
import assert from 'node:assert/strict';

import {
  formatResearchPoint,
  normalizePayload,
  selectPoint,
} from '../src/research.js';

const payload = {
  schema_version: 1,
  dataset: { id: 'fixture', fingerprint: 'abc123', mode: 'SAMPLE' },
  points: [
    {
      id: 'p-1', time: '2026-01-01T00:00:00Z', open: 10, high: 12, low: 9,
      close: 11, volume: 100, features: { momentum: 0.2 }, events: ['cpi'], signal: 'WATCH',
    },
  ],
  features: [{ id: 'momentum', label: 'Momentum' }],
  events: [{ id: 'cpi', label: 'CPI release' }],
  limitations: ['fixture only'],
};

test('normalizePayload preserves provenance and rejects malformed chart records', () => {
  const normalized = normalizePayload(payload);
  assert.equal(normalized.dataset.fingerprint, 'abc123');
  assert.equal(normalized.points[0].id, 'p-1');
  assert.throws(() => normalizePayload({ ...payload, points: [{ ...payload.points[0], close: NaN }] }), /finite|invalid/i);
  assert.throws(() => normalizePayload({ ...payload, dataset: { id: 'fixture' } }), /fingerprint/i);
});

test('normalizePayload rejects duplicate point identity or timestamps', () => {
  const duplicateId = { ...payload.points[0], time: '2026-01-02T00:00:00Z' };
  assert.throws(() => normalizePayload({ ...payload, points: [payload.points[0], duplicateId] }), /unique/i);
  const duplicateTime = { ...payload.points[0], id: 'p-2' };
  assert.throws(() => normalizePayload({ ...payload, points: [payload.points[0], duplicateTime] }), /unique/i);
});

test('selectPoint returns the exact canonical point without recomputing values', () => {
  const normalized = normalizePayload(payload);
  assert.equal(selectPoint(normalized.points, 'p-1').close, 11);
  assert.equal(selectPoint(normalized.points, 'missing'), null);
});

test('formatResearchPoint exposes a keyboard/table-friendly research summary', () => {
  const point = normalizePayload(payload).points[0];
  const text = formatResearchPoint(point, { cpi: 'CPI release' });
  assert.match(text, /2026-01-01/);
  assert.match(text, /Close 11/);
  assert.match(text, /Momentum 0\.2/);
  assert.match(text, /CPI release/);
});
