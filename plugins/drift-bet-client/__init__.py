"""
Benki Drift BET Client Plugin
================================
Drift Protocol BET prediction market operations on Solana.
Supports market discovery and bet placement with cross-collateral.
Uses DRY_RUN mode by default.
"""

import os
import json


def _get_config():
    return {
        "rpc_url": os.environ.get("SOLANA_RPC_URL", ""),
        "private_key": os.environ.get("SOLANA_PRIVATE_KEY", ""),
        "dry_run": os.environ.get("DRY_RUN", "true").lower() == "true",
    }


async def handle_drift_bet_search(params, **kwargs):
    """Search Drift BET for active prediction markets on Solana."""
    config = _get_config()
    if not config["rpc_url"]:
        return json.dumps({"error": "SOLANA_RPC_URL not configured"})

    try:
        import aiohttp

        query = params.get("query", "")
        min_volume = float(params.get("min_volume", 10000))
        limit = int(params.get("limit", 10))

        # Drift BET API for market discovery
        async with aiohttp.ClientSession() as session:
            url = "https://bet-api.drift.trade/markets"
            api_params = {"limit": limit, "status": "active"}

            async with session.get(url, params=api_params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    markets = data if isinstance(data, list) else data.get("markets", [])
                    filtered = []
                    for m in markets:
                        vol = float(m.get("volume", m.get("totalVolume", 0)))
                        title = m.get("title", m.get("question", ""))
                        if vol >= min_volume and (not query or query.lower() in title.lower()):
                            filtered.append({
                                "id": m.get("id", m.get("marketIndex", "")),
                                "title": title,
                                "description": m.get("description", "")[:200],
                                "volume": vol,
                                "yes_price": float(m.get("yesPrice", m.get("probability", 0))),
                                "no_price": float(m.get("noPrice", 1 - float(m.get("probability", 0)))),
                                "end_date": m.get("endDate", m.get("expiryTs", "")),
                                "category": m.get("category", ""),
                            })
                    return json.dumps({
                        "markets": filtered[:limit],
                        "count": len(filtered),
                        "platform": "drift_bet",
                        "chain": "solana",
                        "min_volume_filter": min_volume
                    })
                else:
                    # Fallback if API structure differs
                    return json.dumps({
                        "error": f"Drift BET API returned {resp.status}",
                        "note": "Check https://bet.drift.trade for current API docs"
                    })
    except ImportError:
        return json.dumps({"error": "aiohttp not installed"})
    except Exception as e:
        return json.dumps({"error": str(e)})


async def handle_drift_bet_order(params, **kwargs):
    """Place a bet on Drift BET. Uses DRY_RUN by default."""
    config = _get_config()

    market_id = params.get("market_id", "")
    outcome = params.get("outcome", "")  # 'Yes' or 'No'
    amount = float(params.get("amount", 0))

    if config["dry_run"]:
        return json.dumps({
            "status": "dry_run",
            "message": f"DRY RUN: Would place {outcome} bet of ${amount} on Drift BET market {market_id}",
            "market_id": market_id,
            "outcome": outcome,
            "amount": amount,
            "platform": "drift_bet",
            "chain": "solana",
            "tx_hash": "dry_run_no_tx",
            "note": "Drift BET supports cross-collateral with 30+ assets"
        })

    # Live execution requires Drift SDK
    try:
        return json.dumps({
            "status": "error",
            "message": "Live Drift BET execution requires driftpy SDK integration",
            "note": "Install: pip install driftpy"
        })
    except Exception as e:
        return json.dumps({"error": str(e), "status": "failed"})


def register(ctx):
    """Register Drift BET tools with Hermes."""

    ctx.register_tool("drift_bet_search", "benki_drift", {
        "name": "drift_bet_search",
        "description": (
            "Search Drift BET for active prediction markets on Solana. "
            "Returns markets sorted by volume with current probabilities."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query (e.g., 'BTC', 'election')"},
                "min_volume": {"type": "number", "description": "Minimum volume in USD (default: 10000)"},
                "limit": {"type": "integer", "description": "Max markets to return (default: 10)"}
            }
        }
    }, handle_drift_bet_search, is_async=True)

    ctx.register_tool("drift_bet_order", "benki_drift", {
        "name": "drift_bet_order",
        "description": (
            "Place a bet on Drift BET prediction market (Solana). "
            "In DRY_RUN mode, simulates without placing. "
            "IMPORTANT: Call risk_check BEFORE this tool."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "market_id": {"type": "string", "description": "Drift BET market ID"},
                "outcome": {"type": "string", "description": "'Yes' or 'No'"},
                "amount": {"type": "number", "description": "Bet amount in USDC"}
            },
            "required": ["market_id", "outcome", "amount"]
        }
    }, handle_drift_bet_order, is_async=True)
