'use strict';

const express = require('express');
const { Pool } = require('pg');
const path = require('path');

// ─── Config ────────────────────────────────────────────────────────────────
const PORT = parseInt(process.env.PORT || '3000', 10);
const GATEWAY_PORT = process.env.GATEWAY_PORT || '8642';
const HEALTH_PATH = process.env.HEALTH_PATH || '/health';
const API_KEY = process.env.API_SERVER_KEY || '';

// Feature toggles — control which markets are active
const FEATURES = {
  trading: process.env.FEATURE_TRADING !== 'false',      // default ON
  predictions: process.env.FEATURE_PREDICTIONS === 'true', // default OFF
};

const AGENTS = [
  { id: 'main', name: 'Orchestrator', host: process.env.MAIN_HOST || 'benki-main' },
  { id: 'trader', name: 'Trader', host: process.env.TRADER_HOST || 'benki-trader' },
  { id: 'predictor', name: 'Predictor', host: process.env.PREDICTOR_HOST || 'benki-predictor' },
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
  const url = `http://${agent.host}:${GATEWAY_PORT}${HEALTH_PATH}`;
  const start = Date.now();
  try {
    const res = await fetch(url, {
      headers: API_KEY ? { Authorization: `Bearer ${API_KEY}` } : {},
      signal: AbortSignal.timeout(5000),
    });
    const latency = Date.now() - start;
    let body = {};
    try { body = await res.json(); } catch (_) { /* non-JSON body is fine */ }
    return {
      ...agent,
      status: res.ok ? 'online' : 'degraded',
      httpStatus: res.status,
      latencyMs: latency,
      detail: body,
      lastChecked: new Date().toISOString(),
    };
  } catch (err) {
    return {
      ...agent,
      status: 'offline',
      latencyMs: null,
      error: err.message,
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

// Feature toggles — tells the UI which modules are active
app.get('/api/features', (_req, res) => {
  res.json({
    trading: FEATURES.trading,
    predictions: FEATURES.predictions,
    updatedAt: new Date().toISOString(),
  });
});

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

// Cron logs
app.get('/api/cron', async (_req, res) => {
  const rows = await safeQuery(
    `SELECT id, agent, cron_name, status, timestamp, details
     FROM   cron_logs
     ORDER  BY timestamp DESC
     LIMIT  20`
  );
  res.json(rows);
});

// Agent Commands
app.get('/api/commands', async (_req, res) => {
  const rows = await safeQuery(
    `SELECT id, timestamp, commander, worker, directive_type, directive_json, response_json, response_status, response_at, feedback_loop_closed
     FROM   agent_commands
     ORDER  BY timestamp DESC
     LIMIT  50`
  );
  res.json(rows);
});

// Growth Targets
app.get('/api/growth', async (_req, res) => {
  const rows = await safeQuery(
    `SELECT id, period_start, period_end, starting_capital, target_capital, current_capital, target_daily_pct, on_track
     FROM   growth_targets
     ORDER  BY id DESC
     LIMIT  1`
  );
  res.json(rows[0] || null);
});

// Predictions (open prediction market bets)
app.get('/api/predictions', async (_req, res) => {
  const rows = await safeQuery(
    `SELECT id, timestamp, platform, market_question, position,
            my_probability, market_probability, edge, amount,
            entry_price, resolution_date, status, brier_score, notes
     FROM   predictions
     WHERE  status = 'open'
     ORDER  BY timestamp DESC
     LIMIT  50`
  );
  res.json(rows);
});

// LLM Token Usage (OpenRouter API)
app.get('/api/llm-usage', async (_req, res) => {
  const openRouterKey = process.env.OPENROUTER_API_KEY;
  if (!openRouterKey) {
    return res.json({ error: 'OPENROUTER_API_KEY not configured' });
  }
  try {
    const apiRes = await fetch('https://openrouter.ai/api/v1/auth/key', {
      headers: { Authorization: `Bearer ${openRouterKey}` }
    });
    if (!apiRes.ok) throw new Error('OpenRouter API error');
    const data = await apiRes.json();
    res.json({ data: data.data });
  } catch (err) {
    res.json({ error: err.message });
  }
});

// Minimax Token Usage (Remains API)
app.get('/api/minimax-usage', async (_req, res) => {
  const minimaxKey = process.env.MINIMAX_API_KEY;
  if (!minimaxKey) {
    return res.json({ error: 'MINIMAX_API_KEY not configured' });
  }
  try {
    const apiRes = await fetch('https://api.minimax.io/v1/api/openplatform/coding_plan/remains', {
      headers: {
        'Authorization': `Bearer ${minimaxKey}`,
        'Content-Type': 'application/json'
      }
    });
    if (!apiRes.ok) throw new Error('Minimax API error');
    const data = await apiRes.json();
    // Assuming the API returns { "remains": number, ... } or similar based on research
    res.json(data);
  } catch (err) {
    res.json({ error: err.message });
  }
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

  // Automated first run of crons
  setTimeout(async () => {
    console.log('[benki-ui] Sending startup triggers to agents...');

    const triggers = [
      {
        host: process.env.MAIN_HOST || 'benki-main',
        prompt: `Run the market-research skill now. Steps:\n1. get_crypto_prices for bitcoin, ethereum, solana\n2. get_fear_greed_index\n3. search_news for 'Bitcoin Ethereum Solana market sentiment today'\n4. Compile and dispatch a Market Context Brief to #trading (channel ${process.env.TRADING_CHANNEL_ID || '1494494694057709789'}) and #predictions (channel ${process.env.PREDICTIONS_CHANNEL_ID || '1494494936182165705'})\n5. benki_db_log_cron agent='main' cron_name='market-research' status='success'`
      },
      {
        host: process.env.TRADER_HOST || 'benki-trader',
        prompt: "Run the manage-positions skill now. Check open positions, evaluate exit criteria, execute sells where criteria are met, log results."
      },
      {
        host: process.env.PREDICTOR_HOST || 'benki-predictor',
        prompt: "Run the manage-bets skill now. Check open prediction market bets, re-evaluate edge on each, cash out early where edge has gone negative, log results."
      }
    ];

    for (const t of triggers) {
      try {
        const url = `http://${t.host}:${GATEWAY_PORT}/v1/chat/completions`;
        const res = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(API_KEY ? { 'Authorization': `Bearer ${API_KEY}` } : {})
          },
          body: JSON.stringify({
            model: "hermes",
            messages: [{ role: "user", content: t.prompt }]
          }),
          signal: AbortSignal.timeout(15000)  // don't block server startup forever
        });
        console.log(`[benki-ui] Startup trigger → ${t.host}: HTTP ${res.status}`);
      } catch (err) {
        console.warn(`[benki-ui] Startup trigger failed for ${t.host}: ${err.message}`);
      }
    }
  }, 45_000); // 45s — agents need longer than 30s to fully boot + connect to Discord
});
