import test from 'node:test';
import assert from 'node:assert/strict';

import {
  formatResearchPoint,
  normalizeResearchRun,
  normalizePayload,
  normalizeWorkbenchPayload,
  researchRunStatus,
  selectPoint,
  selectWorkbenchPoint,
  previewWorkbenchParameter,
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

const runPayload = {
  schema_version: 1,
  run_id: 'run-ui',
  state: 'LEARNING_RECORDED',
  mode: 'OFFLINE',
  paper_only: true,
  as_of: '2026-10-01',
  decision_eligible: true,
  analysts: [{ role: 'technical', status: 'READY' }],
  missing_analysts: [],
  report_links: { complete: '/research/run-ui/report/complete' },
};

test('research run status covers loading, success, partial, blocked, and error', () => {
  assert.equal(researchRunStatus(null), 'LOADING');
  const ready = normalizeResearchRun(runPayload);
  assert.equal(researchRunStatus(ready), 'READY');
  assert.equal(researchRunStatus(normalizeResearchRun({ ...runPayload, missing_analysts: ['news'] })), 'PARTIAL');
  assert.equal(researchRunStatus(normalizeResearchRun({ ...runPayload, state: 'VALIDATION_FAILED', decision_eligible: false })), 'BLOCKED');
  assert.equal(researchRunStatus(ready, new Error('offline failure')), 'ERROR');
});

test('research run payload rejects non-offline or non-paper boundaries', () => {
  assert.throws(() => normalizeResearchRun({ ...runPayload, paper_only: false }), /boundary/i);
  assert.throws(() => normalizeResearchRun({ ...runPayload, state: 'UNKNOWN' }), /state/i);
});

const workbench = {
  schema_version: 1,
  view: 'factor-strategy-workbench',
  run_id: 'fixture-workbench-v1',
  paper_only: true,
  points: [
    { point_id: 'p-1', time: '2026-01-01T00:00:00Z', instrument: 'AAA', score: 0.2, signal: true, raw_weight: 1, risk_scale: 1, final_weight: 1, held_weight: 0, exposure: 1, cash: 0, risk_state: 'NORMAL', trade_weight: 0, fees: 0, slippage: 0, gross_return: 0, net_return: 0, equity: 1, drawdown: 0, fault_events: [] },
  ],
  metrics: { total_return: 0 },
  provenance: { dataset_fingerprint: 'dataset', policy_fingerprint: 'policy' },
  factor_observations: [], signals: [], raw_weights: [], risk_scales: [], final_weights: [], exposure: [], cash: [], risk_states: [], trades: [], costs: [], slippage: [], fault_events: [], explanation_refs: [], baseline_variant_refs: [], limitations: [],
};

test('normalizeWorkbenchPayload validates paper-only server-owned layers', () => {
  const normalized = normalizeWorkbenchPayload(workbench);
  assert.equal(normalized.points[0].held_weight, 0);
  assert.equal(normalized.provenance.policy_fingerprint, 'policy');
  assert.throws(() => normalizeWorkbenchPayload({ ...workbench, paper_only: false }), /paper/i);
  assert.throws(() => normalizeWorkbenchPayload({ ...workbench, points: [{ ...workbench.points[0], net_return: NaN }] }), /finite/i);
});

test('selectWorkbenchPoint and previewWorkbenchParameter keep interaction render-only', () => {
  const normalized = normalizeWorkbenchPayload(workbench);
  assert.equal(selectWorkbenchPoint(normalized, 'p-1').risk_state, 'NORMAL');
  assert.equal(selectWorkbenchPoint(normalized, 'missing'), null);
  const root = { dataset: {} };
  const preview = previewWorkbenchParameter(root, 'lookback', 40);
  assert.deepEqual(preview, { parameter: 'lookback', value: 40, saved: false });
  assert.equal(root.dataset.workbenchPreview, JSON.stringify(preview));
});
