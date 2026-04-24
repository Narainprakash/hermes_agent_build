---
name: portfolio-review
description: Check current portfolio positions, balances, and open P&L
---

# Portfolio Review Procedure

## Step 1: Check Balances
- Call `solana_balance` for native SOL
- Call `solana_balance` for key SPL tokens (USDC, etc.)
- Call `evm_balance` for native MATIC
- Call `evm_balance` for key ERC-20 tokens (USDC, WETH, etc.)

## Step 2: Review Open Positions
- Call `benki_db_query_trades` filtered by agent="trader" to see recent trades
- Identify any positions that haven't been closed

## Step 3: Check Risk Status
- Call `benki_db_daily_pnl` for current drawdown and circuit breaker status
- If drawdown > 7%, flag as WARNING
- If drawdown > 9%, flag as CRITICAL and recommend no new positions

## Step 4: Report
Post a portfolio summary in #trading:

💼 **Portfolio Status**
**Solana:** [SOL balance] SOL + [token balances]
**Polygon:** [MATIC balance] MATIC + [token balances]
**Open Positions:** [count]
**Daily Drawdown:** [X%] / 10% limit
**Status:** [Healthy / Warning / Critical]
