/**
 * app.js — plain JavaScript, no framework, no build step.
 *
 * The whole app is: one object holding all the data ("state"), and one
 * function that redraws the page to match that data ("render"). Every
 * time something happens (a button click, a server response), we update
 * `state`, then call `render()` again. That's the entire mental model —
 * no virtual DOM, no components, just "data changes -> redraw."
 */
 
// ---------- STATE ----------
// tickets: array of { ticketId, inputText, phase, data, wentThroughReview, error }
// phase is one of: "submitting" | "pending_review" | "reviewing" | "resolved" | "error"
const state = {
  tickets: [],
  selectedId: null,
};
 
// ---------- API CALLS ----------
// Same-origin now (frontend and backend are served by the same FastAPI
// app), so these are just plain relative fetch() calls — no CORS, no
// base URL config needed at all.
 
async function apiSubmitTicket(text) {
  const res = await fetch('/tickets', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${res.status})`);
  }
  return res.json();
}
 
async function apiReviewTicket(ticketId, decision) {
  const res = await fetch(`/tickets/${ticketId}/review`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(decision),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${res.status})`);
  }
  return res.json();
}
 
// ---------- HELPERS ----------
function findTicket(id) {
  return state.tickets.find((t) => t.ticketId === id) || null;
}
 
function updateTicket(id, patch) {
  const t = findTicket(id);
  if (t) Object.assign(t, patch);
}
 
function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}
 
// ---------- EVENT HANDLERS ----------
async function handleSubmit() {
  const input = document.getElementById('ticket-input');
  const text = input.value.trim();
  if (!text) return;
 
  const tempId = `pending-${Date.now()}`;
  state.tickets.unshift({
    ticketId: tempId,
    inputText: text,
    phase: 'submitting',
    data: null,
    wentThroughReview: false,
  });
  state.selectedId = tempId;
  input.value = '';
  render();
 
  try {
    const data = await apiSubmitTicket(text);
    updateTicket(tempId, {
      ticketId: data.ticket_id,
      data,
      phase: data.status === 'resolved' ? 'resolved' : 'pending_review',
    });
    state.selectedId = data.ticket_id;
  } catch (err) {
    updateTicket(tempId, { phase: 'error', error: err.message });
  }
  render();
}
 
async function handleDecide(decision) {
  const ticket = findTicket(state.selectedId);
  if (!ticket) return;
  const id = ticket.ticketId;
 
  updateTicket(id, { phase: 'reviewing' });
  render();
 
  try {
    const data = await apiReviewTicket(id, decision);
    updateTicket(id, {
      data,
      phase: data.status === 'resolved' ? 'resolved' : 'pending_review',
      wentThroughReview: true,
    });
  } catch (err) {
    updateTicket(id, { phase: 'error', error: err.message });
  }
  render();
}
 
function selectTicket(id) {
  state.selectedId = id;
  render();
}
 
// ---------- EXAMPLE TICKETS ----------
const EXAMPLES = [
  { label: 'Small refund', text: 'I was charged twice for my subscription, customer id cust_001, please refund the duplicate' },
  { label: 'Large refund', text: 'I need a 2000 refund, customer id cust_002, the product never worked' },
  { label: 'Technical issue', text: 'The app keeps crashing whenever I try to upload a photo' },
  { label: 'Account deletion', text: 'Please delete my account entirely, customer id cust_005' },
];
 
function renderExampleButtons() {
  const container = document.getElementById('example-buttons');
  container.innerHTML = EXAMPLES.map(
    (ex, i) => `<button class="example-btn" data-example="${i}">${escapeHtml(ex.label)}</button>`
  ).join('');
  container.querySelectorAll('[data-example]').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.getElementById('ticket-input').value = EXAMPLES[btn.dataset.example].text;
    });
  });
}
 
// ---------- RENDER: history list ----------
const STATUS_LABEL = {
  submitting: 'processing',
  pending_review: 'needs review',
  reviewing: 'submitting decision',
  resolved: 'resolved',
  error: 'error',
};
 
function renderHistory() {
  const container = document.getElementById('ticket-history');
  if (state.tickets.length === 0) {
    container.innerHTML = '<p class="muted small">Nothing yet — submit a ticket to see it appear here.</p>';
    return;
  }
  container.innerHTML = state.tickets.map((t) => `
    <button class="ticket-item ${t.ticketId === state.selectedId ? 'selected' : ''}" data-ticket="${t.ticketId}">
      <p>${escapeHtml(t.inputText)}</p>
      <p class="ticket-status mono muted">${STATUS_LABEL[t.phase]}${t.data && t.data.category ? ' · ' + t.data.category : ''}</p>
    </button>
  `).join('');
  container.querySelectorAll('[data-ticket]').forEach((btn) => {
    btn.addEventListener('click', () => selectTicket(btn.dataset.ticket));
  });
}
 
// ---------- RENDER: pipeline trace (the signature piece) ----------
const NODES = [
  { id: 'ingest', label: 'ingest', x: 240, y: 60 },
  { id: 'triage', label: 'triage', x: 240, y: 140 },
  { id: 'account', label: 'account', x: 80, y: 230 },
  { id: 'billing', label: 'billing', x: 240, y: 230 },
  { id: 'technical', label: 'technical', x: 400, y: 230 },
  { id: 'risk_check', label: 'risk_check', x: 240, y: 320 },
  { id: 'human_review', label: 'human_review', x: 240, y: 410 },
  { id: 'apply_decision', label: 'apply_decision', x: 240, y: 490 },
  { id: 'output_validate', label: 'output_validate', x: 240, y: 570 },
  { id: 'end', label: 'end', x: 240, y: 640 },
];
 
const EDGES = [
  ['ingest', 'triage'],
  ['triage', 'account'], ['triage', 'billing'], ['triage', 'technical'], ['triage', 'human_review'],
  ['account', 'risk_check'], ['billing', 'risk_check'], ['technical', 'risk_check'],
  ['risk_check', 'human_review'], ['risk_check', 'output_validate'],
  ['human_review', 'apply_decision'],
  ['apply_decision', 'output_validate'],
  ['output_validate', 'end'],
];
 
const SPECIALISTS = ['account', 'billing', 'technical'];
 
const COLORS = {
  idle:    { fill: '#12141a', stroke: '#232733', text: '#8a8f9c' },
  active:  { fill: '#1c1836', stroke: '#8b7ff6', text: '#e8e9ed' },
  done:    { fill: '#123028', stroke: '#4ade9e', text: '#e8e9ed' },
  waiting: { fill: '#2e2210', stroke: '#f0a868', text: '#e8e9ed' },
  skipped: { fill: '#0d0f14', stroke: '#1a1d26', text: '#4a4e58' },
};
 
// This mirrors the REAL routing logic in graph/router.py — same
// branches, same conditions — so a node only lights up when the actual
// graph would have visited it.
function computeStatuses(ticket) {
  const idle = {};
  NODES.forEach((n) => (idle[n.id] = 'idle'));
  if (!ticket) return idle;
 
  if (ticket.phase === 'submitting') {
    return { ...idle, ingest: 'active', triage: 'active' };
  }
 
  const category = ticket.data && ticket.data.category;
  const wentViaSpecialist = category && SPECIALISTS.includes(category);
  const s = { ...idle, ingest: 'done', triage: 'done' };
 
  SPECIALISTS.forEach((spec) => {
    s[spec] = wentViaSpecialist && spec === category ? 'done' : 'skipped';
  });
 
  const isPaused = ticket.phase === 'pending_review';
  const isReviewing = ticket.phase === 'reviewing';
  const isResolved = ticket.phase === 'resolved';
 
  if (wentViaSpecialist) {
    s.risk_check = 'done';
    if (isPaused) s.human_review = 'waiting';
    else if (isReviewing) s.human_review = 'active';
    else if (isResolved && ticket.wentThroughReview) {
      s.human_review = 'done'; s.apply_decision = 'done';
      s.output_validate = 'done'; s.end = 'done';
    } else if (isResolved) {
      s.human_review = 'skipped'; s.apply_decision = 'skipped';
      s.output_validate = 'done'; s.end = 'done';
    }
  } else {
    s.risk_check = 'skipped';
    if (isPaused) s.human_review = 'waiting';
    else if (isReviewing) s.human_review = 'active';
    else if (isResolved) {
      s.human_review = 'done'; s.apply_decision = 'done';
      s.output_validate = 'done'; s.end = 'done';
    }
  }
  return s;
}
 
function renderPipelineTrace() {
  const ticket = findTicket(state.selectedId);
  const statuses = computeStatuses(ticket);
  const svg = document.getElementById('pipeline-svg');
 
  const edgeEls = EDGES.map(([from, to]) => {
    const a = NODES.find((n) => n.id === from);
    const b = NODES.find((n) => n.id === to);
    const aDone = statuses[from] === 'done' || statuses[from] === 'active';
    const bLit = statuses[to] !== 'idle' && statuses[to] !== 'skipped';
    const lit = aDone && bLit;
    return `<line x1="${a.x}" y1="${a.y + 16}" x2="${b.x}" y2="${b.y - 16}" stroke="${lit ? '#4a4470' : '#1a1d26'}" stroke-width="1.5" />`;
  }).join('');
 
  const nodeEls = NODES.map((n) => {
    const status = statuses[n.id];
    const c = COLORS[status];
    const pulsing = status === 'active' || status === 'waiting';
    return `
      <g transform="translate(${n.x}, ${n.y})">
        <rect class="node-rect ${pulsing ? 'pulsing' : ''}" x="-56" y="-16" width="112" height="32" rx="7"
              fill="${c.fill}" stroke="${c.stroke}" stroke-width="1.5" />
        <text x="0" y="4" text-anchor="middle" fill="${c.text}" font-family="JetBrains Mono, monospace" font-size="11">${n.label}</text>
      </g>`;
  }).join('');
 
  svg.innerHTML = edgeEls + nodeEls;
  document.getElementById('trace-ticket-id').textContent = ticket ? ticket.ticketId.slice(0, 8) : '';
}
 
// ---------- RENDER: detail panel + review form ----------
function renderDetailPanel() {
  const container = document.getElementById('detail-panel');
  const ticket = findTicket(state.selectedId);
 
  // ALWAYS remove any existing review panel first — it was inserted as a
  // sibling, not inside `container`, so redrawing `container` alone
  // never cleaned it up. This is the fix for the "box stays visible
  // after resolution" bug.
  document.querySelectorAll('.review-panel').forEach((el) => el.remove());
 
  if (!ticket) {
    container.innerHTML = '<p class="muted small center">Submit a ticket, or select one from the list, to see its detail here.</p>';
    return;
  }
 
  const d = ticket.data;
  let html = `
    <h2>TICKET DETAIL</h2>
    <dl class="detail-grid">
      <dt>id</dt><dd>${escapeHtml(ticket.ticketId)}</dd>
      <dt>status</dt><dd>${escapeHtml((d && d.status) || ticket.phase)}</dd>
      ${d && d.category ? `<dt>category</dt><dd>${escapeHtml(d.category)}</dd>` : ''}
      ${d && d.confidence != null ? `<dt>confidence</dt><dd>${d.confidence.toFixed(2)}</dd>` : ''}
    </dl>
    ${d && d.resolution ? `<div class="resolution-box">${escapeHtml(d.resolution)}</div>` : ''}
    ${ticket.error ? `<div class="error-box">${escapeHtml(ticket.error)}</div>` : ''}
  `;
  container.innerHTML = html;
 
  const needsReview = d && d.review_needed && (ticket.phase === 'pending_review' || ticket.phase === 'reviewing');
  if (needsReview) {
    renderReviewForm(d.review_needed, ticket.phase === 'reviewing');
  }
}
 
function renderReviewForm(review, submitting) {
  const wrapper = document.createElement('div');
  wrapper.className = 'panel review-panel';
  wrapper.style.marginTop = '16px';

  const hasAction = !!review.proposed_action;
  const isRefund = hasAction && review.proposed_action.tool === 'issue_refund';

  wrapper.innerHTML = `
    <div class="review-header">
      <span class="review-dot pulsing"></span>
      <h2>AWAITING YOUR REVIEW</h2>
    </div>
    <p class="small" style="margin-bottom:12px;">${escapeHtml(review.reason)}</p>
    ${hasAction ? `
      <div class="action-box">
        <p class="tool-name">${escapeHtml(review.proposed_action.tool)}</p>
        <pre>${escapeHtml(JSON.stringify(review.proposed_action.args, null, 2))}</pre>
      </div>
      <button class="btn btn-resolved" id="approve-btn" ${submitting ? 'disabled' : ''}>Approve</button>
      ${isRefund ? `
        <div class="edit-row">
          <input class="key" id="edit-key" placeholder="argument" value="amount" />
          <input id="edit-value" placeholder="new value" />
          <button class="btn btn-outline-agent" id="edit-btn" ${submitting ? 'disabled' : ''}>Edit & approve</button>
        </div>
      ` : ''}
      <button class="btn btn-outline-reject" id="reject-btn" style="margin-top:8px;" ${submitting ? 'disabled' : ''}>Reject</button>
    ` : `
      <p class="muted small" style="margin-bottom:8px;">No specific action was proposed — write a reply directly.</p>
      <textarea id="manual-reply" rows="3" placeholder="Type a reply to send the customer…"></textarea>
      <button class="btn btn-primary" id="manual-btn" ${submitting ? 'disabled' : ''}>Send reply</button>
    `}
  `;
 
  document.getElementById('detail-panel').after(wrapper);
 
  if (hasAction) {
    document.getElementById('approve-btn').addEventListener('click', () => handleDecide({ action: 'approve' }));
    document.getElementById('reject-btn').addEventListener('click', () => handleDecide({ action: 'reject' }));
    if (isRefund) {
      document.getElementById('edit-btn').addEventListener('click', () => {
        const key = document.getElementById('edit-key').value;
        const rawValue = document.getElementById('edit-value').value;
        if (!rawValue) return;
        const num = Number(rawValue);
        const args = { ...review.proposed_action.args };
        args[key] = Number.isNaN(num) ? rawValue : num;
        handleDecide({ action: 'edit', edited_action: { tool: review.proposed_action.tool, args } });
      });
    }
  } else {
    document.getElementById('manual-btn').addEventListener('click', () => {
      const text = document.getElementById('manual-reply').value.trim();
      if (!text) return;
      handleDecide({ action: 'manual_resolution', text });
    });
  }
}
 
// ---------- MAIN RENDER ----------
function render() {
  const submitBtn = document.getElementById('submit-btn');
  const isSubmitting = state.tickets.some((t) => t.phase === 'submitting');
  submitBtn.disabled = isSubmitting;
  submitBtn.textContent = isSubmitting ? 'Processing…' : 'Submit ticket';
 
  renderHistory();
  renderPipelineTrace();
  renderDetailPanel();
}
 
// ---------- INIT ----------
document.getElementById('submit-btn').addEventListener('click', handleSubmit);
renderExampleButtons();
render();
 
