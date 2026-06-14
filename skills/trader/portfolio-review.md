---
name: portfolio-review
description: Check current portfolio positions, balances, and open P&L
---

# Portfolio Review Procedure

## Step 1: Check Balances
- Call `robinhood_mcp_account` for account context
- Call `robinhood_mcp_positions` for balances and positions

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
**Robinhood MCP Account:** [account id / status]
**Positions:** [symbols and values]
**Open Positions:** [count]
**Daily Drawdown:** [X%] / 5% limit
**Status:** [Healthy / Warning / Critical]
