'use strict';

const express = require('express');
const { Pool }  = require('pg');
const path      = require('path');

// ─── Config ────────────────────────────────────────────────────────────────
const PORT          = parseInt(process.env.PORT || '3000', 10);
const GATEWAY_PORT  = process.env.GATEWAY_PORT  || '8642';
const HEALTH_PATH   = process.env.HEALTH_PATH   || '/health';
const API_KEY       = process.env.API_SERVER_KEY || '';

const AGENTS = [
  { id: 'main',      name: 'Orchestrator', host: process.env.MAIN_HOST      || 'benki-main'      },
  { id: 'trader',    name: 'Trader',       host: process.env.TRADER_HOST    || 'benki-trader'    },
  { id: 'predictor', name: 'Predictor',    host: process.env.PREDICTOR_HOST || 'benki-predictor' },
];

// ─── Database ───────────────────────────────────────────────────────────────
const pool = new Pool({ connectionString: process.env.DATABASE_URL });

pool.on('error', (err) => {
  console.error('[db] idle client error:', err.message);
});

// ─── Helpers ────────────────────────────────────────────────────────────────
/**
 * Hit a single agent's health endpoint. Returns a status object.
 */
async function checkAgent(agent) {
  const url   = `http://${agent.host}:${GATEWAY_PORT}${HEALTH_PATH}`;
  const start = Date.now();
  try {
    const res     = await fetch(url, {
      headers: API_KEY ? { Authorization: `Bearer ${API_KEY}` } : {},
      signal:  AbortSignal.timeout(5000),
    });
    const latency = Date.now() - start;
    let body = {};
    try { body = await res.json(); } catch (_) { /* non-JSON body is fine */ }
    return {
      ...agent,
      status:      res.ok ? 'online' : 'degraded',
      httpStatus:  res.status,
      latencyMs:   latency,
      detail:      body,
      lastChecked: new Date().toISOString(),
    };
  } catch (err) {
    return {
      ...agent,
      status:      'offline',
      latencyMs:   null,
      error:       err.message,
      lastChecked: new Date().toISOString(),
    };
  }
}

/**
 * Safe SQL query — returns empty array on error instead of blowing up.
 */
async function safeQuery(sql, params = []) {
  try {
    const { rows } = await pool.query(sql, params);
    return rows;
  } catch (err) {
    console.warn('[db] query failed:', err.message);
    return [];
  }
}

// ─── Express App ─────────────────────────────────────────────────────────────
const app = express();

// Ping / liveness probe (used by Docker HEALTHCHECK)
app.get('/api/ping', (_req, res) => res.json({ ok: true }));

// Aggregate health of all 3 agent gateways
app.get('/api/status', async (_req, res) => {
  const results = await Promise.all(AGENTS.map(checkAgent));
  res.json(results);
});

// Recent trades (last 50)
app.get('/api/trades', async (_req, res) => {
  const rows = await safeQuery(
    `SELECT id, agent, timestamp, chain, platform, action, market,
            amount, price, tx_hash, status, risk_check_passed, notes
     FROM   trades
     ORDER  BY timestamp DESC
     LIMIT  50`
  );
  res.json(rows);
});

// Cumulative P&L time-series (last 30 days)
app.get('/api/pnl', async (_req, res) => {
  const rows = await safeQuery(
    `SELECT date,
            starting_balance_usd,
            ending_balance_usd,
            realized_pnl,
            drawdown_pct,
            circuit_breaker_hit,
            trades_executed,
            trades_rejected
     FROM   daily_pnl
     ORDER  BY date ASC
     LIMIT  30`
  );
  res.json(rows);
});

// Latest sentiment brief from orchestrator
app.get('/api/sentiment', async (_req, res) => {
  const rows = await safeQuery(
    `SELECT id, timestamp, brief_text, overall_sentiment, confidence, tokens_analyzed
     FROM   sentiment_briefs
     ORDER  BY timestamp DESC
     LIMIT  5`
  );
  res.json(rows);
});

// Recent risk audit entries
app.get('/api/risk', async (_req, res) => {
  const rows = await safeQuery(
    `SELECT id, timestamp, agent, action, chain, market,
            requested_amount, approved, reason, current_drawdown_pct
     FROM   risk_audit_log
     ORDER  BY timestamp DESC
     LIMIT  20`
  );
  res.json(rows);
});

// Today's drawdown summary
app.get('/api/risk/summary', async (_req, res) => {
  const rows = await safeQuery(
    `SELECT date, drawdown_pct, max_drawdown_pct, circuit_breaker_hit,
            trades_executed, trades_rejected
     FROM   daily_pnl
     WHERE  date = CURRENT_DATE
     LIMIT  1`
  );
  res.json(rows[0] || null);
});

// Serve the dashboard SPA
app.use(express.static(path.join(__dirname, 'public')));
app.get('*', (_req, res) =>
  res.sendFile(path.join(__dirname, 'public', 'index.html'))
);

// ─── Start ───────────────────────────────────────────────────────────────────
app.listen(PORT, () => {
  console.log(`[benki-ui] Dashboard running → http://localhost:${PORT}`);
  console.log(`[benki-ui] Polling agents on port ${GATEWAY_PORT} at ${HEALTH_PATH}`);
});
