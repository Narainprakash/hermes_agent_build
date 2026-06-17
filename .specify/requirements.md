# Benki Multi-Agent System — Requirements

## 1. Purpose

Build a Dockerized Hermes multi-agent system for stock/ETF market research, Kalshi prediction-market analysis, trade execution preparation, risk auditing, and dashboard monitoring.

The system must prioritize safety, auditability, dry-run validation, and human oversight before any live financial execution.

---

## 2. Agents

### R1 — Benki Main / Orchestrator

- Acts as commander and market research agent.
- Generates Market Context Briefs using stock/ETF data, news, macro context, sentiment, Kalshi odds, and risk state.
- Never executes trades or bets directly.
- Never dispatches crypto spot/token trades.
- Dispatches structured JSON directives only:
  - `TRADE_NOW` to Trader for stocks/ETFs only
  - `BET_NOW` to Predictor for Kalshi only

### R2 — Benki Trader

- Receives only valid JSON `TRADE_NOW` directives.
- Executes stock/ETF trades through Robinhood MCP only.
- Must reject crypto assets, tokens, coins, and on-chain trades.
- Runs in `DRY_RUN=true` by default.
- Calls `risk-manager` before any trade.
- Logs all trade decisions and results to PostgreSQL.

### R3 — Benki Predictor

- Receives only valid JSON `BET_NOW` directives.
- Scans Kalshi markets only when prediction features are enabled.
- Bets only when calculated edge is greater than 5%.
- Calls `risk-manager` before any bet.
- Tracks prediction quality using Brier score.

---

## 3. Risk Management

### R4 — Risk Controls

- All trades and bets must pass the `risk-manager` plugin.
- Position sizing must use portfolio value and Kelly-style sizing.
- Maximum position size must be capped.
- Daily drawdown limits must trigger a circuit breaker.
- Rejected trades or bets must not be retried in the same session.

### R5 — Safety Defaults

- `DRY_RUN=true` must be default for all execution agents.
- `FEATURE_TRADING=false` must be default until Robinhood MCP is validated.
- `FEATURE_PREDICTIONS=false` must be default until Kalshi credentials are validated.
- Live credentials must never be committed.

---

## 4. Human Oversight

### R6 — Human-in-the-Loop

- Low-confidence decisions must be escalated to designated Discord users.
- High-risk trade or bet decisions must request human approval.
- Agents must report execution results back to the Orchestrator.
- Discord is the primary control and notification plane.

---

## 5. Data Storage

### R7 — PostgreSQL Audit Database

The system must persist:

- Trades and bet executions
- Daily P&L
- Risk audit logs
- Sentiment briefs
- Cron job logs
- Prediction outcomes and Brier scores

### R8 — Auditability

- Risk decisions must be immutable and append-only.
- Executed, skipped, rejected, and dry-run actions must be logged.
- Dashboard data must come from PostgreSQL and agent health endpoints.

---

## 6. Dashboard

### R9 — Web UI

- Exposes a dashboard on port `3000`.
- Shows agent health status.
- Shows recent trades and bets.
- Shows P&L history.
- Shows risk status and circuit breaker state.
- Shows recent sentiment briefs.

### R10 — Dashboard Security

- Dashboard API access must support bearer-token authentication.
- Public deployments should use HTTPS and reverse-proxy protection.
- Agent health APIs must require a shared API key when exposed inside Docker.

---

## 7. Automation

### R11 — Cron Workflows

- Main agent must run scheduled market research.
- Trader must run scheduled position management and reflection.
- Predictor must run scheduled prediction scans and bet management.
- Cron results must be logged.

---

## 8. Deployment

### R12 — Containerized Runtime

The system must run using Docker Compose with:

- PostgreSQL
- Benki Main
- Benki Predictor
- Benki Trader
- Benki UI

### R13 — Service Defaults

- Trader service must remain disabled by default until validated.
- Agent API servers must bind to `0.0.0.0` inside Docker.
- Persistent volumes must store database and agent memory.

---

## 9. Configuration & Secrets

### R14 — Environment Configuration

- Each agent must use its own `.env` file.
- Database URLs must use the same generated database password.
- Discord, OpenRouter, Kalshi, and Robinhood-related values must be configured through environment variables.

### R15 — Secret Handling

- Real `.env` files, private keys, tokens, and credentials must be ignored by Git.
- Kalshi private keys must be mounted as read-only secrets.
- Robinhood authentication must remain outside the repository.
