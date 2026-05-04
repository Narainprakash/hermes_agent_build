---
name: manage-bets
description: Review open Polymarket and Drift bets to determine if positions should be closed early based on shifting probabilities.
---

# Bet Management Procedure

## Step 0: Feature Gate Check (MANDATORY)
Before proceeding, check if prediction markets are enabled:
- Read the environment variable `FEATURE_PREDICTIONS` (or check your config)
- If `FEATURE_PREDICTIONS` is NOT "true" or is unset/empty:
  - **STOP IMMEDIATELY.** Do not proceed with any steps below.
  - Post in #predictor: "Prediction markets disabled by FEATURE_PREDICTIONS toggle. Bet management skipped."
  - Log: `benki_db_log_cron(agent="predictor", cron_name="manage-bets", status="skipped", details="FEATURE_PREDICTIONS=false")`
  - Exit this skill.

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
- Log to PostgreSQL.
- Update `MEMORY.md` with the resolution.
- Post a JSON report in #predictor tagging @benki_main.

@benki_main
```json
{
  "report": "BET_MANAGEMENT_SUMMARY",
  "timestamp": "[timestamp]",
  "exits": [
    {
      "market": "[question]",
      "action": "[EARLY_EXIT|CLOSED_RESOLVED]",
      "pnl_amount": [pnl_amount]
    }
  ]
}
```
