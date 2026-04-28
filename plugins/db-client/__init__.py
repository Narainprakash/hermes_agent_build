"""
Benki DB Client Plugin
======================
PostgreSQL read/write interface for the Benki trading system.
Provides tools for logging trades, querying P&L, and storing sentiment briefs.
"""

import os
import json
from datetime import date


def _get_db_url():
    return os.environ.get("BENKI_DB_URL", "")


async def handle_log_trade(params, **kwargs):
    """Log a trade execution to the database."""
    db_url = _get_db_url()
    if not db_url:
        return json.dumps({"error": "BENKI_DB_URL not configured"})

    try:
        import asyncpg
        conn = await asyncpg.connect(db_url)
        try:
            await conn.execute(
                """INSERT INTO trades (agent, chain, platform, action, market, 
                   amount, price, tx_hash, status, risk_check_passed, notes)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)""",
                params.get("agent", "unknown"),
                params.get("chain", "unknown"),
                params.get("platform", ""),
                params.get("action", "unknown"),
                params.get("market", ""),
                float(params.get("amount", 0)),
                float(params.get("price", 0)),
                params.get("tx_hash", ""),
                params.get("status", "dry_run"),
                params.get("risk_check_passed", False),
                params.get("notes", "")
            )
            return json.dumps({"success": True, "message": "Trade logged successfully"})
        finally:
            await conn.close()
    except Exception as e:
        return json.dumps({"error": str(e)})


async def handle_query_trades(params, **kwargs):
    """Query recent trades from the database."""
    db_url = _get_db_url()
    if not db_url:
        return json.dumps({"error": "BENKI_DB_URL not configured"})

    try:
        import asyncpg
        conn = await asyncpg.connect(db_url)
        try:
            limit = int(params.get("limit", 10))
            agent_filter = params.get("agent", None)

            if agent_filter:
                rows = await conn.fetch(
                    """SELECT id, agent, chain, platform, action, market, amount,
                       price, tx_hash, status, timestamp, notes
                       FROM trades WHERE agent = $1
                       ORDER BY timestamp DESC LIMIT $2""",
                    agent_filter, limit
                )
            else:
                rows = await conn.fetch(
                    """SELECT id, agent, chain, platform, action, market, amount,
                       price, tx_hash, status, timestamp, notes
                       FROM trades ORDER BY timestamp DESC LIMIT $1""",
                    limit
                )

            trades = []
            for row in rows:
                trades.append({
                    "id": row["id"],
                    "agent": row["agent"],
                    "chain": row["chain"],
                    "platform": row["platform"],
                    "action": row["action"],
                    "market": row["market"],
                    "amount": float(row["amount"]) if row["amount"] else 0,
                    "price": float(row["price"]) if row["price"] else 0,
                    "tx_hash": row["tx_hash"],
                    "status": row["status"],
                    "timestamp": row["timestamp"].isoformat() if row["timestamp"] else "",
                    "notes": row["notes"]
                })
            return json.dumps({"trades": trades, "count": len(trades)})
        finally:
            await conn.close()
    except Exception as e:
        return json.dumps({"error": str(e)})


async def handle_query_daily_pnl(params, **kwargs):
    """Query daily P&L for a given date (defaults to today)."""
    db_url = _get_db_url()
    if not db_url:
        return json.dumps({"error": "BENKI_DB_URL not configured"})

    try:
        import asyncpg
        conn = await asyncpg.connect(db_url)
        try:
            target_date_str = params.get("date", date.today().isoformat())
            # Convert string to date object for asyncpg
            from datetime import datetime
            try:
                target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                target_date = date.today()

            rows = await conn.fetch(
                "SELECT * FROM daily_pnl WHERE date = $1", target_date
            )
            if rows:
                row = rows[0]
                return json.dumps({
                    "date": str(row["date"]),
                    "starting_balance_usd": float(row["starting_balance_usd"] or 0),
                    "ending_balance_usd": float(row["ending_balance_usd"] or 0),
                    "realized_pnl": float(row["realized_pnl"] or 0),
                    "drawdown_pct": float(row["drawdown_pct"] or 0),
                    "circuit_breaker_hit": row["circuit_breaker_hit"],
                    "trades_executed": row["trades_executed"],
                    "trades_rejected": row["trades_rejected"]
                })
            return json.dumps({"message": f"No P&L data for {target_date}"})
        finally:
            await conn.close()
    except Exception as e:
        return json.dumps({"error": str(e)})


async def handle_log_sentiment(params, **kwargs):
    """Log a sentiment brief to the database."""
    db_url = _get_db_url()
    if not db_url:
        return json.dumps({"error": "BENKI_DB_URL not configured"})

    try:
        import asyncpg
        conn = await asyncpg.connect(db_url)
        try:
            await conn.execute(
                """INSERT INTO sentiment_briefs 
                   (brief_text, tokens_analyzed, overall_sentiment, confidence, dispatched_to)
                   VALUES ($1, $2, $3, $4, $5)""",
                params.get("brief_text", ""),
                params.get("tokens_analyzed", []),
                params.get("overall_sentiment", "neutral"),
                float(params.get("confidence", 0.5)),
                params.get("dispatched_to", [])
            )
            return json.dumps({"success": True, "message": "Sentiment brief logged"})
        finally:
            await conn.close()
    except Exception as e:
        return json.dumps({"error": str(e)})


async def handle_reset_daily_pnl(params, **kwargs):
    """Reset daily P&L starting balance from previous day."""
    db_url = _get_db_url()
    if not db_url:
        return json.dumps({"error": "BENKI_DB_URL not configured"})

    try:
        import asyncpg
        conn = await asyncpg.connect(db_url)
        try:
            await conn.execute(
                """INSERT INTO daily_pnl (date, starting_balance_usd)
                   VALUES (CURRENT_DATE, (
                     SELECT ending_balance_usd FROM daily_pnl
                     WHERE date = CURRENT_DATE - 1
                   ))
                   ON CONFLICT (date) DO NOTHING;"""
            )
            return json.dumps({"success": True, "message": "Daily P&L starting balance reset applied"})
        finally:
            await conn.close()
    except Exception as e:
        return json.dumps({"error": str(e)})


async def handle_log_cron(params, **kwargs):
    """Log a cron execution to the database."""
    db_url = _get_db_url()
    if not db_url:
        return json.dumps({"error": "BENKI_DB_URL not configured"})

    try:
        import asyncpg
        conn = await asyncpg.connect(db_url)
        try:
            await conn.execute(
                """INSERT INTO cron_logs (agent, cron_name, status, details)
                   VALUES ($1, $2, $3, $4)""",
                params.get("agent", "unknown"),
                params.get("cron_name", "unknown"),
                params.get("status", "success"),
                params.get("details", "")
            )
            return json.dumps({"success": True, "message": "Cron log recorded"})
        finally:
            await conn.close()
    except Exception as e:
        return json.dumps({"error": str(e)})


async def handle_update_daily_pnl(params, **kwargs):
    """
    Update daily P&L with current portfolio value, realized/unrealized PnL,
    and compute drawdown percentage. CRITICAL for circuit breaker to function.
    """
    db_url = _get_db_url()
    if not db_url:
        return json.dumps({"error": "BENKI_DB_URL not configured"})

    try:
        import asyncpg
        from datetime import datetime
        conn = await asyncpg.connect(db_url)
        try:
            today = date.today()
            ending_balance = float(params.get("ending_balance_usd", 0))
            realized_pnl = float(params.get("realized_pnl", 0))
            unrealized_pnl = float(params.get("unrealized_pnl", 0))
            trades_executed = int(params.get("trades_executed", 0))
            trades_rejected = int(params.get("trades_rejected", 0))

            # Get starting balance for drawdown calculation
            rows = await conn.fetch(
                "SELECT starting_balance_usd, max_drawdown_pct FROM daily_pnl WHERE date = $1", today
            )
            if rows and rows[0]["starting_balance_usd"]:
                starting = float(rows[0]["starting_balance_usd"])
                drawdown_pct = max(0.0, (starting - ending_balance) / starting * 100) if starting > 0 else 0.0
                prev_max_dd = float(rows[0]["max_drawdown_pct"] or 0)
                max_dd = max(drawdown_pct, prev_max_dd)
            else:
                starting = ending_balance  # First update of the day
                drawdown_pct = 0.0
                max_dd = 0.0

            # Upsert — preserve max_drawdown across updates
            await conn.execute(
                """INSERT INTO daily_pnl
                   (date, starting_balance_usd, ending_balance_usd, realized_pnl,
                    unrealized_pnl, drawdown_pct, max_drawdown_pct,
                    trades_executed, trades_rejected)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                   ON CONFLICT (date) DO UPDATE SET
                     ending_balance_usd = $3,
                     realized_pnl = COALESCE(daily_pnl.realized_pnl, 0) + $4,
                     unrealized_pnl = $5,
                     drawdown_pct = $6,
                     max_drawdown_pct = GREATEST(COALESCE(daily_pnl.max_drawdown_pct, 0), $7),
                     trades_executed = COALESCE(daily_pnl.trades_executed, 0) + $8,
                     trades_rejected = COALESCE(daily_pnl.trades_rejected, 0) + $9,
                     circuit_breaker_hit = CASE WHEN $6 >= 10.0 THEN TRUE
                                               ELSE daily_pnl.circuit_breaker_hit END""",
                today, starting, ending_balance, realized_pnl, unrealized_pnl,
                drawdown_pct, max_dd, trades_executed, trades_rejected
            )

            cb_msg = ""
            if drawdown_pct >= 10.0:
                cb_msg = " ⚠️ CIRCUIT BREAKER TRIGGERED — 10% drawdown reached!"

            return json.dumps({
                "success": True,
                "message": f"Daily P&L updated. Drawdown: {drawdown_pct:.2f}%{cb_msg}",
                "date": str(today),
                "starting_balance_usd": starting,
                "ending_balance_usd": ending_balance,
                "drawdown_pct": round(drawdown_pct, 2),
                "circuit_breaker_hit": drawdown_pct >= 10.0
            })
        finally:
            await conn.close()
    except Exception as e:
        return json.dumps({"error": str(e)})


def register(ctx):
    """Register database tools with Hermes."""

    # ── Log Trade ──
    ctx.register_tool("benki_db_log_trade", "benki_db", {
        "name": "benki_db_log_trade",
        "description": "Log a trade execution to the Benki PostgreSQL database.",
        "parameters": {
            "type": "object",
            "properties": {
                "agent": {"type": "string", "description": "Agent: 'trader' or 'predictor'"},
                "chain": {"type": "string", "description": "Chain: 'solana' or 'polygon'"},
                "platform": {"type": "string", "description": "Platform: 'jupiter', 'uniswap', 'polymarket', 'drift_bet'"},
                "action": {"type": "string", "description": "Action: 'buy', 'sell', 'bet_yes', 'bet_no'"},
                "market": {"type": "string", "description": "Token pair or market name"},
                "amount": {"type": "number", "description": "Trade amount in USD"},
                "price": {"type": "number", "description": "Entry price"},
                "tx_hash": {"type": "string", "description": "Transaction hash (or 'dry_run')"},
                "status": {"type": "string", "description": "Status: 'executed', 'failed', 'dry_run'"},
                "risk_check_passed": {"type": "boolean", "description": "Whether risk_check approved"},
                "notes": {"type": "string", "description": "Additional notes"}
            },
            "required": ["agent", "chain", "action", "market", "amount", "status"]
        }
    }, handle_log_trade, is_async=True)

    # ── Query Trades ──
    ctx.register_tool("benki_db_query_trades", "benki_db", {
        "name": "benki_db_query_trades",
        "description": "Query recent trades from the database. Optionally filter by agent.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max trades to return (default: 10)"},
                "agent": {"type": "string", "description": "Filter by agent: 'trader' or 'predictor'"}
            }
        }
    }, handle_query_trades, is_async=True)

    # ── Query Daily P&L ──
    ctx.register_tool("benki_db_daily_pnl", "benki_db", {
        "name": "benki_db_daily_pnl",
        "description": "Query daily P&L, drawdown, and circuit breaker status. Defaults to today.",
        "parameters": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "Date in YYYY-MM-DD format (default: today)"}
            }
        }
    }, handle_query_daily_pnl, is_async=True)

    # ── Log Sentiment Brief ──
    ctx.register_tool("benki_db_log_sentiment", "benki_db", {
        "name": "benki_db_log_sentiment",
        "description": "Log a Market Context Brief / sentiment analysis to the database.",
        "parameters": {
            "type": "object",
            "properties": {
                "brief_text": {"type": "string", "description": "Full brief text"},
                "tokens_analyzed": {
                    "type": "array", "items": {"type": "string"},
                    "description": "List of tokens analyzed (e.g., ['BTC', 'ETH', 'SOL'])"
                },
                "overall_sentiment": {"type": "string", "description": "'bullish', 'bearish', or 'neutral'"},
                "confidence": {"type": "number", "description": "Confidence score (0.0-1.0)"},
                "dispatched_to": {
                    "type": "array", "items": {"type": "string"},
                    "description": "Agents dispatched to: ['trader', 'predictor']"
                }
            },
            "required": ["brief_text", "overall_sentiment", "confidence"]
        }
    }, handle_log_sentiment, is_async=True)

    # ── Log Cron Execution ──
    ctx.register_tool("benki_db_log_cron", "benki_db", {
        "name": "benki_db_log_cron",
        "description": "Log a scheduled cron job execution to the database.",
        "parameters": {
            "type": "object",
            "properties": {
                "agent": {"type": "string", "description": "Agent: 'main', 'trader', or 'predictor'"},
                "cron_name": {"type": "string", "description": "Name of the cron job (e.g., 'market-research')"},
                "status": {"type": "string", "description": "Status: 'success' or 'failed'"},
                "details": {"type": "string", "description": "Any additional details or summary"}
            },
            "required": ["agent", "cron_name"]
        }
    }, handle_log_cron, is_async=True)

    # ── Reset Daily P&L ──
    ctx.register_tool("benki_db_reset_daily_pnl", "benki_db", {
        "name": "benki_db_reset_daily_pnl",
        "description": "Roll over the previous day's ending balance to today's starting balance in the daily_pnl table.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }, handle_reset_daily_pnl, is_async=True)

    # ── Update Daily P&L (CRITICAL for circuit breaker) ──
    ctx.register_tool("benki_db_update_daily_pnl", "benki_db", {
        "name": "benki_db_update_daily_pnl",
        "description": (
            "Update today's daily P&L with current portfolio value and compute drawdown. "
            "MUST be called after every trade execution and during hourly position reviews. "
            "This is what makes the circuit breaker work — without it, drawdown is always 0%."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ending_balance_usd": {
                    "type": "number",
                    "description": "Current total portfolio value in USD (cash + open positions)"
                },
                "realized_pnl": {
                    "type": "number",
                    "description": "P&L from closed trades this update (can be 0 if just updating balance)"
                },
                "unrealized_pnl": {
                    "type": "number",
                    "description": "Total unrealized P&L from open positions"
                },
                "trades_executed": {
                    "type": "integer",
                    "description": "Number of trades executed since last update (default: 0)"
                },
                "trades_rejected": {
                    "type": "integer",
                    "description": "Number of trades rejected since last update (default: 0)"
                }
            },
            "required": ["ending_balance_usd"]
        }
    }, handle_update_daily_pnl, is_async=True)

