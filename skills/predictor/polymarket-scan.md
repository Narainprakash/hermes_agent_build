---
name: polymarket-scan
description: Scan BOTH Polymarket and Drift BET for high-value prediction market opportunities. Evaluate edge rigorously. Track calibration.
---

# Prediction Market Scan Procedure (v3 — improved)

## Step 1: Dual-Platform Discovery
Run BOTH platforms in parallel:

**Polymarket:**
Call get_polymarket_markets with min_volume=50000, limit=20
Categories to prioritize: crypto, politics, economics, geopolitics

**Drift BET:**
Call drift_bet_search with min_volume=10000, limit=20
Note: LOWER threshold = MORE opportunities. Drift BET is systematically under-scanned.

Combine both lists. Remove any market you already have an open position in.

## Step 2: Quick Filter (remove obvious pass-throughs)
Skip any market where:
- Resolution is more than 90 days away AND volume < $500k
- The market is essentially settled (odds >95% or <5%) — insufficient edge available
- The question is ambiguous or depends on a metric you cannot independently verify

## Step 3: Rigorous Probability Estimation
For each surviving market, build a 3-step probability estimate:

**Step 3a — Base rate research:**
Call search_news for "[event type] historical frequency" or "[topic] odds statistics"
Example: "how often does the Fed cut rates after a pause" or "prediction market calibration politics"

**Step 3b — Current evidence assessment:**
Call search_news for the specific event: "[market question keywords] latest news"
Rate the evidence: Strong confirms YES, Strong confirms NO, Ambiguous

**Step 3c — Apply evidence adjustment using 7-tier scale:**

| Evidence Strength | Description | News Factor |
|---|---|---|
| Near-certain YES | Official announcement, confirmed by primary source | 0.95 |
| Strong YES | Multiple credible sources, strong confirming signals | 0.85 |
| Moderate YES | Single credible source, some corroborating evidence | 0.70 |
| Ambiguous / mixed | Conflicting signals, unclear | Use base_rate unchanged |
| Moderate NO | Single credible source suggesting against | 0.30 |
| Strong NO | Multiple credible sources, strong refuting signals | 0.15 |
| Near-certain NO | Official denial, confirmed resolution against | 0.05 |

```
if evidence is NOT Ambiguous:
  my_probability = base_rate × 0.30 + news_factor × 0.70
else:
  my_probability = base_rate
```

**Step 3d — Recency/momentum adjustment:**
- If market odds moved >10% in past 48h, research WHY before betting — often an overcorrection
- If your probability aligns with the DIRECTION of the move, reduce confidence (you may be anchoring)
- If your probability OPPOSES the market's recent move, increase confidence (contrarian edge is strongest here)

Round to nearest 5%.

## Step 4: Edge Calculation
```
edge = my_probability - market_probability
```
| Edge | Action |
|---|---|
| < 5% | Skip — no bet |
| 5-10% | Small bet — 1.5% of portfolio |
| 10-20% | Standard bet — 2.5% of portfolio |
| > 20% | Large bet candidate — tag @bud916 for approval before executing |

## Step 5: Calibration Check
Load MEMORY.md and find your running Brier score.
- If Brier > 0.20: increase minimum edge to 8% until you recalibrate
- If Brier 0.15-0.20: standard 5% edge applies
- If Brier < 0.15: you are well-calibrated — consider 4% edge for exceptional markets

If you have fewer than 10 resolved predictions, use standard 5% edge (insufficient data).

## Step 6: Risk Check (MANDATORY)
For each market with sufficient edge:
1. Get portfolio_value from benki_db_daily_pnl("YYYY-MM-DD") → ending_balance_usd
   Fallback: $1000 if DB unavailable
2. Call risk_check with:
   - agent: "predictor"
   - chain: "polygon" (Polymarket) or "solana" (Drift BET)
   - action: "bet_yes" or "bet_no"
   - amount: [calculated from edge tier above]
   - market: [market question]
   - win_probability: my_probability
   - portfolio_value: [REQUIRED for Kelly sizing]
   - trade_type: "prediction"
   - entry_price: market_probability (the price you are buying at)

**If REJECTED:** Log rejection, do NOT retry.

## Step 7: Execute
- Polymarket: call polymarket_order with market_id, outcome, amount, price=my_probability
- Drift BET: call drift_bet_order with market_id, outcome, amount

## Step 8: Log and Record
1. Call benki_db_log_trade:
   - platform: "polymarket" or "drift_bet"
   - action: "bet_yes" or "bet_no"
   - market: question text
   - amount: position size
   - notes: "edge=[X.X%] my_prob=[X.X%] market_prob=[X.X%] resolution=[date]"

2. Update MEMORY.md:
```
## Open Bet — [PLATFORM] [timestamp]
- Market: [question]
- Position: [Yes/No]
- My probability: [X%]
- Market probability at entry: [X%]
- Edge: [X%]
- Amount: $[X]
- Resolution date: [date]
- Catalyst: [what drove my estimate]
- Status: OPEN
```

## Step 9: Post Report
Post Prediction Report for each bet placed in #agent-logs (1494524548815655033).
At end of scan, post a summary:

🔮 **Prediction Scan Summary** — [timestamp]
**Markets scanned:** [Polymarket: X | Drift BET: Y]
**Bets placed:** [count]
**Skipped (below edge):** [count]
**Best edge found:** [X.X% on "market question"]
**Running Brier score:** [X.XX] ([X] predictions resolved)