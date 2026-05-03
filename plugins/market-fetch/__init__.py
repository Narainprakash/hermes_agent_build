"""
Benki Market Fetch Plugin
==========================
Async HTTP market data fetcher — NO API KEY REQUIRED.
Uses free public endpoints: CoinGecko, Polymarket Gamma, DuckDuckGo.

This plugin gives the orchestrator live internet access for:
  - Crypto prices (CoinGecko free tier, no key)
  - Polymarket prediction market data (public Gamma API)
  - DuckDuckGo instant answers for general crypto news
  - Generic URL fetch for any public JSON endpoint

All endpoints confirmed reachable from the Docker container.
Uses aiohttp for non-blocking async I/O.
"""

import json
import aiohttp
import ssl
import os
from datetime import datetime, timezone

# Shared SSL context + UA header to avoid 403s
_SSL_CTX = ssl.create_default_context()
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; BenkiBot/1.0)"}


async def _fetch(url: str, timeout: int = 10) -> dict:
    """Async HTTP GET → parsed JSON dict. Raises on error."""
    async with aiohttp.ClientSession(headers=_HEADERS) as session:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout), ssl=_SSL_CTX) as resp:
            resp.raise_for_status()
            text = await resp.text()
            return json.loads(text)


async def _fetch_text(url: str, timeout: int = 10) -> str:
    """Async HTTP GET → text string."""
    async with aiohttp.ClientSession(headers=_HEADERS) as session:
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
    coins = params.get("coins", ["bitcoin", "ethereum", "solana", "matic-network"])
    if isinstance(coins, str):
        coins = [c.strip() for c in coins.split(",")]

    # Normalise common ticker symbols → CoinGecko IDs
    symbol_map = {
        "btc": "bitcoin", "eth": "ethereum", "sol": "solana",
        "matic": "matic-network", "pol": "matic-network",
        "usdc": "usd-coin", "usdt": "tether",
        "bnb": "binancecoin", "avax": "avalanche-2",
        "link": "chainlink", "uni": "uniswap", "arb": "arbitrum",
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


async def handle_get_polymarket_markets(params, **kwargs):
    """
    Fetch active Polymarket prediction markets from the free Gamma API.
    Returns top markets by volume with current odds.
    No API key required.
    """
    query = params.get("query", "")
    limit = int(params.get("limit", 15))
    min_volume = float(params.get("min_volume", 10000))
    category = params.get("category", "")  # e.g. "crypto", "politics"

    try:
        # Polymarket Gamma public API — no auth needed
        api_params = {
            "limit": min(limit * 3, 50),  # fetch extra to filter by volume
            "active": "true",
            "closed": "false",
            "order": "volume24hr",
            "ascending": "false",
        }
        if category:
            api_params["tag"] = category

        import urllib.parse
        qs = urllib.parse.urlencode(api_params)
        url = f"https://gamma-api.polymarket.com/markets?{qs}"
        markets_raw = await _fetch(url)

        filtered = []
        for m in markets_raw:
            vol = float(m.get("volume24hr") or m.get("volume") or 0)
            question = m.get("question", "")
            if vol >= min_volume:  # FIXED: was > (excluded valid markets)
                if query and query.lower() not in question.lower():
                    continue

                try:
                    prices = json.loads(m.get("outcomePrices", "[]"))
                    outcomes = json.loads(m.get("outcomes", "[]"))
                except Exception:
                    prices = []
                    outcomes = []

                odds = {}
                for i, outcome in enumerate(outcomes):
                    try:
                        p = float(prices[i])
                        odds[outcome] = {"probability": round(p, 4), "implied_pct": round(p * 100, 1)}
                    except Exception:
                        pass

                filtered.append({
                    "id": m.get("id"),
                    "question": question,
                    "volume_24h": round(vol, 0),
                    "total_volume": float(m.get("volume") or 0),
                    "liquidity": float(m.get("liquidity") or 0),
                    "end_date": m.get("endDate", ""),
                    "odds": odds,
                    "slug": m.get("slug", ""),
                    "url": f"https://polymarket.com/event/{m.get('slug', m.get('id', ''))}",
                })

                if len(filtered) >= limit:
                    break

        return json.dumps({
            "markets": filtered,
            "count": len(filtered),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "source": "gamma-api.polymarket.com (public)",
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
            "Use coin IDs (bitcoin, ethereum, solana) or common symbols (BTC, ETH, SOL)."
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

    ctx.register_tool("get_polymarket_markets", "benki_market", {
        "name": "get_polymarket_markets",
        "description": (
            "Fetch active Polymarket prediction markets with live odds. "
            "No API key required. Returns top markets by 24h volume. "
            "Filter by query string or category (e.g. 'crypto', 'politics')."
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
                "category": {
                    "type": "string",
                    "description": "Category tag filter (e.g. 'crypto', 'politics', 'sports')"
                }
            }
        }
    }, handle_get_polymarket_markets)

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
