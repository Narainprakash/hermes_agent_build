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

## Step 5: Write Structured Lesson (Anti-Bloat System)

### 5a. Deduplication Check
Before writing a new lesson, scan the last 10 entries in `workspace/lessons.md`.
If a lesson with the same **root cause** already exists within the last 7 days, do NOT create a duplicate. Instead, append today's date to the existing entry and increment its `frequency` counter.

### 5b. Lesson Format (compact, structured)
Append to `workspace/lessons.md` using this exact format:
```markdown
### [YYYY-MM-DD] Lesson #[auto-increment]
**Type:** [win_pattern | loss_pattern | risk_mistake | missed_opportunity | market_regime]
**Trigger:** [What happened today]
**Root Cause:** [Why it happened — be specific]
**Action:** [What to do differently]
**Frequency:** [1] (increment if duplicate within 7 days)
**Confidence:** [high | medium | low]
**First Seen:** [YYYY-MM-DD]
**Last Seen:** [YYYY-MM-DD]
```

### 5c. Capping Rule (CRITICAL — prevents bloat)
`workspace/lessons.md` must NEVER exceed **30 entries**. If it does:
1. Remove the oldest entries (by `First Seen` date) until only 25 remain
2. Before deleting, compress removed entries into a single **rollup entry**:
```markdown
### [YYYY-MM-DD] Rollup — [Month] Patterns
**Type:** compressed
**Summary:** [3-5 bullet points of recurring themes from removed entries]
**Patterns Retained:** [Only patterns with frequency >= 2]
```

### 5d. AGENTS.md Update Rule (only when pattern is proven)
DO NOT update `AGENTS.md` or `SOUL.md` every day. Only update when:
- A pattern has `frequency >= 3` (observed 3+ times), OR
- A pattern caused a circuit breaker hit, OR
- A pattern saved > 5% of portfolio (major win)

When updating `AGENTS.md`, append a concise rule:
```markdown
## RULE [auto-increment] — [Pattern Name] (freq: [N], since [date])
[One-line rule]. Triggered by: [conditions]. Action: [response].
```

## Step 6: Update Memory
Update MEMORY.md with:
- Trading performance summary (win rate, P&L, profit factor)
- Patterns that worked vs didn't
- Specific adjustments for tomorrow (from Step 3 table)
- Tokens to watch / avoid based on today's data
- Reference to today's lesson number in `lessons.md`

## Step 7: Update Daily P&L
Call **benki_db_update_daily_pnl** with the final portfolio value for today.
This ensures accurate drawdown tracking for tomorrow's circuit breaker.

## Step 8: Post Summary
Post brief performance update in #trading with the Execution Report format.
Include the active adjustment rule if one was triggered.
Reference today's lesson number if one was written.
