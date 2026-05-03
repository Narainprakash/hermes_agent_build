---
name: lessons-template
description: Template and rules for maintaining the predictor's lessons.md file with anti-bloat controls
---

# Predictor Lessons.md — Template & Anti-Bloat Rules

## File Location
`workspace/lessons.md` (in the predictor agent's data volume)

## Max Size
**30 entries maximum.** Exceeding this triggers automatic compression.

## Entry Format
```markdown
### 2026-05-03 Lesson #1
**Type:** calibration_error
**Trigger:** BTC $100k bet lost despite 0.35 probability estimate
**Root Cause:** Anchored to bullish news; ignored bearish on-chain signals
**Action:** Require 2+ independent sources before assigning probability > 0.30
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
- Overconfident on crypto predictions (freq: 5)
- Politics bets more accurate than macro (freq: 3)
- Drift BET liquidity issues caused slippage (freq: 2)
**Patterns Retained:** Crypto overconfidence, Politics edge
```

## AGENTS.md Promotion Rule
Only promote to `AGENTS.md` when:
- `frequency >= 3`, OR
- Caused circuit breaker hit, OR
- Calibration error cost > 5% portfolio

## Valid Types
- `win_pattern` — repeatable winning setup
- `loss_pattern` — repeatable losing mistake
- `calibration_error` — probability misestimation
- `missed_opportunity` — profitable bet skipped
- `platform_bias` — one platform consistently better/worse
