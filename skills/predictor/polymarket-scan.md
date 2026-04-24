---
name: polymarket-scan
description: Scan Polymarket for high-value prediction market opportunities and evaluate edge
---

# Polymarket Scan Procedure

## Step 1: Discover Markets
Call `polymarket_search` with:
- Relevant queries based on the latest MCB (crypto, politics, sports, etc.)
- min_volume: 50000 (USD)
- limit: 10

## Step 2: Evaluate Edge
For each market returned:
1. Read the market question and description
2. Research the topic using `web_search` for latest information
3. Form your own probability estimate
4. Compare to market price: `edge = your_probability - market_probability`
5. Only proceed if edge >= 0.05 (5%)

## Step 3: Risk Check (MANDATORY)
For each trade opportunity with sufficient edge:
Call `risk_check` with:
- `agent`: "predictor"
- `chain`: "polygon"
- `action`: "bet_yes" or "bet_no"
- `amount`: intended bet amount
- `market`: the market question
- `win_probability`: your probability estimate

**IF REJECTED: Stop. Report rejection. Do NOT retry.**

## Step 4: Place Bet
If approved, call `polymarket_order` with:
- market_id from the search result
- outcome: "Yes" or "No"
- amount: the position_size from risk_check (not your original amount)
- price: your limit price

## Step 5: Log and Report
1. Call `benki_db_log_trade` with platform="polymarket"
2. Post a Prediction Report in #predictions using your system prompt format

## Step 6: Update Memory
Note in MEMORY.md:
- Market, your probability, market probability, edge
- Reasoning for your probability estimate
- Outcome tracking for past predictions
