/* ═══════════════════════════════════════════════════════════════════════════
   Benki Control Dashboard — app.js
   Polls /api/* endpoints and updates the DOM live.
   ═══════════════════════════════════════════════════════════════════════════ */

'use strict';

// ── Intervals ─────────────────────────────────────────────────────────────
const POLL_STATUS    = 10_000;   // 10 s  — agent health
const POLL_TRADES    = 30_000;   // 30 s  — trade feed
const POLL_RISK      = 30_000;   // 30 s  — risk log
const POLL_PNL       = 60_000;   // 60 s  — P&L chart
const POLL_SENTIMENT = 60_000;   // 60 s  — sentiment briefs
const POLL_CRON      = 15_000;   // 15 s  — cron logs
const POLL_LLM       = 60_000;   // 60 s  — llm usage

// ── Helpers ───────────────────────────────────────────────────────────────

/**
 * Fetch JSON from a local endpoint; returns null on failure.
 */
async function fetchJSON(url) {
  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn(`[benki-ui] fetch ${url} failed:`, err.message);
    return null;
  }
}

/** Format ISO timestamp → "HH:MM:SS" relative label */
function fmtTime(isoStr) {
  if (!isoStr) return '—';
  try {
    return new Date(isoStr).toLocaleTimeString();
  } catch (_) { return '—'; }
}

/** Format a number as USD */
function fmtUSD(val) {
  if (val == null || val === '') return '—';
  const n = parseFloat(val);
  if (isNaN(n)) return '—';
  return (n >= 0 ? '+' : '') + n.toLocaleString('en-US', {
    style: 'currency', currency: 'USD', maximumFractionDigits: 2,
  });
}

function fmtPct(val) {
  if (val == null) return '—';
  return parseFloat(val).toFixed(2) + '%';
}

function el(id) { return document.getElementById(id); }

// ── Clock ─────────────────────────────────────────────────────────────────
function startClock() {
  const clockEl = el('clock');
  function tick() {
    clockEl.textContent = new Date().toLocaleTimeString('en-US', { hour12: false });
  }
  tick();
  setInterval(tick, 1000);
}

// ══════════════════════════════════════════════════════════════════════════
// Agent Status
// ══════════════════════════════════════════════════════════════════════════
async function refreshStatus() {
  const agents = await fetchJSON('/api/status');
  if (!agents) return;

  let onlineCount = 0;

  agents.forEach((agent) => {
    const { id, status, latencyMs, httpStatus, lastChecked, error } = agent;

    // Card border class
    const card = el(`card-${id}`);
    if (card) {
      card.className = `agent-card ${status}`;
    }

    // Status pill
    const pill = el(`pill-${id}`);
    if (pill) {
      pill.className = `status-pill ${status}`;
    }

    const dot = el(`dot-${id}`);
    if (dot) dot.className = `status-dot ${status}`;

    const statusEl = el(`status-${id}`);
    if (statusEl) statusEl.textContent = status.charAt(0).toUpperCase() + status.slice(1);

    const latEl = el(`latency-${id}`);
    if (latEl) latEl.textContent = latencyMs != null ? `${latencyMs} ms` : '—';

    const httpEl = el(`http-${id}`);
    if (httpEl) httpEl.textContent = httpStatus ?? '—';

    const seenEl = el(`seen-${id}`);
    if (seenEl) seenEl.textContent = fmtTime(lastChecked);

    // Error message
    const errEl = el(`err-${id}`);
    if (errEl) {
      if (error && status === 'offline') {
        errEl.textContent = error;
        errEl.classList.remove('hidden');
      } else {
        errEl.classList.add('hidden');
      }
    }

    if (status === 'online') onlineCount++;
  });

  // Overall system badge
  const total = agents.length;
  const sysDot    = el('systemDot');
  const sysStatus = el('systemStatus');
  const sysBadge  = el('systemBadge');

  if (onlineCount === total) {
    sysDot.className = 'pulse-dot online';
    sysStatus.textContent = 'All Systems Online';
    sysBadge.style.borderColor = 'rgba(16,185,129,0.3)';
  } else if (onlineCount === 0) {
    sysDot.className = 'pulse-dot offline';
    sysStatus.textContent = 'All Agents Offline';
    sysBadge.style.borderColor = 'rgba(239,68,68,0.3)';
  } else {
    sysDot.className = 'pulse-dot degraded';
    sysStatus.textContent = `${onlineCount}/${total} Agents Online`;
    sysBadge.style.borderColor = 'rgba(245,158,11,0.3)';
  }

  el('agentLastUpdated').textContent = 'Updated ' + new Date().toLocaleTimeString();
}

// ══════════════════════════════════════════════════════════════════════════
// P&L Chart
// ══════════════════════════════════════════════════════════════════════════
let pnlChart = null;

function buildPnlChart(labels, realized, ending) {
  const ctx = el('pnlChart').getContext('2d');
  const gradient = ctx.createLinearGradient(0, 0, 0, 220);
  gradient.addColorStop(0, 'rgba(0, 212, 255, 0.25)');
  gradient.addColorStop(1, 'rgba(0, 212, 255, 0)');

  if (pnlChart) pnlChart.destroy();

  pnlChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Realized P&L',
          data: realized,
          borderColor: '#00d4ff',
          backgroundColor: gradient,
          borderWidth: 2,
          pointRadius: 3,
          pointBackgroundColor: '#00d4ff',
          fill: true,
          tension: 0.35,
        },
        {
          label: 'Portfolio Value',
          data: ending,
          borderColor: '#7c3aed',
          borderWidth: 1.5,
          borderDash: [4, 4],
          pointRadius: 2,
          pointBackgroundColor: '#7c3aed',
          fill: false,
          tension: 0.35,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 600 },
      plugins: {
        legend: {
          labels: { color: '#94a3b8', font: { size: 11 }, boxWidth: 12 },
        },
        tooltip: {
          backgroundColor: 'rgba(13,18,32,0.95)',
          borderColor: 'rgba(255,255,255,0.1)',
          borderWidth: 1,
          titleColor: '#f1f5f9',
          bodyColor: '#94a3b8',
          callbacks: {
            label: (ctx) => ` ${ctx.dataset.label}: ${fmtUSD(ctx.raw)}`,
          },
        },
      },
      scales: {
        x: {
          ticks: { color: '#475569', font: { size: 10 }, maxTicksLimit: 8 },
          grid:  { color: 'rgba(255,255,255,0.04)' },
        },
        y: {
          ticks: {
            color: '#475569',
            font: { size: 10 },
            callback: (v) => '$' + (v / 1000).toFixed(1) + 'k',
          },
          grid: { color: 'rgba(255,255,255,0.04)' },
        },
      },
    },
  });
}

async function refreshPnl() {
  const rows = await fetchJSON('/api/pnl');
  const totalEl = el('pnlTotal');
  const emptyEl = el('pnlEmpty');

  if (!rows || rows.length === 0) {
    totalEl.textContent = '—';
    emptyEl.classList.remove('hidden');
    if (pnlChart) { pnlChart.destroy(); pnlChart = null; }
    return;
  }

  emptyEl.classList.add('hidden');

  const labels   = rows.map(r => r.date);
  const realized = rows.map(r => parseFloat(r.realized_pnl ?? 0));
  const ending   = rows.map(r => parseFloat(r.ending_balance_usd ?? 0));

  // Cumulative realized P&L
  const cumulative = realized.reduce((acc, v) => acc + v, 0);
  totalEl.textContent = fmtUSD(cumulative);
  totalEl.className = `pnl-value ${cumulative >= 0 ? 'pos' : 'neg'}`;

  buildPnlChart(labels, realized, ending);
}

// ══════════════════════════════════════════════════════════════════════════
// Risk Monitor
// ══════════════════════════════════════════════════════════════════════════
async function refreshRisk() {
  const [summary, log] = await Promise.all([
    fetchJSON('/api/risk/summary'),
    fetchJSON('/api/risk'),
  ]);

  // Today's summary
  if (summary) {
    const drawdown = parseFloat(summary.drawdown_pct ?? 0);
    const maxDd    = parseFloat(summary.max_drawdown_pct ?? 0);
    el('drawdownPct').textContent    = fmtPct(drawdown);
    el('maxDrawdownPct').textContent = fmtPct(maxDd);
    el('tradesExec').textContent     = summary.trades_executed ?? '—';
    el('tradesRej').textContent      = summary.trades_rejected ?? '—';

    // Drawdown bar (0–10% scale)
    const fillPct  = Math.min((drawdown / 10) * 100, 100);
    const fillEl   = el('drawdownFill');
    fillEl.style.width = fillPct + '%';
    el('drawdownPctBar').textContent = fmtPct(drawdown);

    // Circuit breaker badge
    const cbBadge = el('cbBadge');
    const cbStatus = el('cbStatus');
    if (summary.circuit_breaker_hit) {
      cbBadge.className  = 'risk-badge tripped';
      cbStatus.textContent = '⚠ Circuit Breaker TRIPPED';
    } else {
      cbBadge.className  = 'risk-badge safe';
      cbStatus.textContent = '✓ Circuit Breaker Safe';
    }
  } else {
    // No data yet for today
    ['drawdownPct','maxDrawdownPct','tradesExec','tradesRej'].forEach(id => {
      el(id).textContent = '—';
    });
    el('cbBadge').className = 'risk-badge';
    el('cbStatus').textContent = 'No data today';
  }

  // Risk log entries
  const entriesEl = el('riskEntries');
  if (!log || log.length === 0) {
    entriesEl.innerHTML = '<span class="muted">No risk decisions logged yet</span>';
    return;
  }

  entriesEl.innerHTML = log.slice(0, 6).map(r => `
    <div class="risk-entry">
      <span class="risk-entry-time">${fmtTime(r.timestamp)}</span>
      <span class="risk-entry-text">
        <span class="${r.approved ? 'risk-approved' : 'risk-rejected'}">${r.approved ? '✓' : '✗'}</span>
        <strong>${r.agent}</strong> — ${r.action ?? ''}
        ${r.market ? `<em>${r.market}</em>` : ''}
        ${r.reason ? `<span class="muted">· ${r.reason}</span>` : ''}
      </span>
    </div>
  `).join('');
}

// ══════════════════════════════════════════════════════════════════════════
// Trades Table
// ══════════════════════════════════════════════════════════════════════════
async function refreshTrades() {
  const trades = await fetchJSON('/api/trades');
  const tbody  = el('tradesBody');

  if (!trades || trades.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8" class="table-empty">No trades recorded yet</td></tr>';
    el('tradesLastUpdated').textContent = 'Updated ' + new Date().toLocaleTimeString();
    return;
  }

  tbody.innerHTML = trades.map(t => `
    <tr>
      <td>${fmtTime(t.timestamp)}</td>
      <td>${t.agent ?? '—'}</td>
      <td><span class="badge badge-${t.action}">${t.action ?? '—'}</span></td>
      <td>${t.market ?? '—'}</td>
      <td>${t.amount != null ? parseFloat(t.amount).toLocaleString() : '—'}</td>
      <td><span class="badge badge-${t.chain}">${t.chain ?? '—'}</span></td>
      <td>${t.platform ?? '—'}</td>
      <td><span class="badge badge-${t.status}">${t.status ?? '—'}</span></td>
    </tr>
  `).join('');

  el('tradesLastUpdated').textContent = 'Updated ' + new Date().toLocaleTimeString();
}

// ══════════════════════════════════════════════════════════════════════════
// Sentiment Briefs
// ══════════════════════════════════════════════════════════════════════════
async function refreshSentiment() {
  const briefs  = await fetchJSON('/api/sentiment');
  const wrapper = el('briefsContainer');

  if (!briefs || briefs.length === 0) {
    wrapper.innerHTML = '<span class="muted">No sentiment briefs yet</span>';
    el('sentimentLastUpdated').textContent = 'Updated ' + new Date().toLocaleTimeString();
    return;
  }

  wrapper.innerHTML = briefs.map(b => `
    <div class="brief-card">
      <div class="brief-header">
        <span class="brief-time">${fmtTime(b.timestamp)}</span>
        <span class="brief-sentiment sentiment-${b.overall_sentiment ?? 'neutral'}">
          ${b.overall_sentiment ?? 'neutral'}
        </span>
        ${b.confidence != null
          ? `<span class="brief-confidence">confidence: ${parseFloat(b.confidence).toFixed(2)}</span>`
          : ''}
      </div>
      <div class="brief-body">${escHtml(b.brief_text ?? '')}</div>
    </div>
  `).join('');

  el('sentimentLastUpdated').textContent = 'Updated ' + new Date().toLocaleTimeString();
}

function escHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ══════════════════════════════════════════════════════════════════════════
// Advanced Details
// ══════════════════════════════════════════════════════════════════════════
async function refreshCron() {
  const crons = await fetchJSON('/api/cron');
  const tbody = el('cronBody');

  if (!crons || crons.length === 0) {
    tbody.innerHTML = '<tr><td colspan="4" class="table-empty">No cron logs recorded yet</td></tr>';
    el('cronLastUpdated').textContent = 'Updated ' + new Date().toLocaleTimeString();
    return;
  }

  tbody.innerHTML = crons.map(c => `
    <tr>
      <td>${fmtTime(c.timestamp)}</td>
      <td>${c.agent ?? '—'}</td>
      <td>${c.cron_name ?? '—'}</td>
      <td><span class="badge badge-${c.status === 'success' ? 'execute' : 'rejected'}">${c.status ?? '—'}</span></td>
    </tr>
  `).join('');

  el('cronLastUpdated').textContent = 'Updated ' + new Date().toLocaleTimeString();
}

async function refreshLlm() {
  const usage = await fetchJSON('/api/llm-usage');
  const statsEl = el('llmStats');

  if (!usage || usage.error) {
    statsEl.innerHTML = `<div class="table-empty">${usage?.error || 'Could not load LLM stats'}</div>`;
    el('llmLastUpdated').textContent = 'Updated ' + new Date().toLocaleTimeString();
    return;
  }

  if (usage.data) {
    const d = usage.data;
    statsEl.innerHTML = `
      <div class="risk-stat">
        <div class="risk-stat-label">Credits Remaining</div>
        <div class="risk-stat-value success">${d.limit != null && d.usage != null ? fmtUSD(d.limit - d.usage) : '—'}</div>
      </div>
      <div class="risk-stat">
        <div class="risk-stat-label">Spend (USD)</div>
        <div class="risk-stat-value">${d.usage != null ? fmtUSD(d.usage) : '—'}</div>
      </div>
      <div class="risk-stat">
        <div class="risk-stat-label">Limit (USD)</div>
        <div class="risk-stat-value">${d.limit != null ? fmtUSD(d.limit) : '—'}</div>
      </div>
    `;
  }
  el('llmLastUpdated').textContent = 'Updated ' + new Date().toLocaleTimeString();
}

async function refreshMinimax() {
  const usage = await fetchJSON('/api/minimax-usage');
  const statsEl = el('minimaxStats');

  if (!usage || usage.error) {
    statsEl.innerHTML = `<div class="table-empty">${usage?.error || 'Could not load Minimax stats'}</div>`;
    return;
  }

  // The "Coding Plan" API typically returns remaining quota
  if (usage.data && usage.data.remains !== undefined) {
    const remains = usage.data.remains;
    statsEl.innerHTML = `
      <div class="risk-stat">
        <div class="risk-stat-label">Remaining Tokens</div>
        <div class="risk-stat-value success">${remains.toLocaleString()}</div>
      </div>
      <div class="risk-stat">
        <div class="risk-stat-label">Status</div>
        <div class="risk-stat-value">${usage.base_resp?.status_msg || 'Active'}</div>
      </div>
    `;
  } else {
    statsEl.innerHTML = `<div class="table-empty">No quota data available</div>`;
  }
}


// ══════════════════════════════════════════════════════════════════════════
// Bootstrap
// ══════════════════════════════════════════════════════════════════════════
function start() {
  startClock();

  // Initial fetches
  refreshStatus();
  refreshTrades();
  refreshRisk();
  refreshPnl();
  refreshSentiment();
  refreshCron();
  refreshLlm();
  refreshMinimax();

  // Polling intervals
  setInterval(refreshStatus,    POLL_STATUS);
  setInterval(refreshTrades,    POLL_TRADES);
  setInterval(refreshRisk,      POLL_RISK);
  setInterval(refreshPnl,       POLL_PNL);
  setInterval(refreshSentiment, POLL_SENTIMENT);
  setInterval(refreshCron,      POLL_CRON);
  setInterval(refreshLlm,       POLL_LLM);
  setInterval(refreshMinimax,   POLL_LLM);
}

// Wait for DOM
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', start);
} else {
  start();
}
