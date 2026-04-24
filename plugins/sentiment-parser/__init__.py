"""
Benki Sentiment Parser Plugin
==============================
Provides tools for the orchestrator to search and parse crypto market data.
Uses the agent's built-in web search (via Hermes tool gateway or configured 
search provider) and structures the results into Market Context Briefs.

This plugin registers a 'sentiment_search' tool that the agent uses to
gather market data before composing briefs.
"""

import json
from datetime import datetime, timezone


async def handle_sentiment_search(params, **kwargs):
    """
    Search for crypto market sentiment data.
    
    This tool provides a structured template for the agent to use with 
    its built-in web_search tool. The agent should:
    1. Use web_search to find the data
    2. Call this tool to structure and score the results
    """
    tokens = params.get("tokens", ["BTC", "ETH", "SOL"])
    timeframe = params.get("timeframe", "4h")
    
    # Build search queries for the agent to use
    queries = []
    for token in tokens:
        queries.extend([
            f"{token} price analysis last {timeframe}",
            f"{token} whale movements today",
            f"{token} on-chain metrics sentiment",
        ])
    
    # Add general market queries
    queries.extend([
        "crypto market fear greed index today",
        "DeFi TVL changes last 24 hours",
        "crypto liquidations last 24 hours",
        "Polymarket trending prediction markets crypto",
    ])
    
    return json.dumps({
        "search_queries": queries,
        "tokens": tokens,
        "timeframe": timeframe,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "instructions": (
            "Use the web_search tool to search for each query above. "
            "Then compile the results into a Market Context Brief using "
            "the format defined in your system prompt. Score overall "
            "sentiment from -1.0 (extremely bearish) to +1.0 (extremely bullish). "
            "Map to: bearish (<-0.2), neutral (-0.2 to 0.2), bullish (>0.2). "
            "Include confidence based on source agreement and data freshness."
        )
    })


async def handle_score_sentiment(params, **kwargs):
    """
    Score and structure raw sentiment data into a brief.
    The agent calls this after gathering data to produce a formatted output.
    """
    signals = params.get("signals", [])
    tokens = params.get("tokens", [])
    
    if not signals:
        return json.dumps({
            "error": "No signals provided. Use sentiment_search first to gather data."
        })
    
    # Count bullish/bearish/neutral signals
    bullish = sum(1 for s in signals if s.get("direction") == "bullish")
    bearish = sum(1 for s in signals if s.get("direction") == "bearish")
    neutral = sum(1 for s in signals if s.get("direction") == "neutral")
    total = bullish + bearish + neutral
    
    if total == 0:
        return json.dumps({"overall": "neutral", "confidence": 0.0, "score": 0.0})
    
    # Calculate weighted score
    score = (bullish - bearish) / total  # -1.0 to 1.0
    confidence = 1.0 - (neutral / total)  # Higher when signals agree
    
    if score > 0.2:
        overall = "bullish"
    elif score < -0.2:
        overall = "bearish"
    else:
        overall = "neutral"
    
    return json.dumps({
        "overall": overall,
        "score": round(score, 3),
        "confidence": round(confidence, 3),
        "signal_counts": {
            "bullish": bullish,
            "bearish": bearish,
            "neutral": neutral,
            "total": total
        },
        "tokens_analyzed": tokens,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })


def register(ctx):
    """Register sentiment analysis tools with Hermes."""

    ctx.register_tool("sentiment_search", "benki_sentiment", {
        "name": "sentiment_search",
        "description": (
            "Generate a list of targeted search queries for crypto market sentiment analysis. "
            "Returns queries to use with the web_search tool, plus formatting instructions "
            "for creating a Market Context Brief."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "tokens": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Token symbols to analyze (e.g., ['BTC', 'ETH', 'SOL'])"
                },
                "timeframe": {
                    "type": "string",
                    "description": "Lookback window: '1h', '4h', '24h', '7d'"
                }
            }
        }
    }, handle_sentiment_search, is_async=True)

    ctx.register_tool("score_sentiment", "benki_sentiment", {
        "name": "score_sentiment",
        "description": (
            "Score and structure raw sentiment signals into a quantified assessment. "
            "Call this after gathering data via sentiment_search + web_search."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "signals": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source": {"type": "string"},
                            "direction": {"type": "string", "enum": ["bullish", "bearish", "neutral"]},
                            "summary": {"type": "string"},
                            "confidence": {"type": "number"}
                        }
                    },
                    "description": "List of sentiment signals gathered from research"
                },
                "tokens": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tokens that were analyzed"
                }
            },
            "required": ["signals"]
        }
    }, handle_score_sentiment, is_async=True)
