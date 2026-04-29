---
name: manage-positions
description: Review open positions every hour against TP/SL targets. Execute exits or partial exits. Critical for realized gains.
---

# Position Management Procedure (v3 — improved)

This runs every hour via cron. This is where gains are LOCKED IN and losses are CUT.
Sloppy position management is the #1 reason trading systems fail to compound.

## Step 1: Load Open Positions from MEMORY.md
Read MEMORY.md and extract all blocks with `Status: OPEN`.
For each position, record:
- Token, chain, entry price
- TP target and SL target
- Size and timestamp

If MEMORY.md has no open positions: post "[manage-positions] No open positions — idle" and stop.

## Step 2: Fetch Current Prices
Call get_crypto_prices for ALL tokens with open positions in one call.
Map current_price to each position.

## Step 3: Evaluate Each Position
For each open position calculate:
```
current_pnl_pct = (current_price - entry_price) / entry_price × 100
```

**Action matrix:**
| Condition | Action |
|---|---|
| current_price >= TP target | FULL EXIT — take profit |
| current_price <= SL target | FULL EXIT — stop loss |
| current_pnl_pct >= +10% AND position age > 24h | PARTIAL EXIT — sell 50% |
| current_pnl_pct <= -4% AND momentum diverging | EARLY STOP — tighten SL |
| current_pnl_pct > +5% | TRAIL SL — move SL to break-even |
| No trigger hit | HOLD — no action |

## Step 4: Trailing Stop Logic
If current_pnl_pct > +5% AND position SL is still below entry:
- Move SL to entry_price × 0.995 (break-even minus 0.5%)
- Update MEMORY.md with new SL target
- Post: "🔒 Trailing stop set to break-even for [TOKEN]"

## Step 5: Partial Exit Execution
For PARTIAL EXIT (50% at +10% gain, age >24h):
- Call risk_check with action="sell", amount=position_size/2
- If approved, execute sell via solana_swap or evm_swap
- Update MEMORY.md: reduce size by 50%, note "50% taken at +X%"
- Leave remaining 50% open with SL now at break-even

This locks in gains while letting winners run.

## Step 6: Full Exit Execution
For FULL EXIT (TP hit or SL hit):
1. Call risk_check with action="sell", amount=full_position_size
2. If approved, execute sell
3. Call benki_db_log_trade recording the exit with notes="EXIT:[TP_HIT/SL_HIT] at $price"
4. Update MEMORY.md: change `Status: OPEN` to `Status: CLOSED — reason at $price`
5. Post exit report in #agent-logs

## Step 7: Age-Based Review
For any position older than 48 hours with no TP/SL hit:
- If current_pnl is between -2% and +2%: momentum has stalled
- Search news for the token: search_news "[TOKEN] price update"
- If no new catalyst: close the position (opportunity cost too high)
- If positive catalyst found: extend hold, tighten SL to -3% from current

## Step 8: Post Position Summary
After processing all positions, post the summary in #trading in STRICT JSON format, tagging @benki_main:

@benki_main
```json
{
  "report": "POSITION_SUMMARY",
  "timestamp": "[timestamp]",
  "realized_pnl_session": [total_realized],
  "open_unrealized_pnl": [total_open_unrealized],
  "positions": [
    {
      "asset": "[TOKEN]",
      "entry_price": [x],
      "current_price": [y],
      "pnl_pct": [Z],
      "tp_target": [a],
      "sl_target": [b],
      "action_taken": "[HOLD/PARTIAL EXIT/CLOSED]"
    }
  ]
}
```

## Step 8.5: Update Daily P&L (MANDATORY — circuit breaker depends on this)
After computing all position values, you MUST update the daily P&L tracker:
1. Calculate total portfolio value: cash_balance + sum(all open position current values)
2. Call **benki_db_update_daily_pnl** with:
   - ending_balance_usd: total_portfolio_value
   - realized_pnl: total P&L from positions closed this session (0 if none)
   - unrealized_pnl: total unrealized P&L from all open positions
   - trades_executed: number of exits executed this session
3. Check the response — if `circuit_breaker_hit` is true, post an URGENT alert in #general tagging @vernon_bella and @bud916

**Without this step, drawdown tracking is broken and the 10% circuit breaker will NEVER fire.**

## Step 9: Log and Update MEMORY.md
- Call benki_db_log_cron(agent="trader", cron_name="manage-positions", status="success")
- Ensure all closed positions are marked in MEMORY.md with outcome and lesson
- If 3 consecutive SL hits: note "SL STREAK" in MEMORY.md and tag @bud916 to review strategy