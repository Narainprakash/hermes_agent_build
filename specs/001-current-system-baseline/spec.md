# Feature Specification: Benki Current System Baseline

**Feature Branch**: `001-current-system-baseline`  
**Created**: 2026-06-09  
**Status**: Draft  
**Input**: Capture the current Benki system as the baseline for future Spec Kit work.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Monitor agents and risk (Priority: P1)

Operators can open the dashboard and quickly see enabled agent health, current P&L/risk state, recent decisions, cron activity, and prediction/trade records.

**Independent Test**: Run the dashboard with seeded/empty database states and reachable/unreachable agents; verify all panels render and degrade safely.

**Acceptance Scenarios**:
1. **Given** agents are reachable, **When** status polling runs, **Then** cards show online/degraded/offline state, latency, HTTP status, and last check time.
2. **Given** database tables have rows or are empty, **When** dashboard APIs are called, **Then** they return JSON without crashing.

---

### User Story 2 - Coordinate market decisions (Priority: P1)

The Orchestrator creates Market Context Briefs and sends only structured JSON directives to workers; it never executes trades or bets itself.

**Independent Test**: Trigger market research in dry-run mode and inspect Discord output plus sentiment/cron logs.

**Acceptance Scenarios**:
1. **Given** market research runs, **When** signals pass thresholds, **Then** the Orchestrator logs an MCB and emits valid `TRADE_NOW`/`BET_NOW` JSON.
2. **Given** a feature is disabled or confidence is low, **When** a candidate action appears, **Then** dispatch is skipped or escalated to humans.

---

### User Story 3 - Enforce execution safety (Priority: P1)

Every worker trade or bet must pass deterministic risk checks before execution or dry-run logging.

**Independent Test**: Submit representative valid, oversized, drawdown-limit, leverage, and DB-unavailable risk checks.

**Acceptance Scenarios**:
1. **Given** drawdown or circuit-breaker limits are hit, **When** a worker requests approval, **Then** risk control rejects and logs it.
2. **Given** risk state cannot be read, **When** approval is requested, **Then** the system fails closed.
3. **Given** risk approval succeeds, **When** the worker acts, **Then** the result is logged.

---

### User Story 4 - Run prediction-market flow (Priority: P2)

The Predictor processes valid `BET_NOW` directives and independent scans only when prediction markets are enabled, edge is sufficient, and risk approves.

**Independent Test**: In dry-run mode, test disabled, below-edge, approved, and rejected prediction paths.

**Acceptance Scenarios**:
1. **Given** predictions are disabled, **When** scan/directive handling runs, **Then** betting is skipped and logged.
2. **Given** edge exceeds threshold and risk approves, **When** a bet is processed, **Then** a strict JSON `BET_RESULT` is reported.

### Edge Cases

- Agent, database, RPC, market, news, or LLM usage APIs are unavailable or rate-limited.
- Directives are malformed, duplicated, stale, below-threshold, or target unsupported chains/platforms.
- Feature toggles and running services disagree.
- Daily P&L is missing, stale, or zero-valued.
- Dry-run/live settings conflict with available credentials.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST include PostgreSQL, Orchestrator, enabled workers, cron workflows, plugins, and dashboard services.
- **FR-002**: Dashboard MUST expose JSON APIs for status, trades, P&L, risk, sentiment, cron, commands, predictions, growth, and feature flags.
- **FR-003**: Dashboard APIs MUST degrade safely on missing data or failed dependencies.
- **FR-004**: Orchestrator MUST generate MCBs and MUST NOT execute trades or bets.
- **FR-005**: Worker directives/results MUST use strict JSON contracts.
- **FR-006**: Workers MUST reject non-JSON execution commands.
- **FR-007**: Workers MUST call risk control before every trade or bet.
- **FR-008**: Risk control MUST enforce circuit breaker, sizing, leverage, and fail-closed behavior.
- **FR-009**: Risk decisions, trades/bets, sentiment briefs, cron runs, predictions, and command loops MUST be persistently auditable when storage is available.
- **FR-010**: Trades and bets MUST default to dry-run unless live mode and credentials are explicitly configured.
- **FR-011**: Feature toggles MUST disable trading/prediction behavior across prompts, cron, dispatch, and dashboard state.
- **FR-012**: Low-confidence, high-risk, uncertain, or leverage-related decisions MUST escalate to human operators.

### Key Entities *(include if feature involves data)*

- **Agent**: Orchestrator, Trader, or Predictor service with health, config, prompts, plugins, and channels.
- **Market Context Brief**: Timestamped market analysis with sentiment, confidence, signals, risk advisory, and dispatch targets.
- **Directive / Result**: JSON commander-worker command and JSON worker response.
- **Trade / Prediction**: Execution or dry-run record with market, amount, status, risk result, and outcome/calibration data.
- **Daily P&L / Risk Audit**: Portfolio state and immutable approval/rejection history.
- **Cron Log / Agent Command / Growth Target**: Operational history and planning telemetry.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Operator can identify agent health and risk state within 30 seconds from the dashboard.
- **SC-002**: 100% of trade/bet attempts pass risk control before execution or dry-run logging.
- **SC-003**: 100% of reachable-storage risk decisions are audit logged.
- **SC-004**: No executable directive is emitted outside the required JSON contract.
- **SC-005**: Disabled prediction/trading features are skipped in all relevant paths.
- **SC-006**: Dashboard APIs return JSON for empty data, unavailable agents, and failed DB queries.

## Assumptions

- This is a baseline documentation spec, not a live-trading enablement request.
- Dry-run is the safe default.
- Secrets live in environment-specific config, not committed source.
- PostgreSQL is the audit/source-of-truth layer.
- Current risk plugin behavior is the baseline where docs and implementation differ.
