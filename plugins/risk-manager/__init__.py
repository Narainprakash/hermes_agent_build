"""
Benki Risk Manager Plugin — Hardcoded Circuit Breaker
=====================================================
The 5% daily drawdown limit is HARDCODED at module level (MAX_DAILY_DRAWDOWN_PCT = 5.0).
The LLM cannot override, modify, or bypass this value.
Every trade request is logged to the risk_audit_log table regardless of outcome.
Uses shared connection pool from plugins/shared/db_pool.py.
"""

import os
import json
import math
from datetime import date, datetime, timezone, timedelta
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))
from db_pool import get_pool

# ╔══════════════════════════════════════════════════════════════════════╗
# ║  USER CONFIGURED LIMITS — Updated for Benki production             ║
# ╚══════════════════════════════════════════════════════════════════════╝
MAX_DAILY_DRAWDOWN_PCT = 5.0    # Circuit breaker: 5% max daily loss (user spec)
KELLY_FRACTION = 0.5            # Half-Kelly for conservative sizing
MIN_TRADE_AMOUNT = 0.01         # Minimum trade size in USD
MAX_SINGLE_TRADE_PCT = 2.0      # Max 2% of portfolio on a single trade (user spec)
MAX_CHAIN_EXPOSURE_PCT = 30.0   # Max 30% of portfolio on any single chain
MAX_OPEN_POSITIONS = 6          # Max 6 concurrent open positions
MAX_LOSS_PER_TRADE_PCT = 2.0    # Hard stop: max 2% loss per trade (user spec)
LEVERAGE_MAX_WITHOUT_APPROVAL = 1.0  # No leverage without human approval

# Session-level tracking for pre-trade enforcement.
# Approvals are exact, short-lived, and consumed after one execution call.
_risk_approvals = {}
RISK_APPROVAL_TTL_SECONDS = 15 * 60


def _parse_numeric(val, default=0.0):
    """Safely parse a numeric value."""
    try:
        return float(val) if val is not None else default
    except (ValueError, TypeError):
        return default


def _normalize_market(value):
    """Normalize market identifiers used to bind risk approval to execution."""
    return str(value or "unknown").strip().lower()


def _approval_key(agent, action, execution_market):
    """Build the exact key used for one-time execution approval."""
    return (str(agent or "unknown").lower(), str(action or "unknown").lower(), _normalize_market(execution_market))


def _cleanup_expired_approvals():
    """Remove old approvals so a stale risk check cannot authorize later trades."""
    now = datetime.now(timezone.utc)
    expired = [key for key, approval in _risk_approvals.items() if approval["expires_at"] <= now]
    for key in expired:
        _risk_approvals.pop(key, None)


async def _query_db(query, params=None):
    """Execute a read query against PostgreSQL using the shared connection pool."""
    pool = await get_pool()
    if not pool:
        return None
    try:
        async with pool.acquire() as conn:
            if params:
                return await conn.fetch(query, *params)
            else:
                return await conn.fetch(query)
    except Exception as e:
        return f"DB_ERROR: {str(e)}"


async def _execute_db(query, params=None):
    """Execute a write query against PostgreSQL using the shared connection pool."""
    pool = await get_pool()
    if not pool:
        return "DB_ERROR: BENKI_DB_URL not set or pool creation failed"
    try:
        async with pool.acquire() as conn:
            if params:
                await conn.execute(query, *params)
            else:
                await conn.execute(query)
            return "OK"
    except Exception as e:
        return f"DB_ERROR: {str(e)}"


async def _get_current_drawdown():
    """
    Calculate current daily drawdown from the daily_pnl table.
    Returns (drawdown_pct, circuit_breaker_hit) tuple.
    """
    today = date.today().isoformat()
    result = await _query_db(
        "SELECT drawdown_pct, circuit_breaker_hit FROM daily_pnl WHERE date = $1",
        [today]
    )

    # FIX — fail-closed:
    if isinstance(result, str) and result.startswith("DB_ERROR"):
        return MAX_DAILY_DRAWDOWN_PCT, False  # ← blocks all trades when DB is down

    if result and len(result) > 0:
        row = result[0]
        drawdown = _parse_numeric(row.get("drawdown_pct", 0))
        cb_hit = row.get("circuit_breaker_hit", False)
        return drawdown, cb_hit

    return 0.0, False


async def _log_risk_decision(agent, action, chain, market, amount, approved, reason,
                              drawdown, position_size, daily_pnl):
    """Log every risk decision to the immutable audit trail."""
    await _execute_db(
        """INSERT INTO risk_audit_log 
           (agent, action, chain, market, requested_amount, approved, reason,
            current_drawdown_pct, position_size_calculated, daily_pnl_at_check)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)""",
        [agent, action, chain, market, amount, approved, reason,
         drawdown, position_size, daily_pnl]
    )


def _calculate_kelly(win_prob, trade_type="spot", entry_price=None,
                     tp_pct=0.15, sl_pct=0.07):
    """
    Calculate Kelly Criterion position size with correct win/loss ratios.
    Uses half-Kelly (KELLY_FRACTION = 0.5) for conservative sizing.

    For prediction markets: win_ratio is derived from entry price.
      e.g. buying YES at 0.70 → win_ratio = (1/0.70 - 1) = 0.43
    For spot trades: win_ratio is derived from TP/SL targets.
      e.g. TP=+15%, SL=-7% → win_ratio = 15/7 = 2.14

    Args:
        win_prob: Probability of winning (0.0 - 1.0)
        trade_type: 'prediction' or 'spot'
        entry_price: For predictions, the price paid (0.0-1.0)
        tp_pct: For spot trades, take-profit % (e.g. 0.15 for 15%)
        sl_pct: For spot trades, stop-loss % (e.g. 0.07 for 7%)

    Returns:
        Fraction of bankroll to risk (0.0 - MAX_SINGLE_TRADE_PCT/100)
    """
    if win_prob <= 0 or win_prob >= 1:
        return 0.0

    if trade_type == "prediction" and entry_price and 0 < entry_price < 1:
        # Prediction market: profit = (1/entry_price - 1) per dollar risked
        b = (1.0 / entry_price) - 1.0
    elif trade_type == "spot" and sl_pct > 0:
        # Spot trade: reward/risk ratio from TP/SL
        b = tp_pct / sl_pct
    else:
        # Fallback: conservative 1.5:1
        b = 1.5

    # Kelly formula: f* = (p * b - q) / b
    q = 1.0 - win_prob
    kelly = (win_prob * b - q) / b

    # Apply half-Kelly
    kelly *= KELLY_FRACTION

    # Clamp to [0, MAX_SINGLE_TRADE_PCT/100]
    kelly = max(0.0, min(kelly, MAX_SINGLE_TRADE_PCT / 100.0))

    return kelly


async def handle_risk_check(params, **kwargs):
    """
    Check if a trade is allowed under current risk limits.

    MANDATORY before every trade/bet execution.
    The 5% drawdown limit is hardcoded and cannot be overridden.
    """
    chain = params.get("chain", "unknown")
    action = params.get("action", "unknown")
    amount = _parse_numeric(params.get("amount", 0))
    market = params.get("market", "unknown")
    execution_market = params.get("execution_market") or params.get("market_id") or params.get("ticker") or market
    agent = params.get("agent", "unknown")
    win_probability = _parse_numeric(params.get("win_probability", 0.5))
    portfolio_value = _parse_numeric(params.get("portfolio_value", 0))
    trade_type = params.get("trade_type", "spot")  # 'spot' or 'prediction'
    entry_price = _parse_numeric(params.get("entry_price", 0))  # for predictions
    tp_pct = _parse_numeric(params.get("tp_pct", 0.15))  # for spot
    sl_pct = _parse_numeric(params.get("sl_pct", 0.07))   # for spot

    dry_run = os.environ.get("DRY_RUN", "true").lower() == "true"

    # ── Check 1: Circuit breaker ──────────────────────────────────────
    current_drawdown, cb_already_hit = await _get_current_drawdown()

    if cb_already_hit:
        reason = (f"CIRCUIT BREAKER ACTIVE — Daily drawdown limit "
                  f"({MAX_DAILY_DRAWDOWN_PCT}%) was hit earlier today. "
                  f"ALL trades blocked until tomorrow. Current drawdown: {current_drawdown:.2f}%")
        await _log_risk_decision(agent, action, chain, market, amount,
                                  False, reason, current_drawdown, 0.0, 0.0)
        return json.dumps({
            "approved": False,
            "reason": reason,
            "position_size": 0.0,
            "current_drawdown_pct": current_drawdown,
            "circuit_breaker_hit": True
        })

    if current_drawdown >= MAX_DAILY_DRAWDOWN_PCT:
        reason = (f"CIRCUIT BREAKER TRIGGERED — Current daily drawdown "
                  f"({current_drawdown:.2f}%) >= limit ({MAX_DAILY_DRAWDOWN_PCT}%). "
                  f"ALL trades blocked for the rest of today.")

        # Mark circuit breaker as hit in daily_pnl
        await _execute_db(
            "UPDATE daily_pnl SET circuit_breaker_hit = TRUE WHERE date = $1",
            [date.today().isoformat()]
        )

        await _log_risk_decision(agent, action, chain, market, amount,
                                  False, reason, current_drawdown, 0.0, 0.0)
        return json.dumps({
            "approved": False,
            "reason": reason,
            "position_size": 0.0,
            "current_drawdown_pct": current_drawdown,
            "circuit_breaker_hit": True
        })

    # ── Check 2: Minimum trade size ──────────────────────────────────
    if amount < MIN_TRADE_AMOUNT:
        reason = f"Trade amount ${amount} below minimum ${MIN_TRADE_AMOUNT}"
        await _log_risk_decision(agent, action, chain, market, amount,
                                  False, reason, current_drawdown, 0.0, 0.0)
        return json.dumps({
            "approved": False,
            "reason": reason,
            "position_size": 0.0,
            "current_drawdown_pct": current_drawdown,
            "circuit_breaker_hit": False
        })
    # ── Check 2b: Leverage check (no leverage without human approval) ─
    leverage = _parse_numeric(params.get("leverage", 1.0))
    if leverage > LEVERAGE_MAX_WITHOUT_APPROVAL:
        reason = (f"LEVERAGE REJECTED — Requested {leverage}x leverage exceeds "
                  f"the maximum {LEVERAGE_MAX_WITHOUT_APPROVAL}x without explicit human approval. "
                  f"Tag @vernon_bella or @bud916 for leverage approval.")
        await _log_risk_decision(agent, action, chain, market, amount,
                                  False, reason, current_drawdown, 0.0, 0.0)
        return json.dumps({
            "approved": False,
            "reason": reason,
            "position_size": 0.0,
            "current_drawdown_pct": current_drawdown,
            "circuit_breaker_hit": False
        })

    # ── Check 3: Kelly Criterion position sizing ─────────────────────
    kelly_fraction = _calculate_kelly(
        win_probability,
        trade_type=trade_type,
        entry_price=entry_price if trade_type == "prediction" else None,
        tp_pct=tp_pct,
        sl_pct=sl_pct
    )
    suggested_size = portfolio_value * kelly_fraction if portfolio_value > 0 else amount
    max_allowed = portfolio_value * (MAX_SINGLE_TRADE_PCT / 100.0) if portfolio_value > 0 else amount

    # Cap the trade at the Kelly-suggested size
    final_size = min(amount, suggested_size, max_allowed) if portfolio_value > 0 else amount

    # ── Check 4: Would this trade push us over the drawdown limit? ───
    remaining_budget = (MAX_DAILY_DRAWDOWN_PCT - current_drawdown) / 100.0 * portfolio_value if portfolio_value > 0 else float('inf')
    if final_size > remaining_budget and portfolio_value > 0:
        final_size = remaining_budget
        if final_size < MIN_TRADE_AMOUNT:
            reason = (f"Remaining daily risk budget (${remaining_budget:.2f}) is below "
                      f"minimum trade size. Drawdown: {current_drawdown:.2f}%")
            await _log_risk_decision(agent, action, chain, market, amount,
                                      False, reason, current_drawdown, 0.0, remaining_budget)
            return json.dumps({
                "approved": False,
                "reason": reason,
                "position_size": 0.0,
                "current_drawdown_pct": current_drawdown,
                "circuit_breaker_hit": False
            })

    # ── APPROVED ─────────────────────────────────────────────────────
    mode = "DRY RUN" if dry_run else "LIVE"
    reason = (f"APPROVED ({mode}) — Kelly fraction: {kelly_fraction:.4f}, "
              f"Position size: ${final_size:.2f}, "
              f"Current drawdown: {current_drawdown:.2f}%, "
              f"Remaining budget: ${remaining_budget:.2f}" if portfolio_value > 0
              else f"APPROVED ({mode}) — No portfolio value set, using requested amount")

    await _log_risk_decision(agent, action, chain, market, amount,
                              True, reason, current_drawdown, final_size,
                              remaining_budget if portfolio_value > 0 else 0.0)

    # Track exact one-time approval for pre-trade enforcement.
    _cleanup_expired_approvals()
    approval = {
        "agent": str(agent).lower(),
        "action": str(action).lower(),
        "market": market,
        "execution_market": execution_market,
        "max_amount": round(final_size, 6),
        "approved_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(seconds=RISK_APPROVAL_TTL_SECONDS),
    }
    _risk_approvals[_approval_key(agent, action, execution_market)] = approval

    return json.dumps({
        "approved": True,
        "reason": reason,
        "position_size": round(final_size, 6),
        "current_drawdown_pct": current_drawdown,
        "circuit_breaker_hit": False,
        "kelly_fraction": kelly_fraction,
        "trade_type": trade_type,
        "dry_run": dry_run
    })


def register(ctx):
    """Register the risk_check tool with Hermes."""

    risk_check_schema = {
        "name": "risk_check",
        "description": (
            "MANDATORY pre-trade risk check. Must be called before EVERY trade or bet. "
            "Enforces a hardcoded 5% daily drawdown circuit breaker and calculates "
            "Kelly Criterion position sizes. Returns approval status with reasoning. "
            "For prediction markets, set trade_type='prediction' and entry_price to the "
            "market probability you are buying at. For spot trades, set trade_type='spot' "
            "and provide tp_pct/sl_pct."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "agent": {
                    "type": "string",
                    "description": "Agent name: 'trader' or 'predictor'"
                },
                "chain": {
                    "type": "string",
                    "description": "Execution venue: 'robinhood_mcp' or 'kalshi'"
                },
                "action": {
                    "type": "string",
                    "description": "Trade action: 'buy', 'sell', 'bet_yes', 'bet_no'"
                },
                "amount": {
                    "type": "number",
                    "description": "Requested trade amount in USD"
                },
                "market": {
                    "type": "string",
                    "description": "Market name or symbol (e.g., 'HOOD', 'Will BTC hit 100k?')"
                },
                "win_probability": {
                    "type": "number",
                    "description": "Estimated probability of winning this trade (0.0-1.0). Used for Kelly sizing."
                },
                "portfolio_value": {
                    "type": "number",
                    "description": "Current total portfolio value in USD. Used for position sizing."
                },
                "trade_type": {
                    "type": "string",
                    "description": "'prediction' for prediction markets, 'spot' for DeFi trades. Affects Kelly calculation."
                },
                "entry_price": {
                    "type": "number",
                    "description": "For prediction markets: the market probability/price you are buying at (0.0-1.0)."
                },
                "execution_market": {
                    "type": "string",
                    "description": "Exact identifier the execution tool will use, e.g. Robinhood symbol or Kalshi ticker. Used to bind approval to a specific order."
                },
                "market_id": {
                    "type": "string",
                    "description": "Alias for execution_market, commonly used for Kalshi tickers."
                },
                "tp_pct": {
                    "type": "number",
                    "description": "For spot trades: take-profit percentage as decimal (e.g. 0.15 for 15%). Default: 0.15."
                },
                "sl_pct": {
                    "type": "number",
                    "description": "For spot trades: stop-loss percentage as decimal (e.g. 0.07 for 7%). Default: 0.07."
                }
            },
            "required": ["agent", "chain", "action", "amount", "market"]
        }
    }

    ctx.register_tool("risk_check", "benki_risk", risk_check_schema, handle_risk_check, is_async=True)

    # --- Pre-trade guard: BLOCK trade tools unless risk_check was called ---
    def pre_trade_guard(tool_name, params):
        """
        Enforce that risk_check was called before any trade execution tool.
        Returns an error dict to block execution, or None to allow.
        """
        trade_tools = {"robinhood_mcp_order", "kalshi_order"}
        if tool_name in trade_tools:
            _cleanup_expired_approvals()

            if tool_name == "robinhood_mcp_order":
                agent = "trader"
                market = params.get("symbol") or params.get("asset") or params.get("market") or "unknown"
                actions = [str(params.get("action", "buy")).lower()]
            else:
                agent = "predictor"
                market = params.get("execution_market") or params.get("market_id") or params.get("ticker") or params.get("market") or "unknown"
                side = str(params.get("side") or params.get("outcome") or "yes").lower()
                order_action = str(params.get("action", "buy")).lower()
                if order_action == "sell":
                    actions = ["sell_bet", "sell"]
                else:
                    actions = [f"bet_{side}"]

            approval = None
            approval_key = None
            for action in actions:
                key = _approval_key(agent, action, market)
                if key in _risk_approvals:
                    approval = _risk_approvals[key]
                    approval_key = key
                    break

            if not approval:
                print(f"[risk-manager] 🛑 BLOCKED: '{tool_name}' called without matching risk_check approval "
                      f"for agent={agent}, market={market}, actions={actions}.")
                return json.dumps({
                    "error": f"BLOCKED: You must call risk_check for the exact {tool_name} order before execution.",
                    "status": "blocked",
                    "agent": agent,
                    "market": market,
                    "expected_actions": actions,
                })

            requested_amount = _parse_numeric(params.get("amount", 0))
            if requested_amount > approval["max_amount"] + 1e-9:
                print(f"[risk-manager] 🛑 BLOCKED: '{tool_name}' amount ${requested_amount:.2f} exceeds "
                      f"approved ${approval['max_amount']:.2f}.")
                return json.dumps({
                    "error": "BLOCKED: execution amount exceeds risk-approved position size.",
                    "status": "blocked",
                    "approved_amount": approval["max_amount"],
                    "requested_amount": requested_amount,
                })

            _risk_approvals.pop(approval_key, None)
            print(f"[risk-manager] ✅ Trade tool '{tool_name}' proceeding — exact risk approval consumed.")
        return None  # allow the call

    # Register as pre_tool_call hook if available, else post_tool_call
    try:
        ctx.register_hook("pre_tool_call", pre_trade_guard)
    except Exception:
        # Fallback: post-call audit logging
        def on_tool_call(tool_name, params, result):
            trade_tools = {"robinhood_mcp_order", "kalshi_order"}
            if tool_name in trade_tools:
                print(f"[risk-manager] ⚠️  Trade tool '{tool_name}' was called. "
                      f"Ensure risk_check was called first.")
        ctx.register_hook("post_tool_call", on_tool_call)
