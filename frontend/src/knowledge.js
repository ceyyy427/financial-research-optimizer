import katex from 'katex';

function requiredText(value, field) {
  if (typeof value !== 'string' || value.trim() === '') throw new TypeError(`${field} is required`);
  return value;
}

export function normalizeKnowledgePayload(payload) {
  if (!payload || payload.schema_version !== 1 || !payload.unit) throw new TypeError('knowledge payload schema is invalid');
  const unit = payload.unit;
  requiredText(unit.unit_id, 'unit id');
  requiredText(unit.title, 'unit title');
  if (!Array.isArray(unit.equations)) throw new TypeError('knowledge equations are invalid');
  const equationIds = new Set();
  const equations = unit.equations.map((equation, index) => {
    requiredText(equation.equation_id, `equation ${index} id`);
    if (equationIds.has(equation.equation_id)) throw new TypeError('knowledge equation ids must be unique');
    equationIds.add(equation.equation_id);
    requiredText(equation.latex, `equation ${index} latex`);
    return { ...equation };
  });
  if (!Array.isArray(unit.code_segments)) throw new TypeError('knowledge code segments are invalid');
  const codeIds = new Set();
  const codeSegments = unit.code_segments.map((segment, index) => {
    requiredText(segment.segment_id, `code segment ${index} id`);
    if (codeIds.has(segment.segment_id)) throw new TypeError('knowledge code segment ids must be unique');
    codeIds.add(segment.segment_id);
    if (!Array.isArray(segment.line_range) || segment.line_range.length !== 2) throw new TypeError('code line range is invalid');
    return { ...segment, line_range: [...segment.line_range] };
  });
  const context = payload.context && typeof payload.context === 'object' ? { ...payload.context } : { status: 'NO_CONTEXT_AVAILABLE', binding: null };
  if (!['AVAILABLE', 'NO_CONTEXT_AVAILABLE'].includes(context.status)) throw new TypeError('knowledge context status is invalid');
  return { ...payload, schema_version: 1, unit: { ...unit, equations, code_segments: codeSegments }, context };
}

export function renderKnowledgeEquation(equation) {
  requiredText(equation?.latex, 'equation latex');
  return katex.renderToString(equation.latex, { displayMode: true, throwOnError: false, output: 'htmlAndMathml' });
}

export function selectCodeSegment(segments, segmentId) {
  const segment = segments.find((item) => item.segment_id === segmentId);
  if (!segment) throw new Error(`knowledge code segment not found: ${segmentId}`);
  return segment;
}

function renderLineButtons(root, segments) {
  const target = root.querySelector('[data-knowledge-code-lines]');
  const inspector = root.querySelector('[data-knowledge-code-inspector]');
  if (!target) return;
  target.textContent = '';
  segments.forEach((segment) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'knowledge-code-line';
    button.dataset.segmentId = segment.segment_id;
    button.textContent = `${segment.line_range[0]}–${segment.line_range[1]}  ${segment.code}`;
    button.addEventListener('click', () => {
      target.querySelectorAll('[aria-current="true"]').forEach((item) => item.removeAttribute('aria-current'));
      button.setAttribute('aria-current', 'true');
      if (inspector) inspector.textContent = `${segment.data_input} → ${segment.data_output}`;
      root.dispatchEvent(new CustomEvent('finathink:code-selected', { bubbles: true, detail: { segmentId: segment.segment_id, equationIds: segment.equation_ids ?? [] } }));
    });
    target.appendChild(button);
  });
}

export function mountKnowledge(root, { payload, payloadUrl } = {}) {
  const load = payload ? Promise.resolve(payload) : fetch(payloadUrl || root.dataset.payloadUrl).then((response) => {
    if (!response.ok) throw new Error(`knowledge payload request failed (${response.status})`);
    return response.json();
  });
  return load.then((raw) => {
    const normalized = normalizeKnowledgePayload(raw);
    const whyNow = root.querySelector('[data-knowledge-why-now]');
    if (whyNow && normalized.context.status === 'AVAILABLE') whyNow.textContent = normalized.context.binding.why_now;
    normalized.unit.equations.forEach((equation) => {
      const target = root.querySelector(`[data-knowledge-equation="${CSS.escape(equation.equation_id)}"]`);
      if (target) target.innerHTML = renderKnowledgeEquation(equation);
    });
    renderLineButtons(root, normalized.unit.code_segments);
    return normalized;
  }).catch((error) => {
    const target = root.querySelector('[data-knowledge-error]') || root;
    target.textContent = `Knowledge rendering unavailable: ${error.message}`;
    target.hidden = false;
    target.setAttribute('role', 'alert');
    throw error;
  });
}

if (typeof document !== 'undefined') {
  document.querySelectorAll('[data-finathink-knowledge]').forEach((root) => { mountKnowledge(root); });
}
