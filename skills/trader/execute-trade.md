---
name: execute-trade
description: Step-by-step procedure for evaluating and executing a DeFi trade. Enforces Kelly sizing, momentum filter, and TP/SL target recording.
---

# Trade Execution Procedure (v3 — improved)

## Step 1: Parse the JSON `TRADE_NOW` Directive
When you receive a JSON `TRADE_NOW` block from @benki_main extract:
- asset and chain
- action (buy/sell)
- confidence score
- win_probability
- portfolio_value (provided by benki_main or fetch yourself)
- suggested_amount
- tp_pct and sl_pct

**Skip the trade immediately if:**
- Confidence < 0.60 → post skip reason in #trading
- Circuit breaker is active (check benki_db_daily_pnl — pass date as string "YYYY-MM-DD")
- No clear momentum signal (benki_main should have filtered this, but verify)

## Step 2: Get Portfolio Value (CRITICAL — Kelly requires this)
If benki_main did not provide portfolio_value:
1. Call benki_db_daily_pnl("YYYY-MM-DD" — today's date as a string)
2. Use ending_balance_usd as portfolio_value
3. If DB unavailable or returns error: use $1000 as conservative fallback
4. Note [DB UNAVAILABLE — used $1000 fallback] in the execution report

Never call risk_check without portfolio_value. Kelly Criterion is disabled without it
and you will get arbitrary position sizes.

## Step 3: Momentum Filter (quick check)
Get current price: call get_crypto_prices for [target_token, "bitcoin"]
```
token_momentum = token_24h_change - btc_24h_change
```
- If token_momentum < -0.5% AND confidence < 0.70: skip and report "Momentum unfavorable"
- If token_momentum > 0: confirms the signal, proceed with full confidence

## Step 4: Risk Check (MANDATORY — no exceptions)
Call risk_check with ALL of these fields:
```
agent: "trader"
chain: [solana or polygon]
action: [buy or sell]
amount: [suggested_amount from directive]
market: "[TOKEN]/USDC"
win_probability: [from directive]
portfolio_value: [from Step 2 — REQUIRED]
trade_type: "spot"
tp_pct: [from directive or default 0.15]
sl_pct: [from directive or default 0.07]
leverage: 1.0  # MUST be 1.0 — no leverage without human approval
```

**Updated Risk Limits (as of May 2026):**
- Max single trade: 2% of portfolio
- Max daily drawdown: 5% (circuit breaker)
- Max loss per trade: 2% of portfolio (hard stop-loss)
- No leverage > 1x without explicit human approval

**If REJECTED:** Post rejection reason. Do NOT retry same trade in this session.
**If APPROVED:** Use position_size from the risk_check response — NOT your original amount.

Note the Kelly fraction returned — if Kelly < 0.01 (1%), the edge is too thin to be worth it.
Post a skip note and move on.

## Step 5: Check for Duplicate Position
Call benki_db_query_trades(agent="trader", limit=5)
- If an open position in the same token exists: do NOT add to it without checking MEMORY.md
- Review MEMORY.md for the existing position's TP/SL — if price has NOT hit either, stand pat

## Step 6: Execute the Trade
Solana tokens (SOL, JTO, WIF, BONK, RNDR, INJ): use solana_swap
EVM tokens (MATIC, ARB, OP, LINK, AVAX): use evm_swap

Use position_size from risk_check (not suggested_amount).

## Step 7: Set TP/SL Targets
Based on confidence:
- confidence > 0.75: TP = entry × 1.20, SL = entry × 0.92
- confidence 0.60-0.75: TP = entry × 1.15, SL = entry × 0.94
- confidence 0.50-0.60: TP = entry × 1.10, SL = entry × 0.95 — tag @vernon_bella first

Also pass these to risk_check as tp_pct and sl_pct for accurate Kelly sizing:
```
risk_check(
  ...
  trade_type: "spot",
  tp_pct: 0.20,  # (or 0.15 or 0.10 per confidence tier)
  sl_pct: 0.08   # (or 0.06 or 0.05 per confidence tier)
)
```

### Step 7b: Volatility Adjustment
Adjust TP/SL based on the token's recent price behavior:
| Token Category | 24h Abs Change | TP/SL Multiplier |
|---|---|---|
| Large cap (BTC, ETH, SOL) | Any | 1.0× (standard) |
| Mid cap (ARB, OP, LINK, AVAX) | > 8% | 1.3× (wider ranges) |
| Mid cap | < 3% | 0.8× (tighter, take profits sooner) |
| Speculative (WIF, BONK, PEPE) | Always | 1.5× (high vol = wider ranges) |

Apply multiplier to BOTH TP and SL distances from entry.
Example: Standard TP +15% on BONK becomes +22.5% (15% × 1.5).

**Rationale:** Static TP/SL on a meme coin triggers stop-loss on normal noise,
while the same TP on BTC might take weeks to reach.

## Step 8: Record in MEMORY.md
Append this block after every trade:
```
## Open Position — [TOKEN] [timestamp]
- Entry price: $[price]
- Size: $[amount] (Kelly: [fraction])
- Chain: [solana/polygon]
- TP target: $[tp_price] (+X%)
- SL target: $[sl_price] (-X%)
- Confidence: [X.X] | Win probability: [X.X]
- Catalyst: [1-sentence from MCB]
- Status: OPEN
```

## Step 9: Log and Report
1. Call benki_db_log_trade with all fields including notes="TP:$X SL:$X"
2. Post the JSON Execution Report in #trading, tagging @benki_main

Report format MUST BE STRICT JSON fenced in ```json:
@benki_main
```json
{
  "report": "EXECUTION_RESULT",
  "directive_ref": "TRADE_NOW",
  "asset": "[TOKEN]/USDC",
  "chain": "[solana/polygon]",
  "action": "[buy/sell]",
  "status": "[executed|dry_run|rejected|skipped]",
  "amount": [amount],
  "entry_price": [price],
  "tp_target": [price],
  "sl_target": [price],
  "tx_hash": "[hash or dry_run]",
  "kelly_fraction": [X.XX],
  "risk_check": "[approved or rejected reason]",
  "portfolio_value_used": [amount]
}
```