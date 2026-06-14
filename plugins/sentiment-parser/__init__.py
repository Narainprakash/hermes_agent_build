"""
Benki Sentiment Parser Plugin
==============================
Provides tools for scoring and structuring crypto market sentiment data.
The agent uses its built-in web_search tool to gather data, then calls
score_sentiment to structure and quantify the results.
"""

import json
from datetime import datetime, timezone


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

    ctx.register_tool("score_sentiment", "benki_sentiment", {
        "name": "score_sentiment",
        "description": (
            "Score and structure raw sentiment signals into a quantified assessment. "
            "Call this after gathering data via web_search."
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
