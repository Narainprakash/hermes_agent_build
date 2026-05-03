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
- Progress toward 30-day 2x growth target (Targeting ~2.3% daily compound)

## Step 3: Identify Lessons
Analyze each losing trade:
- Was the entry signal correct but timing wrong?
- Was the position size appropriate?
- Did the risk_check flags any concerns that were overridden by market conditions?

Analyze each winning trade:
- Was the edge correctly identified?
- Was the position size optimal (Kelly sizing)?
- Can this pattern be repeated?

## Step 4: Write Structured Lesson (Anti-Bloat System)

### 4a. Deduplication Check
Before writing a new lesson, scan the last 10 entries in `workspace/lessons.md`.
If a lesson with the same **root cause** already exists within the last 7 days, do NOT create a duplicate. Instead, append today's date to the existing entry and increment its `frequency` counter.

### 4b. Lesson Format (compact, structured)
Append to `workspace/lessons.md` using this exact format:
```markdown
### [YYYY-MM-DD] Lesson #[auto-increment]
**Type:** [dispatch_error | signal_quality | coordination_issue | market_regime | risk_event]
**Trigger:** [What happened today]
**Root Cause:** [Why it happened — be specific]
**Action:** [What to do differently]
**Frequency:** [1] (increment if duplicate within 7 days)
**Confidence:** [high | medium | low]
**First Seen:** [YYYY-MM-DD]
**Last Seen:** [YYYY-MM-DD]
```

### 4c. Capping Rule (CRITICAL — prevents bloat)
`workspace/lessons.md` must NEVER exceed **30 entries**. If it does:
1. Remove the oldest entries (by `First Seen` date) until only 25 remain
2. Before deleting, compress removed entries into a single **rollup entry**:
```markdown
### [YYYY-MM-DD] Rollup — [Month] Patterns
**Type:** compressed
**Summary:** [3-5 bullet points of recurring themes from removed entries]
**Patterns Retained:** [Only patterns with frequency >= 2]
```

### 4d. AGENTS.md Update Rule (only when pattern is proven)
DO NOT update `AGENTS.md` or `SOUL.md` every day. Only update when:
- A pattern has `frequency >= 3` (observed 3+ times), OR
- A pattern caused a circuit breaker hit, OR
- A dispatch error cost > 5% of portfolio

When updating `AGENTS.md`, append a concise rule:
```markdown
## RULE [auto-increment] — [Pattern Name] (freq: [N], since [date])
[One-line rule]. Triggered by: [conditions]. Action: [response].
```

## Step 5: Update Memory
Update MEMORY.md with:
- Today's P&L summary
- Key lessons learned (reference lesson number)
- Strategy adjustments for tomorrow
- Tokens/patterns to watch

## Step 6: Post Summary
Post a daily performance summary to #general:

📊 **Daily Performance Report** — [date]
**P&L:** $[amount] ([%])
**Growth Target Progress:** [Current balance vs target balance]
**Trades:** [executed] / [rejected by risk_check]
**Win Rate:** [X%]
**Drawdown:** [X%] / 5% limit
**Circuit Breaker:** [Not hit / Hit at HH:MM]
**Key Lessons:** [1-2 sentences — reference lesson number]
**Tomorrow's Focus:** [tokens/strategies to watch]
