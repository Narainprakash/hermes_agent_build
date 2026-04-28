-------------------------------------------------------------------------------
-- Benki Multi-Agent System — PostgreSQL Schema
-- Tables for trade logging, P&L tracking, sentiment briefs, and risk auditing
-------------------------------------------------------------------------------

-- Trade execution log
CREATE TABLE trades (
    id              SERIAL PRIMARY KEY,
    agent           TEXT NOT NULL,                   -- 'trader' or 'predictor'
    timestamp       TIMESTAMPTZ DEFAULT NOW(),
    chain           TEXT NOT NULL,                   -- 'solana', 'polygon'
    platform        TEXT,                            -- 'jupiter', 'polymarket', 'drift_bet', 'uniswap'
    action          TEXT NOT NULL,                   -- 'buy', 'sell', 'bet_yes', 'bet_no'
    market          TEXT,                            -- market name / token pair
    amount          NUMERIC,
    price           NUMERIC,
    tx_hash         TEXT,
    status          TEXT DEFAULT 'pending',          -- 'pending', 'executed', 'failed', 'dry_run'
    risk_check_passed BOOLEAN,
    notes           TEXT
);

-- Daily portfolio performance tracking
CREATE TABLE daily_pnl (
    id                  SERIAL PRIMARY KEY,
    date                DATE NOT NULL UNIQUE,
    starting_balance_usd NUMERIC,
    ending_balance_usd  NUMERIC,
    realized_pnl        NUMERIC,
    unrealized_pnl      NUMERIC,
    drawdown_pct        NUMERIC,
    max_drawdown_pct    NUMERIC,
    circuit_breaker_hit BOOLEAN DEFAULT FALSE,
    trades_executed     INTEGER DEFAULT 0,
    trades_rejected     INTEGER DEFAULT 0
);

-- Sentiment analysis briefs from orchestrator
CREATE TABLE sentiment_briefs (
    id              SERIAL PRIMARY KEY,
    timestamp       TIMESTAMPTZ DEFAULT NOW(),
    brief_text      TEXT,
    tokens_analyzed TEXT[],
    overall_sentiment TEXT,                          -- 'bullish', 'bearish', 'neutral'
    confidence      NUMERIC,
    dispatched_to   TEXT[]                           -- ['trader', 'predictor']
);

-- Risk manager audit log (append-only, immutable)
CREATE TABLE risk_audit_log (
    id                      SERIAL PRIMARY KEY,
    timestamp               TIMESTAMPTZ DEFAULT NOW(),
    agent                   TEXT NOT NULL,
    action                  TEXT NOT NULL,
    chain                   TEXT,
    market                  TEXT,
    requested_amount        NUMERIC,
    approved                BOOLEAN NOT NULL,
    reason                  TEXT,
    current_drawdown_pct    NUMERIC,
    position_size_calculated NUMERIC,
    daily_pnl_at_check      NUMERIC
);

-- Cron execution log
CREATE TABLE cron_logs (
    id              SERIAL PRIMARY KEY,
    agent           TEXT NOT NULL,
    cron_name       TEXT NOT NULL,
    timestamp       TIMESTAMPTZ DEFAULT NOW(),
    status          TEXT DEFAULT 'success',
    details         TEXT
);

-- Index for common queries
CREATE INDEX idx_trades_agent ON trades(agent);
CREATE INDEX idx_trades_status ON trades(status);
CREATE INDEX idx_trades_timestamp ON trades(timestamp);
CREATE INDEX idx_risk_audit_timestamp ON risk_audit_log(timestamp);
CREATE INDEX idx_risk_audit_agent ON risk_audit_log(agent);
CREATE INDEX idx_sentiment_timestamp ON sentiment_briefs(timestamp);
CREATE INDEX idx_cron_logs_timestamp ON cron_logs(timestamp);

-- Prediction market tracking (for Brier score and calibration)
CREATE TABLE IF NOT EXISTS predictions (
    id                  SERIAL PRIMARY KEY,
    agent               TEXT NOT NULL DEFAULT 'predictor',
    timestamp           TIMESTAMPTZ DEFAULT NOW(),
    platform            TEXT NOT NULL,                   -- 'polymarket' or 'drift_bet'
    market_id           TEXT,
    market_question     TEXT NOT NULL,
    position            TEXT NOT NULL,                   -- 'yes' or 'no'
    my_probability      NUMERIC NOT NULL,
    market_probability  NUMERIC NOT NULL,
    edge                NUMERIC NOT NULL,
    amount              NUMERIC,
    entry_price         NUMERIC,
    resolution_date     DATE,
    outcome             BOOLEAN,                         -- NULL = unresolved, true = win, false = loss
    brier_score         NUMERIC,                         -- computed on resolution: (prob - outcome)^2
    status              TEXT DEFAULT 'open',              -- 'open', 'closed_early', 'resolved_win', 'resolved_loss'
    notes               TEXT
);

CREATE INDEX idx_predictions_status ON predictions(status);
CREATE INDEX idx_predictions_platform ON predictions(platform);
CREATE INDEX idx_predictions_timestamp ON predictions(timestamp);
