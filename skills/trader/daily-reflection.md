---
name: daily-reflection
description: End-of-day review for the trader agent — trade outcomes, strategy assessment, and MANDATORY automatic adjustments
---

# Trader Daily Reflection (v2 — actionable)

## Step 1: Review Today's Trades
- Call `benki_db_query_trades` with agent="trader" for today
- Categorize: wins, losses, dry runs, skipped
- Calculate: win_rate, avg_win_size, avg_loss_size, profit_factor

## Step 2: Assess Performance
- Calculate win rate and profit factor
- Identify largest win and largest loss
- Check if Kelly sizing was followed
- Compare actual outcomes to the win_probability estimates used at entry

## Step 3: Strategy Adjustment Rules (MUST follow)
Based on today's performance, apply these **automatic adjustments**:

| Condition | Action |
|---|---|
| Win rate < 40% over last 5 trades | Increase momentum threshold from +1.5% to +2.5% for next 24h |
| Average loss > 2× average win | Tighten SL by 2% (e.g., -7% → -5%) for next 24h |
| 3+ consecutive losses | Reduce position sizes by 50% for next 24h |
| Win rate > 65% over last 10 trades | Consider increasing position sizes by 25% |
| Kelly fraction consistently < 0.02 | Edge is too thin — skip more aggressively |
| Profit factor < 1.0 | Set minimum confidence to 0.70 (up from 0.60) for next 24h |
| Profit factor > 2.0 | Current strategy is working — no changes needed |

Write the adjustment at the TOP of MEMORY.md as:
```
## ACTIVE ADJUSTMENT (expires [tomorrow_date])
- [Rule triggered]: [Action taken]
- Reason: [Win rate X% / loss streak / etc.]
```

Read this section at the start of EVERY trading session and follow it.

## Step 4: Pattern Analysis
- Which MCB signals led to profitable trades? (momentum score, F&G zone, catalyst type)
- Which signals led to losses? (orphan momentum? greed zone? extended token?)
- Were any risk_check rejections correct in hindsight?
- Were any SKIPPED trades profitable? (missed opportunities indicate edge threshold may be too high)

## Step 5: Update Memory
Update MEMORY.md with:
- Trading performance summary (win rate, P&L, profit factor)
- Patterns that worked vs didn't
- Specific adjustments for tomorrow (from Step 3 table)
- Tokens to watch / avoid based on today's data

## Step 6: Update Daily P&L
Call **benki_db_update_daily_pnl** with the final portfolio value for today.
This ensures accurate drawdown tracking for tomorrow's circuit breaker.

## Step 7: Post Summary
Post brief performance update in #trading with the Execution Report format.
Include the active adjustment rule if one was triggered.
