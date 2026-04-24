"""
Benki Polymarket Client Plugin
================================
Polymarket CLOB API integration for prediction market operations on Polygon.
Supports market discovery, order placement, and position tracking.
Uses DRY_RUN mode by default.
"""

import os
import json


def _get_config():
    return {
        "api_key": os.environ.get("POLYMARKET_API_KEY", ""),
        "secret": os.environ.get("POLYMARKET_SECRET", ""),
        "passphrase": os.environ.get("POLYMARKET_PASSPHRASE", ""),
        "private_key": os.environ.get("EVM_PRIVATE_KEY", ""),
        "dry_run": os.environ.get("DRY_RUN", "true").lower() == "true",
    }


async def handle_polymarket_search(params):
    """Search Polymarket for active prediction markets."""
    try:
        import aiohttp

        query = params.get("query", "")
        min_volume = float(params.get("min_volume", 50000))
        limit = int(params.get("limit", 10))

        # Polymarket REST API for market discovery
        async with aiohttp.ClientSession() as session:
            url = "https://gamma-api.polymarket.com/markets"
            api_params = {
                "limit": limit,
                "active": "true",
                "order": "volume",
                "ascending": "false",
            }
            if query:
                api_params["tag"] = query

            async with session.get(url, params=api_params) as resp:
                if resp.status == 200:
                    markets = await resp.json()
                    filtered = []
                    for m in markets:
                        vol = float(m.get("volume", 0))
                        if vol >= min_volume:
                            filtered.append({
                                "id": m.get("id"),
                                "question": m.get("question", ""),
                                "description": m.get("description", "")[:200],
                                "volume": vol,
                                "liquidity": float(m.get("liquidity", 0)),
                                "end_date": m.get("endDate", ""),
                                "outcomes": m.get("outcomes", []),
                                "outcome_prices": m.get("outcomePrices", []),
                            })
                    return json.dumps({
                        "markets": filtered,
                        "count": len(filtered),
                        "min_volume_filter": min_volume
                    })
                else:
                    return json.dumps({"error": f"Polymarket API returned {resp.status}"})
    except ImportError:
        return json.dumps({"error": "aiohttp not installed. Run: pip install aiohttp"})
    except Exception as e:
        return json.dumps({"error": str(e)})


async def handle_polymarket_order(params):
    """Place an order on Polymarket. Uses DRY_RUN by default."""
    config = _get_config()
    if not config["api_key"]:
        return json.dumps({"error": "POLYMARKET_API_KEY not configured"})

    market_id = params.get("market_id", "")
    outcome = params.get("outcome", "")  # 'Yes' or 'No'
    amount = float(params.get("amount", 0))
    price = float(params.get("price", 0))  # Limit price (0.0 - 1.0)

    if config["dry_run"]:
        return json.dumps({
            "status": "dry_run",
            "message": f"DRY RUN: Would place {outcome} order on market {market_id}",
            "market_id": market_id,
            "outcome": outcome,
            "amount": amount,
            "price": price,
            "platform": "polymarket",
            "chain": "polygon",
            "tx_hash": "dry_run_no_tx"
        })

    # Live order placement via CLOB client
    try:
        from py_clob_client.client import ClobClient
        from py_clob_client.clob_types import OrderArgs

        client = ClobClient(
            host="https://clob.polymarket.com",
            key=config["api_key"],
            chain_id=137,  # Polygon mainnet
        )

        # Build and place order
        order_args = OrderArgs(
            price=price,
            size=amount,
            side="BUY" if outcome.lower() == "yes" else "SELL",
            token_id=market_id,
        )

        result = client.create_and_post_order(order_args)
        return json.dumps({
            "status": "executed",
            "order_id": result.get("orderID", ""),
            "market_id": market_id,
            "outcome": outcome,
            "amount": amount,
            "price": price,
            "platform": "polymarket",
            "chain": "polygon"
        })
    except ImportError:
        return json.dumps({"error": "py-clob-client not installed. Run: pip install py-clob-client"})
    except Exception as e:
        return json.dumps({"error": str(e), "status": "failed"})


def register(ctx):
    """Register Polymarket tools with Hermes."""

    ctx.register_tool("polymarket_search", {
        "name": "polymarket_search",
        "description": (
            "Search Polymarket for active prediction markets. "
            "Returns markets sorted by volume with outcome prices."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query or tag (e.g., 'crypto', 'politics')"},
                "min_volume": {"type": "number", "description": "Minimum volume in USD (default: 50000)"},
                "limit": {"type": "integer", "description": "Max markets to return (default: 10)"}
            }
        }
    }, handle_polymarket_search)

    ctx.register_tool("polymarket_order", {
        "name": "polymarket_order",
        "description": (
            "Place an order on Polymarket (Polygon CLOB). "
            "In DRY_RUN mode, simulates without placing. "
            "IMPORTANT: Call risk_check BEFORE this tool."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "market_id": {"type": "string", "description": "Polymarket market/token ID"},
                "outcome": {"type": "string", "description": "'Yes' or 'No'"},
                "amount": {"type": "number", "description": "Amount in USDC"},
                "price": {"type": "number", "description": "Limit price (0.01 - 0.99)"}
            },
            "required": ["market_id", "outcome", "amount", "price"]
        }
    }, handle_polymarket_order)
