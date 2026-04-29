---
name: momentum-scan
description: Identify tokens with momentum divergence from BTC for high-probability short-term swing trades
---

# Momentum Scan Procedure

This skill finds the highest-probability trade setups by measuring which tokens
are leading or lagging the broader market, then dispatching actionable TRADE_NOW
directives with all required parameters pre-filled.

## Step 1: Baseline Fetch
- Call get_crypto_prices for the full watchlist:
  bitcoin, ethereum, solana, arbitrum, optimism, matic-network, avalanche-2,
  chainlink, render-token, injective-protocol, dogwifhat, pepe
- Record BTC 24h change as the BASELINE

## Step 2: Momentum Score Each Token
For each token:
```
momentum_score = token_24h_change - btc_24h_change
volume_signal  = (token_volume_24h / token_market_cap) — higher = more conviction
```

Tier classification:
- **STRONG BULLISH:** momentum_score > +2.5% — front-run the narrative
- **BULLISH:** momentum_score > +1.5% — trade the breakout
- **NEUTRAL:** -1.5% to +1.5% — no directional edge, skip
- **BEARISH:** momentum_score < -1.5% — potential short or avoid
- **STRONG BEARISH:** momentum_score < -3% — consider market-wide risk-off

## Step 3: Catalyst Check
For each BULLISH or STRONG BULLISH token:
- Call search_news for "[TOKEN] price catalyst news today"
- If news is found explaining the move: CONFIRMATION — proceed with higher confidence
- If no news found: ORPHAN momentum — lower confidence, smaller position

## Step 4: Fear & Greed Filter
- Call get_fear_greed_index
- F&G > 60 (Greed): Reduce confidence by 0.10 — market may be extended
- F&G 40-60 (Neutral): Standard confidence
- F&G < 40 (Fear): Add 0.05 to momentum confidence — fear dips are buy opportunities
- F&G < 25 (Extreme Fear): Only trade confirmed-catalyst breakouts, not general momentum

## Step 5: Build TRADE_NOW Directives
For each token that passes Steps 2-4 with final_confidence >= 0.60:

```json
{
  "directive": "TRADE_NOW",
  "asset": "[TOKEN]/USDC",
  "chain": "[solana/polygon]",
  "action": "[buy/sell]",
  "confidence": "[final_confidence]",
  "win_probability": "[use table below]",
  "portfolio_value": "[ending_balance_usd from benki_db_daily_pnl or 200 fallback]",
  "suggested_amount": "[2% of portfolio_value, min 10, max 50 for speculative tokens]",
  "tp_pct": 0.15,
  "sl_pct": 0.07,
  "reasoning": "[Sentence 1: momentum_score + F&G context. Sentence 2: catalyst or lack thereof.]",
  "mcb_timestamp": "[timestamp]"
}
```

**Win Probability Estimation (research-backed):**
| Condition | Base win_prob |
|---|---|
| momentum_score > 3% with catalyst | 0.65 |
| momentum_score 1.5-3% with catalyst | 0.60 |
| momentum_score > 3% no catalyst (orphan) | 0.58 |
| momentum_score 1.5-3% no catalyst (orphan) | 0.55 |

**Adjustments (apply all that match):**
- F&G > 75 (Extreme Greed): -0.05 (late-cycle risk)
- F&G < 30 (Fear): +0.03 (contrarian opportunity)
- Token already up >15% in 7d: -0.05 (mean reversion risk)
- Volume/MCap ratio > 0.10: +0.02 (strong conviction signal)
- **Hard cap: 0.70** (no crypto momentum signal deserves higher)

## Step 6: Anti-Signals (SKIP trade if any apply)
- Token had a >15% gain in past 7 days AND momentum is still up (extended, not a new breakout)
- Token news shows team/dev negative event (rug risk)
- BTC is down >3% today AND token has no independent catalyst
- Circuit breaker hit (check benki_db_daily_pnl)

## Step 7: Post Summary
Post a Momentum Scan Summary in #general:

⚡ **Momentum Scan** — [timestamp]
**BTC baseline:** [X.X%]
**Leaders (TRADE_NOW sent):** [token list with scores]
**Laggards (avoid/short):** [token list with scores]
**Skipped (below threshold):** [count]
**F&G:** [value] — [impact on confidence]

## Step 8: Update Memory
Record in MEMORY.md:
- Tokens dispatched today with their momentum scores
- F&G reading at time of scan
- Any anti-signals encountered