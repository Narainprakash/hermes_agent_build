---
name: sentiment-analysis
description: Analyze crypto market sentiment and create a Market Context Brief for dispatch to trading and prediction agents
---

# Sentiment Analysis Procedure

## Step 0: Feature Gate Check
Before proceeding, check if prediction markets are enabled:
- Read the environment variable `FEATURE_PREDICTIONS` (or check your config)
- If `FEATURE_PREDICTIONS` is NOT "true" or is unset/empty:
  - SKIP all prediction-related steps below (Steps 2 Kalshi, Step 4 BET_NOW dispatch)
  - Continue with trading-related steps only
  - Note in your output: "Prediction markets disabled by FEATURE_PREDICTIONS toggle"

## Step 1: Gather Market Data
Use the built-in `web_search` tool to gather market data for the following tokens:
- BTC, ETH, SOL (always include these core assets)
- Any tokens currently in the portfolio (check with `benki_db_query_trades`)

Search for each token with queries like:
- "[TOKEN] price analysis last 4h"
- "[TOKEN] whale movements today"
- "[TOKEN] on-chain metrics sentiment"

Also search for general market data:
- "crypto market fear greed index today"
- "DeFi TVL changes last 24 hours"
- "crypto liquidations last 24 hours"
- "Kalshi trending prediction markets crypto" (ONLY if FEATURE_PREDICTIONS is enabled)

Use a 4-hour lookback timeframe for regular scans, 1-hour for urgent scans.

## Step 2: Score the Signals
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
3. **ONLY if FEATURE_PREDICTIONS is enabled:** Use `send_message` to post to #predictor channel @mentioning @benki_predictor with a STRICT JSON `BET_NOW` block
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
