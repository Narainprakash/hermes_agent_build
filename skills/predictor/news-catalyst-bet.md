---
name: news-catalyst-bet
description: Identify prediction markets that are temporarily mispriced due to a breaking news event, then fade or follow the move with a calibrated bet
---

# News Catalyst Bet Procedure

Breaking news often causes Polymarket odds to overshoot or undershoot their
true probability. This skill systematically finds and trades those mispricings
within the first 2-4 hours of a catalyst event.

## Step 0: Feature Gate Check (MANDATORY)
Before proceeding, check if prediction markets are enabled:
- Read the environment variable `FEATURE_PREDICTIONS` (or check your config)
- If `FEATURE_PREDICTIONS` is NOT "true" or is unset/empty:
  - **STOP IMMEDIATELY.** Do not proceed with any steps below.
  - Post in #predictor: "Prediction markets disabled by FEATURE_PREDICTIONS toggle. News catalyst scan skipped."
  - Log: `benki_db_log_cron(agent="predictor", cron_name="news-catalyst-bet", status="skipped", details="FEATURE_PREDICTIONS=false")`
  - Exit this skill.

## Step 1: Identify the Catalyst
From the MCB or via search_news:
- What is the major news event in the last 6 hours?
- Categories to watch: Fed statements, geopolitical escalation/de-escalation,
  regulatory rulings, major token launches, protocol hacks, ETF approvals

## Step 2: Find Related Polymarket Markets
Call get_polymarket_markets with queries related to the catalyst.
Examples:
- Fed announcement → search "Fed rate", "FOMC", "Powell"
- Geopolitical → search "ceasefire", "sanctions", "oil price"
- Crypto regulatory → search "SEC", "ETF", "CFTC"
- Protocol event → search token name + "hack", "upgrade", "listing"

Also call drift_bet_search with same queries (min_volume: 5000 — even smaller markets matter here).

## Step 3: Assess the Overshoot/Undershoot

**Fade the move (bet AGAINST the news-driven direction) when:**
- Odds moved >20% in past 24h due to the news
- The news is a preliminary report / rumor (not confirmed)
- Historical base rate suggests the market overreacted
- Example: "Iran ceasefire by April 30" drops to 2% on bad news when it was 15% yesterday
  → True probability may be 8% → BIG edge on YES

**Follow the move (bet WITH the news direction) when:**
- Odds have moved <5% despite highly relevant breaking news
- The market has not yet priced in a clear catalyst
- Example: Major country announces crypto-friendly regulation → "BTC hits $100k in 2026" still at 15%
  → True probability may now be 25% → edge on YES

## Step 4: Independent Probability Estimate

Build your estimate using this framework:
1. **Base rate:** How often has this type of event resolved YES historically?
2. **Prior probability:** What was the market pricing BEFORE the news?
3. **News strength:** Is this confirmed, preliminary, or speculative?
4. **Time to resolution:** Less time = less uncertainty = more extreme probabilities valid

Formula: `my_probability = base_rate × 0.3 + prior × 0.3 + news_adjustment × 0.4`

Document each component explicitly. Round to nearest 5%.

## Step 5: Edge Calculation and Sizing

```
edge = my_probability - market_probability
```

- edge < 5%: NO BET
- edge 5-15%: Standard size (2% of portfolio)
- edge 15-25%: Medium size (3% of portfolio) — tag @bud916 if >$30
- edge > 25%: Large size candidate — MUST tag @vernon_bella or @bud916 for approval first

### Step 5b: Time Decay Adjustment
Scale position size based on how old the catalyst news is:
| News Age | Size Multiplier |
|---|---|
| < 1 hour | 1.0× (full edge — market still adjusting) |
| 1-3 hours | 0.75× (edge partially priced in) |
| 3-6 hours | 0.50× (significant correction occurred) |
| > 6 hours | SKIP — odds have likely converged to fair value |

Apply: `adjusted_amount = base_amount × size_multiplier`

## Step 6: Risk Check and Execute
- Call risk_check with portfolio_value (from benki_db_daily_pnl or $1000 fallback)
- If approved, execute via polymarket_order or drift_bet_order
- Log to benki_db_log_trade

## Step 7: Set Resolution Alert
Record in MEMORY.md:
- Market question
- Position and amount
- My probability vs market probability at time of bet
- Resolution date
- News catalyst that prompted the bet
- Target: re-evaluate if market probability moves >10% — may want to exit early

## Step 8: Post Report
Post the JSON Execution Report in #predictor tagging @benki_main.

Report format MUST BE STRICT JSON fenced in ```json:
@benki_main
```json
{
  "report": "BET_RESULT",
  "directive_ref": "BET_NOW",
  "market": "[question]",
  "platform": "[polymarket/drift_bet]",
  "position": "[yes/no]",
  "status": "[placed|dry_run|rejected|below_edge]",
  "amount": [amount],
  "my_probability": [my_prob],
  "market_probability": [market_prob],
  "edge": [edge],
  "kelly_fraction": [X.XX],
  "risk_check": "[approved or rejected reason]",
  "brier_score_running": [X.XX],
  "catalyst": "[1-sentence description of the news event]",
  "error": null
}
```

## Anti-patterns to Avoid
- Do NOT bet on markets resolving in >90 days unless edge is >20%
- Do NOT bet on markets with <$5k volume on Drift BET (liquidity risk)
- Do NOT bet against scientific consensus (climate, vaccine efficacy) — base rates are clear
- Do NOT double down after a loss on the same market — one bet per market per catalyst