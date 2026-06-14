"""
Benki Market Fetch Plugin
==========================
Async HTTP market data fetcher — NO API KEY REQUIRED.
Uses free public endpoints: CoinGecko, Kalshi public markets, DuckDuckGo.

This plugin gives the orchestrator live internet access for:
  - Crypto prices (CoinGecko free tier, no key)
    - Kalshi prediction market data (public markets API)
  - DuckDuckGo instant answers for general crypto news
  - Generic URL fetch for any public JSON endpoint

All endpoints confirmed reachable from the Docker container.
Uses aiohttp for non-blocking async I/O with connection pooling.
"""

import json
import aiohttp
import ssl
import os
from datetime import datetime, timezone

# Shared SSL context + UA header to avoid 403s
_SSL_CTX = ssl.create_default_context()
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; BenkiBot/1.0)"}

# Shared session for connection reuse
_session = None


async def _get_session():
    """Get or create a shared aiohttp session."""
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession(headers=_HEADERS)
    return _session


async def _fetch(url: str, timeout: int = 10) -> dict:
    """Async HTTP GET → parsed JSON dict. Raises on error."""
    session = await _get_session()
    async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout), ssl=_SSL_CTX) as resp:
        resp.raise_for_status()
        text = await resp.text()
        return json.loads(text)


async def _fetch_text(url: str, timeout: int = 10) -> str:
    """Async HTTP GET → text string."""
    session = await _get_session()
    async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout), ssl=_SSL_CTX) as resp:
        resp.raise_for_status()
        return await resp.text()

async def handle_get_funding_rates(params, **kwargs):
    """Fetch funding rates from Binance (may be blocked in some regions)."""
    url = "https://fapi.binance.com/fapi/v1/premiumIndex"
    try:
        data = await _fetch(url)
        return json.dumps([
            {"symbol": d["symbol"], "lastFundingRate": float(d["lastFundingRate"]) * 100}
            for d in data if d["symbol"] in ["BTCUSDT","ETHUSDT","SOLUSDT"]
        ])
    except Exception as e:
        # Graceful fallback if Binance blocks the IP (e.g., US region)
        return json.dumps({
            "error": "Funding rate service unavailable in your region",
            "details": str(e)
        })

# ─────────────────────────────────────────────────────────────────────────────
# Tool Handlers
# ─────────────────────────────────────────────────────────────────────────────

async def handle_get_crypto_prices(params, **kwargs):
    """
    Fetch live crypto prices from CoinGecko (free, no API key).
    Returns price in USD, 24h change, market cap, volume.
    """
    coins = params.get("coins", ["bitcoin", "ethereum"])
    if isinstance(coins, str):
        coins = [c.strip() for c in coins.split(",")]

    # Normalise common ticker symbols → CoinGecko IDs
    symbol_map = {
        "btc": "bitcoin", "eth": "ethereum",
        "usdt": "tether",
        "bnb": "binancecoin", "avax": "avalanche-2",
        "link": "chainlink", "arb": "arbitrum",
        "op": "optimism", "doge": "dogecoin", "pepe": "pepe",
    }
    resolved = [symbol_map.get(c.lower(), c.lower()) for c in coins]
    ids = ",".join(resolved)

    try:
        url = (
            f"https://api.coingecko.com/api/v3/simple/price"
            f"?ids={ids}&vs_currencies=usd"
            f"&include_24hr_change=true&include_market_cap=true&include_24hr_vol=true"
        )
        data = await _fetch(url)
        results = {}
        for cid, info in data.items():
            results[cid] = {
                "price_usd": info.get("usd"),
                "change_24h_pct": round(info.get("usd_24h_change", 0), 2),
                "market_cap_usd": info.get("usd_market_cap"),
                "volume_24h_usd": info.get("usd_24h_vol"),
            }
        return json.dumps({
            "prices": results,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "source": "coingecko.com (free tier)",
        })
    except Exception as e:
        return json.dumps({"error": str(e), "url": url})


async def handle_get_kalshi_markets(params, **kwargs):
    """
    Fetch active Kalshi prediction markets from the public markets API.
    Returns top markets by volume with current odds.
    No API key required.
    """
    query = params.get("query", "")
    limit = int(params.get("limit", 15))
    min_volume = float(params.get("min_volume", 10000))
    series_ticker = params.get("series_ticker", "")

    try:
        # Kalshi public markets API — no auth needed for discovery
        api_params = {
            "limit": min(max(limit * 3, limit), 1000),
            "status": "open",
        }
        if series_ticker:
            api_params["series_ticker"] = series_ticker

        import urllib.parse
        qs = urllib.parse.urlencode(api_params)
        url = f"https://external-api.kalshi.com/trade-api/v2/markets?{qs}"
        response = await _fetch(url)
        markets_raw = response.get("markets", [])

        filtered = []
        for m in markets_raw:
            vol = float(m.get("volume_24h_fp") or m.get("volume_fp") or 0)
            question = m.get("title") or m.get("subtitle") or m.get("ticker", "")
            if vol >= min_volume:  # FIXED: was > (excluded valid markets)
                if query and query.lower() not in question.lower():
                    continue

                yes_ask = float(m.get("yes_ask_dollars") or m.get("last_price_dollars") or 0)
                yes_bid = float(m.get("yes_bid_dollars") or yes_ask or 0)
                no_ask = float(m.get("no_ask_dollars") or max(0.0, 1.0 - yes_bid))
                no_bid = float(m.get("no_bid_dollars") or max(0.0, 1.0 - yes_ask))
                odds = {
                    "Yes": {"bid": round(yes_bid, 4), "ask": round(yes_ask, 4), "probability": round(yes_ask, 4)},
                    "No": {"bid": round(no_bid, 4), "ask": round(no_ask, 4), "probability": round(no_ask, 4)},
                }

                filtered.append({
                    "id": m.get("ticker"),
                    "ticker": m.get("ticker"),
                    "event_ticker": m.get("event_ticker"),
                    "question": question,
                    "volume_24h": round(vol, 0),
                    "total_volume": float(m.get("volume_fp") or 0),
                    "liquidity": float(m.get("liquidity_dollars") or 0),
                    "end_date": m.get("close_time") or m.get("expiration_time", ""),
                    "odds": odds,
                    "url": f"https://kalshi.com/markets/{m.get('ticker', '')}",
                })

                if len(filtered) >= limit:
                    break

        return json.dumps({
            "markets": filtered,
            "count": len(filtered),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "source": "external-api.kalshi.com/trade-api/v2/markets",
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


async def handle_search_news(params, **kwargs):
    """
    Search crypto news headlines using DuckDuckGo Instant Answer API.
    Free, no API key required.
    """
    query = params.get("query", "crypto market today")

    try:
        import urllib.parse
        qs = urllib.parse.urlencode({"q": query, "format": "json", "no_redirect": "1"})
        url = f"https://api.duckduckgo.com/?{qs}"
        data = await _fetch(url)

        abstract = data.get("AbstractText", "")
        related = [
            {"title": r.get("Text", ""), "url": r.get("FirstURL", "")}
            for r in data.get("RelatedTopics", [])[:8]
            if r.get("Text")
        ]
        results = data.get("Results", [])[:5]

        return json.dumps({
            "query": query,
            "abstract": abstract,
            "related_topics": related,
            "results": [{"title": r.get("Text", ""), "url": r.get("FirstURL", "")} for r in results],
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "source": "api.duckduckgo.com (free)",
            "note": "For richer news, set TAVILY_API_KEY in configs/main/.env",
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


async def handle_fetch_url(params, **kwargs):
    """
    Fetch any public URL and return its content as text.
    Max 50KB returned to keep context window manageable.
    """
    url = params.get("url", "")
    if not url:
        return json.dumps({"error": "url parameter is required"})

    max_bytes = int(params.get("max_bytes", 50000))

    try:
        text = await _fetch_text(url)
        truncated = len(text) > max_bytes
        return json.dumps({
            "url": url,
            "content": text[:max_bytes],
            "truncated": truncated,
            "length": len(text),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        return json.dumps({"error": str(e), "url": url})


async def handle_get_fear_greed(params, **kwargs):
    """
    Fetch the Crypto Fear & Greed Index from alternative.me (free, no key).
    """
    limit = int(params.get("days", 7))
    try:
        url = f"https://api.alternative.me/fng/?limit={limit}&format=json"
        data = await _fetch(url)
        entries = data.get("data", [])
        return json.dumps({
            "fear_greed": [
                {
                    "value": int(e["value"]),
                    "classification": e["value_classification"],
                    "timestamp": e["timestamp"],
                }
                for e in entries
            ],
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "source": "api.alternative.me/fng (free)",
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


# ─────────────────────────────────────────────────────────────────────────────
# Registration
# ─────────────────────────────────────────────────────────────────────────────

def register(ctx):
    """Register all market-fetch tools with Hermes."""

    ctx.register_tool("get_crypto_prices", "benki_market", {
        "name": "get_crypto_prices",
        "description": (
            "Fetch live cryptocurrency prices from CoinGecko. "
            "No API key required. Returns USD price, 24h % change, market cap, volume. "
            "Use coin IDs (bitcoin, ethereum) or common symbols (BTC, ETH)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "coins": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of coin IDs or symbols, e.g. ['bitcoin', 'ethereum', 'sol']"
                }
            }
        }
    }, handle_get_crypto_prices)

    ctx.register_tool("get_kalshi_markets", "benki_market", {
        "name": "get_kalshi_markets",
        "description": (
            "Fetch active Kalshi prediction markets with live odds. "
            "No API key required for discovery. Returns top markets by 24h volume. "
            "Filter by query string or optional series ticker."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Filter markets by keyword in the question (e.g. 'Bitcoin', 'ETH')"
                },
                "limit": {
                    "type": "integer",
                    "description": "Max markets to return (default: 15)"
                },
                "min_volume": {
                    "type": "number",
                    "description": "Minimum 24h volume in USD (default: 10000)"
                },
                "series_ticker": {
                    "type": "string",
                    "description": "Optional Kalshi series ticker filter"
                }
            }
        }
    }, handle_get_kalshi_markets)

    ctx.register_tool("search_news", "benki_market", {
        "name": "search_news",
        "description": (
            "Search for crypto news and market info via DuckDuckGo Instant Answers. "
            "Free, no API key. Good for quick context on tokens or market events."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query, e.g. 'Bitcoin price analysis today' or 'Ethereum merge news'"
                }
            },
            "required": ["query"]
        }
    }, handle_search_news)

    ctx.register_tool("fetch_url", "benki_market", {
        "name": "fetch_url",
        "description": (
            "Fetch any public URL and return the content as text. "
            "Useful for reading public JSON APIs, market data feeds, or news pages. "
            "Max 50KB returned."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Full URL to fetch (must be public, no auth required)"
                },
                "max_bytes": {
                    "type": "integer",
                    "description": "Maximum bytes to return (default: 50000)"
                }
            },
            "required": ["url"]
        }
    }, handle_fetch_url)

    ctx.register_tool("get_funding_rates", "benki_market", {
        "name": "get_funding_rates",
        "description": (
            "Fetch perpetual futures funding rates from Binance for BTC, ETH, SOL. "
            "Positive rate = longs pay shorts (overcrowded longs → correction risk). "
            "Negative rate = shorts pay longs (overcrowded shorts → squeeze risk). "
            "Rates are expressed as percentage. Extreme values (>0.03% or <-0.03%) are strong signals."
        ),
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }, handle_get_funding_rates)

    ctx.register_tool("get_fear_greed_index", "benki_market", {
        "name": "get_fear_greed_index",
        "description": (
            "Fetch the Crypto Fear & Greed Index from alternative.me. "
            "Free, no API key. Returns current value (0=extreme fear, 100=extreme greed) "
            "and up to 7 days of history."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Number of days of history to return (default: 7)"
                }
            }
        }
    }, handle_get_fear_greed)
