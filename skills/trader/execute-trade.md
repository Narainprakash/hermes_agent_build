---
name: execute-trade
description: Step-by-step procedure for evaluating and executing a DeFi trade based on a Market Context Brief
---

# Trade Execution Procedure

## Step 1: Parse the Market Context Brief
When you receive an MCB from @benki_main:
- Extract the overall sentiment and confidence
- Identify the specific actionable tokens/pairs for you
- Note the risk advisory (current drawdown, circuit breaker status)

**Skip the trade if:**
- MCB confidence < 0.6
- Circuit breaker is active
- No clear actionable signal for trading

## Step 2: Research the Opportunity
- Check current token prices using web_search
- Check your wallet balance using `solana_balance` or `evm_balance`
- Review recent trades using `benki_db_query_trades` (avoid repeating recent losses)

## Step 3: Risk Check (MANDATORY)
Call `risk_check` with:
- `agent`: "trader"
- `chain`: the target chain ("solana" or "polygon")
- `action`: "buy" or "sell"
- `amount`: your intended trade amount in USD
- `market`: the token pair (e.g., "SOL/USDC")
- `win_probability`: your estimated probability of profit (0.0-1.0)
- `portfolio_value`: current total portfolio value in USD

**IF REJECTED: Stop. Do not retry. Report the rejection reason in #trading.**

## Step 4: Execute the Trade
If risk_check approved:
- Use `solana_swap` for Solana trades (via Jupiter)
- Use `evm_swap` for Polygon trades
- Use the `position_size` from the risk_check response, NOT your original amount

## Step 5: Log and Report
1. Call `benki_db_log_trade` with all trade details
2. Post an Execution Report in #trading using the format in your system prompt
3. Include the tx hash and risk check details

## Step 6: Update Memory
After execution, note in MEMORY.md:
- Entry rationale
- Position size and Kelly calculation
- Expected exit criteria
