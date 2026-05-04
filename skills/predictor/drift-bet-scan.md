---
name: drift-bet-scan
description: Scan Drift BET on Solana for prediction market opportunities
---

# Drift BET Scan Procedure

## Step 0: Feature Gate Check (MANDATORY)
Before proceeding, check if prediction markets are enabled:
- Read the environment variable `FEATURE_PREDICTIONS` (or check your config)
- If `FEATURE_PREDICTIONS` is NOT "true" or is unset/empty:
  - **STOP IMMEDIATELY.** Do not proceed with any steps below.
  - Post in #predictor: "Prediction markets disabled by FEATURE_PREDICTIONS toggle. Drift BET scan skipped."
  - Log: `benki_db_log_cron(agent="predictor", cron_name="drift-bet-scan", status="skipped", details="FEATURE_PREDICTIONS=false")`
  - Exit this skill.

## Step 1: Discover Markets
Call `drift_bet_search` with:
- Relevant queries from the latest MCB
- min_volume: 10000 (USD) — lower threshold than Polymarket
- limit: 10

## Step 2: Evaluate Edge
Same process as Polymarket scan:
1. Research each market question
2. Form your probability estimate
3. Calculate edge vs market probability
4. Proceed only if edge >= 0.05 (5%)

Note: Drift BET supports cross-collateral — you can use SOL, mSOL, or other assets as collateral.

## Step 3: Risk Check (MANDATORY)
Call `risk_check` with:
- `agent`: "predictor"
- `chain`: "solana"
- `action`: "bet_yes" or "bet_no"
- `amount`: intended bet amount
- `market`: the market title

**IF REJECTED: Stop immediately.**

## Step 4: Place Bet
If approved, call `drift_bet_order` with:
- market_id from search
- outcome: "Yes" or "No"
- amount: position_size from risk_check

## Step 5: Log and Report
1. Call `benki_db_log_trade` with platform="drift_bet", chain="solana"
2. Post Prediction Report in #predictions

## Step 6: Update Memory
Track prediction accuracy in MEMORY.md for self-improvement.
