---
name: daily-reflection
description: End-of-day performance review, lessons learned, and memory update
---

# Daily Reflection Procedure

## Step 1: Query Today's Performance
- Call `benki_db_daily_pnl` for today's date
- Call `benki_db_query_trades` with limit=50 for today's trades
- Note: circuit breaker status, total trades executed vs rejected

## Step 2: Calculate Key Metrics
- Win rate: (profitable trades / total trades) × 100
- Average profit per winning trade
- Average loss per losing trade
- Profit factor: (gross profits / gross losses)
- Max drawdown hit during the day
- Sentiment brief accuracy: compare morning predictions to actual price movements

## Step 3: Identify Lessons
Analyze each losing trade:
- Was the entry signal correct but timing wrong?
- Was the position size appropriate?
- Did the risk_check flags any concerns that were overridden by market conditions?

Analyze each winning trade:
- Was the edge correctly identified?
- Was the position size optimal (Kelly sizing)?
- Can this pattern be repeated?

## Step 4: Update Memory
Update MEMORY.md with:
- Today's P&L summary
- Key lessons learned
- Strategy adjustments for tomorrow
- Tokens/patterns to watch

## Step 5: Post Summary
Post a daily performance summary to #general:

📊 **Daily Performance Report** — [date]
**P&L:** $[amount] ([%])
**Trades:** [executed] / [rejected by risk_check]
**Win Rate:** [X%]
**Drawdown:** [X%] / 10% limit
**Circuit Breaker:** [Not hit / Hit at HH:MM]
**Key Lessons:** [1-2 sentences]
**Tomorrow's Focus:** [tokens/strategies to watch]
