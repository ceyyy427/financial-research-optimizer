import { performance } from 'node:perf_hooks';
import { normalizePayload, selectPoint } from '../src/research.js';

function payload(size) {
  const points = Array.from({ length: size }, (_, index) => {
    const close = 100 + (index % 31) * 0.1;
    return {
      id: `DEMO-${index}`,
      time: new Date(Date.UTC(2026, 0, 1 + index)).toISOString(),
      open: close - 0.2,
      high: close + 0.4,
      low: close - 0.5,
      close,
      volume: 1000 + index,
      features: { return_1d: index ? 0.001 : 0, range_pct: 0.009 },
      events: index === 0 ? ['fixture-start'] : [],
    };
  });
  return {
    schema_version: 1,
    dataset: { id: `perf-${size}`, fingerprint: 'a'.repeat(64), mode: 'SAMPLE' },
    points,
    events: [{ id: 'fixture-start', label: 'Fixture start' }],
    features: [],
    limitations: ['Synthetic parser benchmark; not a browser paint measurement.'],
  };
}

function measure(size) {
  const raw = payload(size);
  const start = performance.now();
  const normalized = normalizePayload(raw);
  const selected = selectPoint(normalized.points, `DEMO-${Math.floor(size / 2)}`);
  const elapsedMs = performance.now() - start;
  if (!selected) throw new Error(`selection failed for ${size}`);
  if (elapsedMs > 2000) throw new Error(`normalization exceeded 2s for ${size}: ${elapsedMs}`);
  return { size, elapsed_ms: Number(elapsedMs.toFixed(3)), selected_id: selected.id };
}

console.log(JSON.stringify({ status: 'PASS', measurements: [measure(1000), measure(10000)] }));
