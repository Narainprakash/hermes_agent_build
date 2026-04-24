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
            target_date = params.get("date", date.today().isoformat())
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
