"""
Benki Kalshi Client Plugin
==========================
Kalshi API integration for prediction market discovery and order placement.
Supports DRY_RUN mode by default.
"""

import base64
import json
import os
import time
from urllib.parse import urlparse


DEFAULT_BASE_URL = "https://external-api.kalshi.com/trade-api/v2"

# Cache for the loaded private key to avoid repeated disk reads
_cached_private_key = None


def _get_config():
    return {
        "api_key_id": os.environ.get("KALSHI_API_KEY_ID", ""),
        "private_key": os.environ.get("KALSHI_PRIVATE_KEY", ""),
        "private_key_path": os.environ.get("KALSHI_PRIVATE_KEY_PATH", ""),
        "base_url": os.environ.get("KALSHI_BASE_URL", DEFAULT_BASE_URL).rstrip("/"),
        "dry_run": os.environ.get("DRY_RUN", "true").lower() == "true",
    }


def _as_float(value, default=0.0):
    try:
        return float(value) if value is not None and value != "" else default
    except (TypeError, ValueError):
        return default


def _load_private_key(config):
    """Load and cache the Kalshi private key from environment or file."""
    global _cached_private_key
    
    # Return cached key if already loaded
    if _cached_private_key is not None:
        return _cached_private_key
    
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import serialization

    pem = config.get("private_key", "")
    if not pem and config.get("private_key_path"):
        with open(config["private_key_path"], "rb") as key_file:
            pem = key_file.read()
    elif pem:
        pem = pem.encode("utf-8")

    if not pem:
        raise ValueError("KALSHI_PRIVATE_KEY or KALSHI_PRIVATE_KEY_PATH not configured")

    _cached_private_key = serialization.load_pem_private_key(pem, password=None, backend=default_backend())
    return _cached_private_key


def _auth_headers(config, method, path):
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding

    if not config["api_key_id"]:
        raise ValueError("KALSHI_API_KEY_ID not configured")

    private_key = _load_private_key(config)
    timestamp = str(int(time.time() * 1000))
    sign_path = urlparse(config["base_url"] + path).path.split("?")[0]
    message = f"{timestamp}{method.upper()}{sign_path}".encode("utf-8")
    signature = private_key.sign(
        message,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.DIGEST_LENGTH,
        ),
        hashes.SHA256(),
    )
    return {
        "KALSHI-ACCESS-KEY": config["api_key_id"],
        "KALSHI-ACCESS-SIGNATURE": base64.b64encode(signature).decode("utf-8"),
        "KALSHI-ACCESS-TIMESTAMP": timestamp,
        "Content-Type": "application/json",
    }


async def handle_kalshi_search(params, **kwargs):
    """Search Kalshi for open prediction markets."""
    try:
        import aiohttp
        import urllib.parse

        query = params.get("query", "")
        min_volume = float(params.get("min_volume", 50000))
        limit = int(params.get("limit", 10))
        series_ticker = params.get("series_ticker", "")
        base_url = os.environ.get("KALSHI_BASE_URL", DEFAULT_BASE_URL).rstrip("/")

        api_params = {
            "limit": min(max(limit * 3, limit), 1000),
            "status": "open",
        }
        if series_ticker:
            api_params["series_ticker"] = series_ticker

        url = f"{base_url}/markets?{urllib.parse.urlencode(api_params)}"
        async with aiohttp.ClientSession(headers={"User-Agent": "BenkiBot/1.0"}) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    return json.dumps({"error": f"Kalshi API returned {resp.status}"})
                data = await resp.json()

        filtered = []
        for market in data.get("markets", []):
            title = market.get("title") or market.get("subtitle") or market.get("ticker", "")
            if query and query.lower() not in title.lower():
                continue

            volume = _as_float(market.get("volume_24h_fp"), _as_float(market.get("volume_fp")))
            liquidity = _as_float(market.get("liquidity_dollars"))
            if volume < min_volume:
                continue

            yes_ask = _as_float(market.get("yes_ask_dollars"), _as_float(market.get("last_price_dollars")))
            yes_bid = _as_float(market.get("yes_bid_dollars"), yes_ask)
            no_ask = _as_float(market.get("no_ask_dollars"), max(0.0, 1.0 - yes_bid))
            no_bid = _as_float(market.get("no_bid_dollars"), max(0.0, 1.0 - yes_ask))

            filtered.append({
                "id": market.get("ticker"),
                "ticker": market.get("ticker"),
                "event_ticker": market.get("event_ticker"),
                "question": title,
                "volume_24h": round(volume, 2),
                "liquidity": liquidity,
                "end_date": market.get("close_time") or market.get("expiration_time", ""),
                "odds": {
                    "Yes": {"bid": yes_bid, "ask": yes_ask, "probability": yes_ask},
                    "No": {"bid": no_bid, "ask": no_ask, "probability": no_ask},
                },
                "url": f"https://kalshi.com/markets/{market.get('ticker', '')}",
            })
            if len(filtered) >= limit:
                break

        return json.dumps({
            "markets": filtered,
            "count": len(filtered),
            "source": "external-api.kalshi.com/trade-api/v2/markets",
        })
    except ImportError:
        return json.dumps({"error": "aiohttp not installed. Run: pip install aiohttp"})
    except Exception as e:
        return json.dumps({"error": str(e)})


async def handle_kalshi_order(params, **kwargs):
    """Place an order on Kalshi. Uses DRY_RUN by default."""
    config = _get_config()
    ticker = params.get("ticker") or params.get("market_id", "")
    side = params.get("side") or params.get("outcome", "yes")
    action = params.get("action", "buy")
    amount = float(params.get("amount", 0))
    price = float(params.get("price", 0))
    count = int(params.get("count", max(1, round(amount / max(price, 0.01)))))

    side = side.lower()
    if side not in {"yes", "no"}:
        return json.dumps({"error": "side/outcome must be 'yes' or 'no'", "status": "failed"})

    if config["dry_run"]:
        return json.dumps({
            "status": "dry_run",
            "message": f"DRY RUN: Would {action} {count} {side.upper()} contract(s) on {ticker}",
            "market_id": ticker,
            "ticker": ticker,
            "outcome": side,
            "amount": amount,
            "price": price,
            "platform": "kalshi",
            "chain": "offchain",
            "tx_hash": "dry_run_no_tx",
        })

    try:
        import aiohttp

        path = "/portfolio/orders"
        price_cents = max(1, min(99, round(price * 100)))
        body = {
            "ticker": ticker,
            "side": side,
            "action": action,
            "count": count,
            "time_in_force": "immediate_or_cancel",
        }
        if side == "yes":
            body["yes_price"] = price_cents
        else:
            body["no_price"] = price_cents

        headers = _auth_headers(config, "POST", path)
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(config["base_url"] + path, json=body, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                result = await resp.json()
                if resp.status not in (200, 201):
                    return json.dumps({"error": result, "status": "failed"})

        order = result.get("order", {})
        return json.dumps({
            "status": "executed",
            "order_id": order.get("order_id", ""),
            "market_id": ticker,
            "ticker": ticker,
            "outcome": side,
            "amount": amount,
            "price": price,
            "platform": "kalshi",
            "chain": "offchain",
        })
    except ImportError:
        return json.dumps({"error": "aiohttp/cryptography not installed", "status": "failed"})
    except Exception as e:
        return json.dumps({"error": str(e), "status": "failed"})


def register(ctx):
    """Register Kalshi tools with Hermes."""

    ctx.register_tool("kalshi_search", "benki_kalshi", {
        "name": "kalshi_search",
        "description": "Search Kalshi for open prediction markets sorted by volume.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Keyword filter for market title"},
                "min_volume": {"type": "number", "description": "Minimum 24h volume in USD/contracts (default: 50000)"},
                "limit": {"type": "integer", "description": "Max markets to return (default: 10)"},
                "series_ticker": {"type": "string", "description": "Optional Kalshi series ticker filter"},
            },
        },
    }, handle_kalshi_search, is_async=True)

    ctx.register_tool("kalshi_order", "benki_kalshi", {
        "name": "kalshi_order",
        "description": "Place a Kalshi order. In DRY_RUN mode, simulates without placing. IMPORTANT: Call risk_check first.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Kalshi market ticker"},
                "market_id": {"type": "string", "description": "Alias for ticker"},
                "side": {"type": "string", "description": "yes or no"},
                "outcome": {"type": "string", "description": "Alias for side"},
                "action": {"type": "string", "description": "buy or sell"},
                "amount": {"type": "number", "description": "Dollar amount to spend"},
                "price": {"type": "number", "description": "Limit price/probability (0.01 - 0.99)"},
                "count": {"type": "integer", "description": "Optional contract count"},
            },
            "required": ["amount", "price"],
        },
    }, handle_kalshi_order, is_async=True)
