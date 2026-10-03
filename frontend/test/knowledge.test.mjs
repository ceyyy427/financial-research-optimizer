import test from 'node:test';
import assert from 'node:assert/strict';
import { normalizeKnowledgePayload, renderKnowledgeEquation, selectCodeSegment } from '../src/knowledge.js';

const payload = {
  schema_version: 1,
  unit: {
    unit_id: 'sharpe',
    title: 'Sharpe Ratio',
    equations: [{ equation_id: 'sharpe-formula', latex: '\\frac{r-rf}{sigma}', mathml: '<math></math>' }],
    code_segments: [{ segment_id: 'sharpe-code', line_range: [1, 1], code: 'sharpe = mean_excess / volatility' }],
  },
  context: { status: 'NO_CONTEXT_AVAILABLE', binding: null },
};

test('normalizes knowledge payload and rejects duplicate equations', () => {
  const normalized = normalizeKnowledgePayload(payload);
  assert.equal(normalized.unit.unit_id, 'sharpe');
  assert.equal(selectCodeSegment(normalized.unit.code_segments, 'sharpe-code').segment_id, 'sharpe-code');
  assert.throws(() => normalizeKnowledgePayload({ ...payload, unit: { ...payload.unit, equations: [...payload.unit.equations, payload.unit.equations[0]] } }), /equation/);
});

test('renders local equation markup and rejects unknown code selections', () => {
  assert.match(renderKnowledgeEquation(payload.unit.equations[0]), /frac|math/);
  assert.throws(() => selectCodeSegment(payload.unit.code_segments, 'missing'), /code segment/);
});
