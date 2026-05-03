---
name: lessons-template
description: Template and rules for maintaining the orchestrator's lessons.md file with anti-bloat controls
---

# Orchestrator Lessons.md — Template & Anti-Bloat Rules

## File Location
`workspace/lessons.md` (in the main agent's data volume)

## Max Size
**30 entries maximum.** Exceeding this triggers automatic compression.

## Entry Format
```markdown
### 2026-05-03 Lesson #1
**Type:** signal_quality
**Trigger:** MCB flagged SOL bullish but trader lost on entry
**Root Cause:** Momentum signal was 6h stale; price had already moved 4%
**Action:** Add freshness check — reject signals older than 2h
**Frequency:** 1
**Confidence:** high
**First Seen:** 2026-05-03
**Last Seen:** 2026-05-03
```

## Deduplication Rule
Before adding a new entry, check last 10 entries. If same root cause exists within 7 days:
- Do NOT create new entry
- Append date to existing `Last Seen`
- Increment `Frequency` by 1

## Compression Rule (when > 30 entries)
1. Sort by `First Seen` ascending
2. Remove oldest entries until count = 25
3. Create ONE rollup entry for removed items:
```markdown
### 2026-05-03 Rollup — April Patterns
**Type:** compressed
**Summary:**
- Stale momentum signals caused 3 bad dispatches (freq: 4)
- Fear & Greed > 75 reliably preceded corrections (freq: 3)
- Trader ignored predictor's crypto edge signals (freq: 2)
**Patterns Retained:** Stale signal rule, Greed zone caution
```

## AGENTS.md Promotion Rule
Only promote to `AGENTS.md` when:
- `frequency >= 3`, OR
- Caused circuit breaker hit, OR
- Dispatch error cost > 5% portfolio

## Valid Types
- `dispatch_error` — wrong directive or bad timing
- `signal_quality` — MCB signal was flawed
- `coordination_issue` — trader/predictor misalignment
- `market_regime` — broader market condition missed
- `risk_event` — circuit breaker or major drawdown
