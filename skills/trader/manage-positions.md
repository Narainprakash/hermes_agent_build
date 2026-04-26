---
name: manage-positions
description: Review open portfolio positions against exit criteria and execute sells to take profit or stop loss.
---

# Position Management Procedure

## Step 1: Discover Open Positions
- Call `benki_db_query_trades` for agent="trader" to find open positions.
- Review `MEMORY.md` to recall the "Expected exit criteria" (take profit / stop loss levels) for each.

## Step 2: Check Live Prices
- Use `web_search` or market tools to check the current live price of each open asset.
- Calculate the current ROI for each position.

## Step 3: Evaluate Exit Criteria
For each open position:
- If current price >= Take Profit target: Mark for SELL (Take Profit).
- If current price <= Stop Loss target: Mark for SELL (Stop Loss).

## Step 4: Execute Sells
For each position marked for sale:
- Call `risk_check` with action="sell" and the specific asset to sell.
- If approved, execute via `solana_swap` or `evm_swap`.
- Call `benki_db_log_trade` to record the sell.
- Post a Trade Execution Report in #trading noting the exit reason (e.g., "Take Profit Hit").

## Step 5: Update Memory
- Remove closed positions from active tracking in `MEMORY.md`.
