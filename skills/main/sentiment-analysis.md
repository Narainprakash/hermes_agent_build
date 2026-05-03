---
name: sentiment-analysis
description: Analyze crypto market sentiment and create a Market Context Brief for dispatch to trading and prediction agents
---

# Sentiment Analysis Procedure

## Step 1: Gather Market Data
Use the `sentiment_search` tool with the following tokens:
- BTC, ETH, SOL (always include these core assets)
- Any tokens currently in the portfolio (check with `benki_db_query_trades`)

Use a 4-hour lookback timeframe for regular scans, 1-hour for urgent scans.

## Step 2: Execute Web Searches
For each query returned by `sentiment_search`, use the built-in `web_search` tool.
Focus on:
- Price action and technical indicators
- Whale movements and on-chain metrics
- Liquidation data
- Fear & Greed Index
- DeFi TVL changes
- Active Polymarket prediction markets (crypto-related)

## Step 3: Score the Signals
Use the `score_sentiment` tool with collected signals:
- Classify each data point as `bullish`, `bearish`, or `neutral`
- Include source and confidence for each signal
- The tool returns an overall score (-1.0 to +1.0) and confidence

## Step 4: Create Market Context Brief
Format using the MCB template in your system prompt:
- Include overall sentiment with confidence
- List key signals with sources
- Provide specific actionable items for @benki_trader (tokens/pairs)
- Provide specific actionable items for @benki_predictor (markets/events)
- Include current risk status (drawdown %, circuit breaker state)

## Step 5: Dispatch
1. Post the MCB in #general (your home channel)
2. Use `send_message` to post to #trading channel @mentioning @benki_trader with a STRICT JSON `TRADE_NOW` block
3. Use `send_message` to post to #predictor channel @mentioning @benki_predictor with a STRICT JSON `BET_NOW` block
4. Log the brief using `benki_db_log_sentiment`
5. Log the directive using `benki_db_log_command` for audit tracking

## Step 6: Update Memory
After dispatching, update MEMORY.md with:
- Brief summary of this scan's findings
- Any notable market regime changes
- Running tally of brief accuracy (compare past predictions to outcomes)

## Step 7: Risk Advisory in Every MCB
Every Market Context Brief MUST include:
- Current drawdown % (from benki_db_daily_pnl)
- Circuit breaker status (Safe / TRIPPED)
- Remaining daily risk budget (5% - current_drawdown)
- Reminder: max 2% per trade, no leverage without approval
