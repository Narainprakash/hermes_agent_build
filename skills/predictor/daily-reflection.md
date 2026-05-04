---
name: daily-reflection
description: End-of-day review for the predictor agent — prediction accuracy, calibration feedback, and MANDATORY edge adjustments
---

# Predictor Daily Reflection (v2 — calibration-driven)

## Step 0: Feature Gate Check (MANDATORY)
Before proceeding, check if prediction markets are enabled:
- Read the environment variable `FEATURE_PREDICTIONS` (or check your config)
- If `FEATURE_PREDICTIONS` is NOT "true" or is unset/empty:
  - **STOP IMMEDIATELY.** Do not proceed with any steps below.
  - Post in #predictor: "Prediction markets disabled by FEATURE_PREDICTIONS toggle. Daily reflection skipped."
  - Log: `benki_db_log_cron(agent="predictor", cron_name="daily-reflection", status="skipped", details="FEATURE_PREDICTIONS=false")`
  - Exit this skill.

## Step 1: Review Today's Predictions
- Call `benki_db_query_trades` with agent="predictor" for today
- List all bets placed (Polymarket + Drift BET)
- Note edge at time of entry, platform, and current status

## Step 2: Check Resolved Markets
- Use web_search to check if any of your open markets have resolved
- For each resolved market:
  1. Record outcome: 1 (YES resolved) or 0 (NO resolved)
  2. Compute Brier score for that prediction: `brier = (my_probability - outcome)^2`
  3. Update the prediction entry in MEMORY.md with outcome and Brier score
  4. Update running average Brier score

## Step 3: Calibration Adjustment (MANDATORY)
Read your running Brier score from MEMORY.md (computed over ALL resolved predictions).

| Brier Score | Adjustment |
|---|---|
| > 0.25 | **STOP BETTING for 24h.** Review methodology. Tag @bud916 for strategy review. |
| 0.20 - 0.25 | Increase minimum edge to 10%. You are systematically miscalibrated. |
| 0.15 - 0.20 | Standard 5% minimum edge. Continue as normal. |
| 0.10 - 0.15 | Good calibration. May use 4% edge for high-volume (>$500k) markets. |
| < 0.10 | Excellent calibration. Consider increasing position sizes by 25%. |

Write at the TOP of MEMORY.md:
```
## CALIBRATION STATUS (updated [date])
Running Brier score: [X.XX] (over [N] resolved predictions)
Active edge minimum: [5%/4%/7%/10%/PAUSED]
Position size modifier: [standard/+25%/-50%/ZERO]
```

**If you have fewer than 10 resolved predictions**, use standard 5% edge (insufficient data for calibration).

## Step 4: Platform Performance Breakdown
Analyze separately for each platform:
- Polymarket: avg edge, win rate, Brier score
- Drift BET: avg edge, win rate, Brier score
- If one platform Brier > 0.25 while the other < 0.15: focus on the better platform

## Step 5: Edge Quality Analysis
- Were your highest-edge bets (>15%) more accurate than low-edge (5-10%)?
- If HIGH edge bets have WORSE Brier than low edge: you're overconfident on strong views
- If LOW edge bets have WORSE Brier: your minimum edge threshold should be raised

## Step 6: Write Structured Lesson (Anti-Bloat System)

### 6a. Deduplication Check
Before writing a new lesson, scan the last 10 entries in `workspace/lessons.md`.
If a lesson with the same **root cause** already exists within the last 7 days, do NOT create a duplicate. Instead, append today's date to the existing entry and increment its `frequency` counter.

### 6b. Lesson Format (compact, structured)
Append to `workspace/lessons.md` using this exact format:
```markdown
### [YYYY-MM-DD] Lesson #[auto-increment]
**Type:** [win_pattern | loss_pattern | calibration_error | missed_opportunity | platform_bias]
**Trigger:** [What happened today]
**Root Cause:** [Why it happened — be specific]
**Action:** [What to do differently]
**Frequency:** [1] (increment if duplicate within 7 days)
**Confidence:** [high | medium | low]
**First Seen:** [YYYY-MM-DD]
**Last Seen:** [YYYY-MM-DD]
```

### 6c. Capping Rule (CRITICAL — prevents bloat)
`workspace/lessons.md` must NEVER exceed **30 entries**. If it does:
1. Remove the oldest entries (by `First Seen` date) until only 25 remain
2. Before deleting, compress removed entries into a single **rollup entry**:
```markdown
### [YYYY-MM-DD] Rollup — [Month] Patterns
**Type:** compressed
**Summary:** [3-5 bullet points of recurring themes from removed entries]
**Patterns Retained:** [Only patterns with frequency >= 2]
```

### 6d. AGENTS.md Update Rule (only when pattern is proven)
DO NOT update `AGENTS.md` or `SOUL.md` every day. Only update when:
- A pattern has `frequency >= 3` (observed 3+ times), OR
- A pattern caused a circuit breaker hit, OR
- A calibration error cost > 5% of portfolio

When updating `AGENTS.md`, append a concise rule:
```markdown
## RULE [auto-increment] — [Pattern Name] (freq: [N], since [date])
[One-line rule]. Triggered by: [conditions]. Action: [response].
```

## Step 7: Update Memory
Update MEMORY.md with:
- Prediction accuracy metrics (win rate, avg Brier, by platform)
- Calibration adjustments from Step 3
- Market categories where you perform best (crypto > politics? macro > geopolitics?)
- Specific category adjustments if one type has Brier > 0.25
- Reference to today's lesson number in `lessons.md`

## Step 8: Update Daily P&L
Call **benki_db_update_daily_pnl** with the current portfolio value.

## Step 9: Post Summary
Post prediction performance update in #predictions:

🔮 **Predictor Daily Report** — [date]
**Bets placed today:** [count]
**Open bets:** [count] (total exposure: $[X])
**Resolved today:** [count] — [wins]/[losses]
**Running Brier score:** [X.XX] ([interpretation])
**Active edge minimum:** [X%]
**Best performing category:** [category]
**Active adjustments:** [any from Step 3]
**Lesson written:** [yes/no — reference number if yes]
