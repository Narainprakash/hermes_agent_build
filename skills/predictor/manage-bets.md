---
name: manage-bets
description: Review open Polymarket and Drift bets to determine if positions should be closed early based on shifting probabilities.
---

# Bet Management Procedure

## Step 1: Discover Open Bets
- Call `benki_db_query_trades` for agent="predictor" to find un-resolved bets.
- Review `MEMORY.md` for the original entry rationale and probabilities.

## Step 2: Re-Evaluate Edge
For each open bet:
- Use `polymarket_search` or `drift_bet_search` to find the current market probability.
- Use `web_search` to reassess the real-world probability.
- Calculate the new edge.

## Step 3: Determine Exit
- If the market has fundamentally shifted and your probability is now lower than the market probability (negative edge), mark for EARLY EXIT.
- If the market has resolved, note the final outcome.

## Step 4: Execute Exits
For each early exit:
- Call `risk_check` with action="sell_bet".
- Execute via `polymarket_order` or `drift_bet_order` to close the position.
- Log to PostgreSQL and post a report in #predictions.
- Update `MEMORY.md` with the resolution.
